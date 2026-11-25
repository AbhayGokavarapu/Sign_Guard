"""Assertions on security outcomes, including negative controls and failure paths."""
import io
import json
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import pytest
import pymupdf as fitz
from PIL import Image
import config
from core.pipeline import run
from core.crypto_verifier import verify, validate_byte_range
from core.evidence_fusion import fuse
from simulation.security_fixtures import signed_control, tamper_signed, incremental_update, shadow_pair


@pytest.fixture(autouse=True)
def isolated_audit(tmp_path, monkeypatch):
    monkeypatch.setattr(config, 'AUDIT_LOG_PATH', str(tmp_path / 'audit.json'))


@pytest.fixture(scope='module')
def genuine():
    return signed_control()


def codes(result):
    return {f.code for f in result.fusion.findings}


def test_real_signature_and_untrusted_identity(genuine):
    result = run(genuine)
    sig = result.crypto.results[0]
    assert sig.integrity_status == 'PASS'
    assert sig.math_valid is True
    assert sig.trust_status == 'SELF-SIGNED (untrusted)'
    assert 'UNVERIFIED' in sig.identity_status
    assert result.fusion.verdict.value == 'INCONCLUSIVE'
    assert not codes(result)


def test_signed_bytes_tampering_is_critical(genuine):
    changed = tamper_signed(genuine)
    with fitz.open(stream=genuine, filetype='pdf') as a, fitz.open(stream=changed, filetype='pdf') as b:
        assert a[0].get_pixmap().samples == b[0].get_pixmap().samples
    result = run(changed)
    assert result.crypto.results[0].integrity_status == 'FAIL'
    assert result.fusion.verdict.value == 'TAMPERING DETECTED'
    assert 'CRYPTO-001' in codes(result)


def test_valid_incremental_content_change(genuine):
    changed = incremental_update(genuine, 'Payment amount: $9,000')
    assert changed.startswith(genuine)
    result = run(changed)
    assert result.crypto.results[0].integrity_status == 'PASS'
    assert result.crypto.results[0].math_valid is True
    assert result.fusion.verdict.value == 'REVIEW REQUIRED'
    assert {'SHADOW-001', 'SHADOW-002'} <= codes(result)
    assert result.revision.changed_area_pct > 0


def test_change_on_last_page_is_detected():
    _, changed = shadow_pair(pages=3, page_index=2)
    result = run(changed)
    assert result.coverage['pages_analysed'] == 3
    assert any(f.code == 'SHADOW-001' and f.page == 2 for f in result.fusion.findings)


def test_additional_signature_is_benign(genuine):
    from simulation.signed_samples import sign_pdf, get_test_cert
    updated, message = sign_pdf(genuine, *get_test_cert(), field_name='Signature2')
    assert updated is not None, message
    result = run(updated)
    assert result.crypto.total_sigs == 2
    assert all(s.integrity_status == 'PASS' and s.math_valid is True for s in result.crypto.results)
    assert all(s.modpolicy_status == 'COMPLIANT' for s in result.crypto.results)
    assert result.fusion.verdict.value == 'INCONCLUSIVE'
    assert not ({'CRYPTO-003', 'SHADOW-001'} & codes(result))


def test_annotation_is_not_claimed_as_forgery(genuine):
    result = run(incremental_update(genuine, annotation=True))
    assert result.crypto.results[0].integrity_status == 'PASS'
    assert result.fusion.verdict.value != 'TAMPERING DETECTED'
    assert 'SHADOW-001' not in codes(result)
    # pyHanko may conservatively reject annotations; preserve that policy result.


def test_unsigned_negative_control():
    from simulation.sample_generator import build_unsigned
    result = run(build_unsigned('Ordinary unsigned contract'))
    assert result.fusion.verdict.value == 'INCONCLUSIVE'
    assert result.fusion.integrity_verdict.value == 'NOT APPLICABLE'


def test_duplicate_has_geometric_evidence():
    from simulation.sample_generator import build_duplicate_sig_pdf
    result = run(build_duplicate_sig_pdf())
    assert 'ORB-001' in codes(result)
    assert result.ransac.geometric_ok
    assert result.ransac.inlier_count >= config.RANSAC_MIN_INLIERS


def test_last_page_signature_localisation():
    from simulation.sample_generator import build_multi_page_visual
    result = run(build_multi_page_visual(pages=3))
    assert result.page_results[2]['candidate_count'] >= 1
    assert result.coverage['pages_analysed'] == 3


def test_ela_all_measurements_and_verdict_ignore_amplification():
    from core.ela_detector import run_ela
    image = Image.fromarray(np.random.default_rng(17).integers(90, 165, (96, 96, 3), dtype=np.uint8))
    low, high = [run_ela(image, quality=85, amplification=a) for a in (1, 30)]
    for name in ('mean_residual', 'max_residual', 'std_residual', 'high_pct', 'histogram'):
        assert getattr(low, name) == getattr(high, name)
    assert fuse(ela_result=low).verdict == fuse(ela_result=high).verdict
    assert low.amplified.tobytes() != high.amplified.tobytes()


def test_byte_range_requires_zero_start_and_real_contents_gap():
    raw = b'0'*10 + b'<abcd>' + b'0'*10 + b'%%EOF'
    assert validate_byte_range(raw, [0, 10, 16, len(raw)-16]).structurally_valid
    assert not validate_byte_range(raw, [1, 9, 16, len(raw)-16]).structurally_valid
    assert not validate_byte_range(b'x'*100, [0,10,20,80]).structurally_valid


def test_fake_revision_tokens_in_stream_do_not_create_revisions():
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), 'Normal document')
    xref = page.get_contents()[0]
    doc.update_stream(xref, doc.xref_stream(xref) + b'\n% startxref\n1\n%%EOF\n')
    raw = doc.tobytes(deflate=False)
    doc.close()
    result = run(raw)
    assert len(result.revision.revisions) == 1
    assert result.revision.discovery_method == 'pyhanko_xref_chain'


def test_timeout_terminates_worker(genuine):
    result = run(genuine, timeout=.001)
    assert result.fusion.verdict.value == 'UNSUPPORTED'
    assert result.coverage['complete'] is False
    assert 'time limit' in result.processing_error


def test_huge_page_rejected_before_render():
    doc = fitz.open()
    doc.new_page(width=10000, height=10000)
    raw = doc.tobytes()
    doc.close()
    result = run(raw)
    assert result.fusion.verdict.value == 'UNSUPPORTED'
    assert 'rendering budget' in result.processing_error


def test_actual_password_encryption_is_rejected():
    doc = fitz.open()
    doc.new_page()
    raw = doc.tobytes(encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw='owner', user_pw='secret')
    doc.close()
    result = run(raw)
    assert result.fusion.verdict.value == 'UNSUPPORTED'
    assert 'encrypted' in result.processing_error


def test_malformed_pdf_returns_explicit_failure():
    result = run(b'%PDF-1.7\nnot a valid pdf')
    assert result.fusion.verdict.value == 'UNSUPPORTED'
    assert result.processing_error


def test_partial_pair_coverage_is_reported(monkeypatch):
    from simulation.sample_generator import build_duplicate_sig_pdf
    monkeypatch.setattr(config, 'MAX_CANDIDATE_PAIRS', 1)
    result = run(build_duplicate_sig_pdf())
    assert result.coverage['pairs_analysed'] == 1
    assert result.coverage['complete'] is False
    assert result.coverage['limitations']


def test_corrupt_audit_is_not_empty_success(tmp_path):
    from core.audit_logger import verify_chain, append_record
    with open(config.AUDIT_LOG_PATH, 'w') as f:
        f.write('{broken')
    assert verify_chain()[0] is False
    with pytest.raises(ValueError):
        append_record('a'*64, 'INCONCLUSIVE')


def test_concurrent_audit_writes_preserve_all_records():
    from core.audit_logger import append_record, get_records, verify_chain
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda n: append_record(f'{n:064x}', 'INCONCLUSIVE'), range(30)))
    assert len(get_records()) == 30
    assert verify_chain()[0]


def test_checkpoint_detects_truncation():
    from core.audit_logger import append_record, export_checkpoint, verify_checkpoint
    append_record('a'*64, 'INCONCLUSIVE')
    checkpoint = export_checkpoint()
    with open(config.AUDIT_LOG_PATH, 'w') as f:
        json.dump([], f)
    assert verify_checkpoint(checkpoint)[0] is False


def test_audit_failure_visible_in_report(genuine, monkeypatch):
    import core.pipeline as pipeline
    def fail(*args):
        raise OSError('disk full')
    monkeypatch.setattr(pipeline, 'append_record', fail)
    result = run(genuine)
    from reporting.json_report import build_report
    assert 'disk full' in build_report(result)['audit_error']


def test_report_contains_coverage_and_policy(genuine):
    from reporting.json_report import build_report
    report = build_report(run(genuine))
    assert report['coverage']['pages_analysed'] == 1
    assert report['cryptographic']['signatures'][0]['revocation_status'].startswith('NOT CHECKED')
    assert report['cryptographic']['signatures'][0]['timestamp_status'] == 'NOT VALIDATED'


def test_explicit_test_root_and_unknown_issuer():
    from simulation.security_fixtures import certificate_chain
    from asn1crypto import pem, x509
    pair, root = certificate_chain()
    raw = signed_control(cert_pair=pair)
    untrusted = verify(raw).results[0]
    assert untrusted.integrity_status == 'PASS'
    assert untrusted.math_valid is True
    assert untrusted.trust_status == 'UNKNOWN ISSUER (untrusted)'
    trusted = verify(raw, trust_roots=[x509.Certificate.load(pem.unarmor(root)[2])]).results[0]
    assert trusted.trust_status == 'TRUSTED'
    assert trusted.math_valid is True
    assert trusted.revocation_status.startswith('NOT CHECKED')


def test_expired_certificate_never_reports_trusted():
    from simulation.security_fixtures import certificate_chain
    from asn1crypto import pem, x509
    pair, root = certificate_chain(expired=True)
    raw = signed_control(cert_pair=pair)
    sig = verify(raw, trust_roots=[x509.Certificate.load(pem.unarmor(root)[2])]).results[0]
    assert sig.integrity_status == 'PASS'
    assert sig.math_valid is True
    assert sig.trust_status == 'EXPIRED OR NOT YET VALID'
    assert sig.cert_trusted is False


def test_invalid_public_key_signature_is_detected(genuine):
    from asn1crypto import cms
    from pyhanko.pdf_utils.reader import PdfFileReader
    reader = PdfFileReader(io.BytesIO(genuine))
    sig = reader.embedded_signatures[0]
    _, length, second, _ = map(int, sig.sig_object['/ByteRange'])
    original_gap = genuine[length:second]
    content = bytes.fromhex(original_gap[1:-1].decode())
    parsed = cms.ContentInfo.load(content)
    signature = parsed['content']['signer_infos'][0]['signature'].native
    parsed['content']['signer_infos'][0]['signature'] = bytes([signature[0] ^ 1]) + signature[1:]
    replacement = parsed.dump().ljust(len(content), b'\0')
    changed = genuine[:length] + b'<' + replacement.hex().encode() + b'>' + genuine[second:]
    result = run(changed)
    assert result.crypto.results[0].integrity_status == 'PASS'
    assert result.crypto.results[0].math_valid is False
    assert 'CRYPTO-002' in codes(result)
    assert result.fusion.verdict.value == 'TAMPERING DETECTED'


def test_cross_page_duplicate_is_compared():
    from simulation.sample_generator import build_visual_only
    first = build_visual_only(sig_seed=77)
    with fitz.open(stream=first, filetype='pdf') as doc, fitz.open(stream=first, filetype='pdf') as second:
        doc.insert_pdf(second)
        raw = doc.tobytes()
    result = run(raw)
    assert any(pair['pages']==[0,1] and pair['geometric_match'] for pair in result.pair_results)
    assert 'ORB-001' in codes(result)


def test_memory_limit_failure_is_explicit(genuine, monkeypatch):
    import sys
    if sys.platform == 'win32':
        pytest.skip('Linux address-space enforcement')
    monkeypatch.setattr(config, 'WORKER_MEMORY_MB', 96)
    result = run(genuine)
    assert result.fusion.verdict.value == 'UNSUPPORTED'
    assert result.coverage['complete'] is False
    assert result.processing_error


def test_signature_limit_disclosed(genuine, monkeypatch):
    from simulation.signed_samples import sign_pdf, get_test_cert
    raw, message = sign_pdf(genuine, *get_test_cert(), field_name='Signature2')
    assert raw, message
    monkeypatch.setattr(config, 'MAX_SIGNATURES', 1)
    result = run(raw)
    assert result.crypto.total_sigs == 1
    assert result.crypto.all_valid is False
    assert result.coverage['complete'] is False
    assert any('signatures' in text for text in result.coverage['limitations'])


def test_interprocess_audit_writes_preserve_records():
    import subprocess
    import sys
    from core.audit_logger import get_records, verify_chain
    script = ('import config; config.AUDIT_LOG_PATH=' + repr(config.AUDIT_LOG_PATH) +
              '; from core.audit_logger import append_record; '
              '[append_record("a"*64,"INCONCLUSIVE") for _ in range(5)]')
    workers=[subprocess.Popen([sys.executable,'-c',script]) for _ in range(3)]
    assert all(p.wait(timeout=20)==0 for p in workers)
    assert len(get_records())==15
    assert verify_chain()[0]
