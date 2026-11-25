"""Create downloadable synthetic PDFs and verify every advertised upload outcome."""
from pathlib import Path
import csv
import hashlib
import json
import zipfile
import pymupdf as fitz
import config
from core.pipeline import run
from reporting.json_report import build_report
from simulation.security_fixtures import signed_control, tamper_signed, incremental_update, shadow_pair
from simulation.sample_generator import build_duplicate_sig_pdf, build_unsigned, build_multi_page_visual


def build():
    destination=Path(config.BASE_DIR)/'samples'/'upload-kit'
    destination.mkdir(parents=True,exist_ok=True)
    original=signed_control('Payment amount: $1,000')
    _,last_page=shadow_pair(pages=3,page_index=2)
    cases=[
        ('01_signed_original.pdf','Signed original','A genuine test signature with intact signed bytes. The test certificate does not establish signer identity.',original,'INCONCLUSIVE',None),
        ('02_tampered_signed_bytes.pdf','Tampered signed bytes','The original PDF with signed metadata changed. It looks identical to sample 01, but byte integrity must fail.',tamper_signed(original),'TAMPERING DETECTED','CRYPTO-001'),
        ('03_changed_after_signing.pdf','Changed after signing','The same signed original with a valid appended revision changing the displayed payment to $9,000. Signed bytes remain intact.',incremental_update(original,'Payment amount: $9,000'),'REVIEW REQUIRED','SHADOW-001'),
        ('04_duplicated_signature_images.pdf','Duplicated signature images','Two matching synthetic handwriting images. Geometric similarity warrants review; it does not prove theft.',build_duplicate_sig_pdf(),'REVIEW REQUIRED','ORB-001'),
        ('05_unsigned_document.pdf','Unsigned document','An ordinary unsigned PDF. Absence of a signature is not evidence of forgery.',build_unsigned('Unsigned purchase agreement.\nReference: DEMO-005\nNo digital signature is present.'),'INCONCLUSIVE',None),
        ('06_change_on_last_page.pdf','Change on the last page','A three-page signed PDF with a post-signing content replacement on page 3.',last_page,'REVIEW REQUIRED','SHADOW-001'),
        ('07_signature_on_last_page.pdf','Visual signature on the last page','A three-page unsigned agreement with a handwritten-image candidate only on its final page.',build_multi_page_visual(pages=3,sig_seed=7),'INCONCLUSIVE',None),
    ]
    rows=[]
    reports=destination/'verification';reports.mkdir(exist_ok=True)
    for filename,title,description,raw,expected,required in cases:
        (destination/filename).write_bytes(raw)
        with fitz.open(stream=raw,filetype='pdf') as pdf:
            pages=len(pdf)
            assert pages>0
            for page in pdf:page.get_pixmap(matrix=fitz.Matrix(.25,.25))
        result=run(raw,filename,record_audit=False)
        assert not result.processing_error,(filename,result.processing_error)
        observed=result.fusion.verdict.value
        codes=sorted({finding.code for finding in result.fusion.findings})
        assert observed==expected,(filename,observed,expected)
        assert required is None or required in codes,(filename,codes)
        if filename.startswith('01'):
            sig=result.crypto.results[0]
            assert sig.integrity_status=='PASS' and sig.math_valid is True
        if filename.startswith('02'):assert result.crypto.results[0].integrity_status=='FAIL'
        if filename.startswith('03'):assert result.crypto.results[0].integrity_status=='PASS'
        if filename.startswith('06'):assert any(f.code=='SHADOW-001' and f.page==2 for f in result.fusion.findings)
        if filename.startswith('07'):assert result.page_results[2]['candidate_count']>0
        row={'file':filename,'title':title,'description':description,'pages':pages,
             'expected_verdict':expected,'observed_verdict':observed,
             'integrity':result.fusion.integrity_verdict.value,'finding_codes':codes,
             'sha256':hashlib.sha256(raw).hexdigest(),'verified':True}
        rows.append(row)
        (reports/(Path(filename).stem+'.json')).write_text(json.dumps(build_report(result),indent=2,default=str))
        print(filename,observed,codes,flush=True)
    with fitz.open(stream=original,filetype='pdf') as a, fitz.open(stream=cases[1][3],filetype='pdf') as b:
        assert a[0].get_pixmap().samples==b[0].get_pixmap().samples
    (destination/'verified_results.json').write_text(json.dumps(rows,indent=2))
    with (destination/'verified_results.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['file','pages','expected_verdict','observed_verdict','integrity','finding_codes','verified'],extrasaction='ignore',lineterminator='\n')
        writer.writeheader();writer.writerows(rows)
    instructions='''SIGNGUARD - READY-TO-UPLOAD SAMPLE KIT

All documents are synthetic and safe to use for this demonstration.

HOW TO USE
1. Extract signguard-upload-kit.zip on your computer.
2. Open SignGuard and select Document analysis.
3. Upload ONE numbered PDF, then click Run document analysis.
4. Compare the outcome with the list below.
5. Open Digital signatures, Document revisions and Coverage for the explanation.
6. Download your PDF report or JSON evidence after the analysis.

START WITH FILES 01, 02, AND 03 IN THAT ORDER.

EXPECTED AND LOCALLY OBSERVED OUTCOMES
'''
    for row in rows:
        instructions+=f'\n{row["file"]}\n  Result: {row["observed_verdict"]}\n  Integrity: {row["integrity"]}\n  {row["description"]}\n'
    instructions+='''
IMPORTANT INTERPRETATION
- INCONCLUSIVE does not mean forged. An intact test signature cannot certify a real person's identity.
- Samples 01 and 02 look the same. Signed-byte tampering does not need a visible page difference.
- Sample 03 keeps the original signature's bytes intact but changes visible content in a later revision.
- REVIEW REQUIRED is an investigation alert, not proof of fraud.
- Samples 06 and 07 demonstrate analysis beyond the first page.
- Upload the numbered source PDFs, not a generated forensic report or the ZIP archive.
- verification/ contains engine reports from the local validation run; verified_results.csv/JSON contains the comparison.
- These checks used the repository's current engine. The hosted site's results were not independently verified because its URL is blocked from the workspace.
'''
    (destination/'START_HERE.txt').write_text(instructions)
    archive=destination.parent/'signguard-upload-kit.zip'
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for file in sorted(destination.rglob('*')):
            if file.is_file():z.write(file,file.relative_to(destination))
    print('KIT VERIFIED:',len(rows),'PDFs;',archive.stat().st_size,'ZIP bytes')
    return rows


if __name__=='__main__':build()
