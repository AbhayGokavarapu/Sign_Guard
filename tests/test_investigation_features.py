"""Outcome tests for comparison, provenance, static inspection, review and evidence custody."""
import io
import json
import zipfile
import hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import pymupdf as fitz
from PIL import Image
import pytest
import config
from core.pipeline import run
from core.document_diff import compare,ordered_text_diff
from simulation.security_fixtures import signed_control,incremental_update


@pytest.fixture(scope='module')
def baseline():return signed_control()


@pytest.fixture(autouse=True)
def no_shared_audit(monkeypatch,tmp_path):monkeypatch.setattr(config,'AUDIT_LOG_PATH',str(tmp_path/'audit.json'))


def test_text_reordering_and_repetition_are_preserved():
    assert ordered_text_diff('Pay Alice\nPay Bob','Pay Bob\nPay Alice')
    assert ordered_text_diff('Pay Alice\nPay Alice','Pay Alice')
    assert not ordered_text_diff('Pay Alice\nPay Bob','Pay Alice\nPay Bob')


def test_coverage_is_tied_to_a_signed_parsed_revision(baseline):
    from core.crypto_verifier import validate_byte_range
    from pyhanko.pdf_utils.reader import PdfFileReader
    reader=PdfFileReader(io.BytesIO(baseline))
    br=list(map(int,reader.embedded_signatures[0].sig_object['/ByteRange']))
    assert validate_byte_range(baseline,br).covers_signed_rev
    assert not validate_byte_range(b'0'*10+b'<abcd>'+b'0'*10+b'%%EOF',[0,10,16,15]).covers_signed_rev


def test_document_comparison_reports_changed_text_and_metadata(baseline):
    changed=incremental_update(baseline,'Payment amount: $9,000')
    result=compare(baseline,changed)
    assert not result.get('error')
    assert result['changed_pages']==[0]
    assert any('$9,000' in line for c in result['pages'][0]['text_changes'] for line in c['added'])
    assert result['original']['sha256']!=result['suspect']['sha256']


def test_comparison_identical_files(baseline):
    result=compare(baseline,baseline)
    assert result['identical_bytes'] and not result['changed_pages']


def test_comparison_added_and_removed_pages():
    from simulation.sample_generator import build_unsigned
    one,two=build_unsigned('One',pages=1),build_unsigned('One',pages=2)
    assert compare(one,two)['pages'][-1]['change']=='added'
    assert compare(two,one)['pages'][-1]['change']=='removed'


def test_timeline_records_changes_even_when_later_restored(baseline):
    changed=incremental_update(baseline,'Payment amount: $9,000')
    restored=incremental_update(changed,'Payment amount: $1,000')
    result=run(restored,record_audit=False)
    transitions=result.timeline['transitions']
    assert len(transitions)>=4
    assert any(p['change']=='modified' for t in transitions[-2:] for p in t['pages'])
    assert transitions[-1]['pages'][0]['text_changes']


def test_pair_selection_finds_late_duplicate_and_is_order_invariant():
    from core.pair_selector import select_pairs
    from core.signature_localizer import SignatureCandidate
    rng=np.random.default_rng(4)
    candidates=[]
    for i in range(8):
        img=Image.fromarray(rng.integers(0,256,(50,180,3),dtype=np.uint8))
        candidates.append(SignatureCandidate(i,(0,0,180,50),img,.5))
    candidates[-1].crop=candidates[-2].crop.copy()
    selected=select_pairs(candidates,2)
    reverse=select_pairs(list(reversed(candidates)),2)
    assert (selected[0][0].page,selected[0][1].page)==(6,7)
    assert [(a.page,b.page,s) for a,b,s in selected]==[(a.page,b.page,s) for a,b,s in reverse]


def test_active_content_detected_without_running_script():
    doc=fitz.open();doc.new_page()
    xref=doc.get_new_xref()
    doc.update_object(xref,'<< /S /JavaScript /JS (app.alert\\(test\\)) >>')
    doc.xref_set_key(doc.pdf_catalog(),'OpenAction',f'{xref} 0 R')
    raw=doc.tobytes();doc.close()
    result=run(raw,record_audit=False)
    assert result.active_content['review_required']
    assert {e['category'] for e in result.active_content['entries']} >= {'JavaScript','Open action'}
    assert result.fusion.verdict.value=='REVIEW REQUIRED'
    assert any(f.code=='PDF-ACTIVE-001' for f in result.fusion.findings)


def test_plain_text_mention_of_javascript_is_not_an_action():
    from simulation.sample_generator import build_unsigned
    result=run(build_unsigned('JavaScript /OpenAction /Launch are words here.'),record_audit=False)
    assert not result.active_content['review_required']


def test_provenance_records_thresholds_versions_and_options(baseline):
    result=run(baseline,ela_quality=85,record_audit=False)
    assert result.provenance['settings']['ela_quality']==85
    assert result.provenance['dependencies']['pyhanko']!='UNAVAILABLE'
    assert len(result.provenance['engine_source_sha256'])==64
    assert result.provenance['thresholds_and_limits']['ELA_HIGH_THRESHOLD']==config.ELA_HIGH_THRESHOLD


def test_review_keeps_machine_outcome_unchanged(baseline):
    from core.review import record_review,verify_reviews
    changed=incremental_update(baseline,'Payment amount: $9,000')
    result=run(changed,record_audit=False)
    finding=result.fusion.findings[0]
    history=record_review([],result.parsed.sha256,finding,'Benign','Approved change','Examiner')
    assert result.fusion.verdict.value=='REVIEW REQUIRED'
    assert verify_reviews(history)
    history[0]['reason']='rewritten'
    assert not verify_reviews(history)


def test_review_requires_reason(baseline):
    from core.review import record_review
    from core.evidence_fusion import Finding,Severity
    with pytest.raises(ValueError):record_review([],hashlib.sha256(baseline).hexdigest(),Finding('X',Severity.INFO,'T','D','M'),'Benign','')


def test_evidence_package_verifies_and_detects_modified_report(baseline):
    from reporting.evidence_bundle import build_bundle,verify_bundle
    result=run(baseline,record_audit=False)
    raw,reference=build_bundle(result)
    verified=verify_bundle(raw,reference)
    assert verified['valid'] and verified['independent_reference_matches']
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        files={n:archive.read(n) for n in archive.namelist()}
    files['report.json']=b'{}'
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w') as archive:
        for name,data in files.items():archive.writestr(name,data)
    assert not verify_bundle(output.getvalue(),reference)['valid']


def test_evidence_package_rejects_traversal_and_wrong_reference(baseline):
    from reporting.evidence_bundle import build_bundle,verify_bundle
    raw,reference=build_bundle(run(baseline,record_audit=False))
    assert not verify_bundle(raw,'0'*64)['valid']
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w') as archive:archive.writestr('../escape','test')
    assert not verify_bundle(output.getvalue())['valid']


def test_operator_signature_requires_an_independent_trust_key(baseline,tmp_path,monkeypatch):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization
    from reporting.evidence_bundle import build_bundle,verify_bundle
    key=Ed25519PrivateKey.generate();path=tmp_path/'signer.pem'
    path.write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
    monkeypatch.setenv('SIGNGUARD_EVIDENCE_SIGNING_KEY',str(path))
    raw,_=build_bundle(run(baseline,record_audit=False))
    assert verify_bundle(raw)['signature_valid']
    assert not verify_bundle(raw)['signer_trusted']
    public=key.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo)
    assert verify_bundle(raw,trusted_public_key=public)['signer_trusted']


def test_bounded_queue_rejects_saturation(baseline,monkeypatch):
    from core.processing_queue import admit
    monkeypatch.setattr(config,'MAX_CONCURRENT_JOBS',1)
    monkeypatch.setattr(config,'QUEUE_WAIT_S',.01)
    with admit():
        with ThreadPoolExecutor(1) as pool:
            result=pool.submit(run,baseline,record_audit=False).result(timeout=10)
    assert result.processing_error.startswith('Busy:')
    assert not result.coverage['complete']


def test_independent_renderer_is_real_and_bounded(baseline):
    from core.independent_checks import availability
    if not availability()['renderer']:pytest.skip('Poppler not installed')
    result=run(baseline,record_audit=False,renderer_check=True)
    assert result.renderer_comparison['engines']==['MuPDF','Poppler']
    assert len(result.renderer_comparison['pages'])==1
    assert result.renderer_comparison['complete']


def test_independent_signature_validator(baseline):
    from core.independent_checks import availability
    from core.worker import execute_task
    if not availability()['signature_validator']:pytest.skip('Poppler not installed')
    result=execute_task('external_validate',{'raw':baseline})
    assert result['signatures'][0]['valid']


def test_session_clear_removes_inputs_results_and_review_notes():
    from dashboard.session_controls import clear_mapping
    state={'pipeline_result':object(),'comparison_result':object(),'human_reviews':{'doc':['note']},'_upload_epoch':3,'nav_page':'Case review','document_upload_3':b'private'}
    clear_mapping(state)
    assert state=={'_upload_epoch':4,'nav_page':'Overview'}


def test_external_nonstandard_coverage_is_not_called_complete():
    path=Path(config.BASE_DIR)/'datasets/external-pyhanko/coverage-anomalies__signature-gap-too-big.pdf'
    result=run(path.read_bytes(),record_audit=False)
    assert result.crypto.results[0].integrity_status=='PASS'
    assert result.crypto.results[0].math_valid is True
    assert not result.crypto.results[0].byte_range.covers_signed_rev
    assert result.crypto.all_valid is False
    assert any(f.code=='CRYPTO-006' for f in result.fusion.findings)
    assert result.fusion.verdict.value=='REVIEW REQUIRED'


def test_timeline_explicitly_reports_page_removal(baseline):
    import tempfile
    from simulation.security_fixtures import signed_control
    raw=signed_control(pages=2)
    with tempfile.TemporaryDirectory() as folder:
        path=Path(folder)/'removed.pdf';path.write_bytes(raw)
        with fitz.open(path) as doc:
            doc.delete_page(1);doc.saveIncr()
        changed=path.read_bytes()
    result=run(changed,record_audit=False)
    assert any(row['change']=='removed' and row['page']==1 for t in result.timeline['transitions'] for row in t['pages'])


def test_comparison_package_round_trip(baseline):
    from reporting.evidence_bundle import build_bundle,verify_bundle
    result=compare(baseline,incremental_update(baseline,'Different amount: $8,000'))
    raw,reference=build_bundle(comparison=result)
    assert verify_bundle(raw,reference)['valid']


def test_review_package_cannot_mix_documents(baseline):
    from reporting.evidence_bundle import build_bundle
    from core.review import record_review
    from core.evidence_fusion import Finding,Severity
    result=run(baseline,record_audit=False)
    review=record_review([],'0'*64,Finding('X',Severity.INFO,'T','D','M'),'Benign','Reviewed')
    with pytest.raises(ValueError):build_bundle(result=result,reviews=review)


def test_timeout_stops_native_child_processes(tmp_path):
    import os,sys,time
    if os.name=='nt':pytest.skip('POSIX process-group enforcement')
    from core.worker import _run_process
    pidfile=tmp_path/'child.pid'
    program=('import subprocess,sys,time; '
             'from pathlib import Path; '
             'child=subprocess.Popen([sys.executable,"-c","import time; time.sleep(30)"]); '
             f'Path({str(pidfile)!r}).write_text(str(child.pid)); '
             'time.sleep(30)')
    with pytest.raises(RuntimeError,match='time limit'):
        _run_process([sys.executable,'-c',program],dict(os.environ),.7)
    pid=int(pidfile.read_text())
    stat=Path(f'/proc/{pid}/stat')
    assert not stat.exists() or stat.read_text().split()[2]=='Z'
