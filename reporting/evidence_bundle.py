"""Reviewable evidence packages with explicit integrity and provenance boundaries."""
import hashlib
import io
import json
import os
from pathlib import Path
import zipfile
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer
from reportlab.lib.styles import getSampleStyleSheet
from xml.sax.saxutils import escape
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey,Ed25519PublicKey


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,default=str).encode()


def _png(image):
    buffer=io.BytesIO();image.save(buffer,'PNG');return buffer.getvalue()


def comparison_pdf(comparison):
    from core.document_diff import public_comparison
    data=public_comparison(comparison)
    output=io.BytesIO();styles=getSampleStyleSheet()
    story=[Paragraph('SignGuard Document Comparison',styles['Title']),
           Paragraph('Differences do not by themselves establish forgery. Source PDFs are aligned by page position.',styles['BodyText'])]
    for key in ('original','suspect'):
        identity=data.get(key,{})
        story.append(Paragraph(escape(f"{key.title()}: {identity.get('filename','')} | SHA-256 {identity.get('sha256','')}"),styles['BodyText']))
    for row in data.get('pages',[]):
        story.extend([Spacer(1,10),Paragraph(escape(f"Page {row['page']+1}: {row['change']}"),styles['Heading2'])])
        for change in row.get('text_changes',[]):
            story.append(Paragraph(escape('Removed: '+' | '.join(change['removed'])[:5000]),styles['BodyText']))
            story.append(Paragraph(escape('Added: '+' | '.join(change['added'])[:5000]),styles['BodyText']))
    SimpleDocTemplate(output).build(story)
    return output.getvalue()


def build_bundle(result=None,comparison=None,reviews=None,include_source=False):
    files={}
    if result:
        from reporting.json_report import build_report,_safe
        from reporting.pdf_report import build_pdf_report
        files['report.json']=canonical(_safe(build_report(result)))
        files['report.pdf']=build_pdf_report(result)
        files['provenance.json']=canonical(result.provenance)
        for name,image in [('signature_regions',result.localization.annotated if result.localization else None),
                           ('ela_residual',result.ela.raw_diff if result.ela else None),
                           ('revision_difference',result.revision.diff_image if result.revision else None),
                           ('geometric_matches',result.ransac.inlier_vis if result.ransac else None)]:
            if image is not None:files['images/'+name+'.png']=_png(image)
        if include_source and result.parsed:files['source/document.pdf']=result.parsed.raw_bytes
    if comparison:
        from core.document_diff import public_comparison
        files['comparison.json']=canonical(public_comparison(comparison))
        files['comparison.pdf']=comparison_pdf(comparison)
        for row in comparison.get('images',[]):
            for name in ('original','suspect','difference'):files[f'comparison/page-{row["page"]+1}-{name}.png']=row[name]
    if not files:raise ValueError('No analysis or comparison evidence to export.')
    if reviews:
        from core.review import verify_reviews,finding_id
        if not verify_reviews(reviews):raise ValueError('Human review history is inconsistent.')
        if result and result.parsed:
            known={finding_id(result.parsed.sha256,f) for f in result.fusion.findings}
            if any(r['document_sha256']!=result.parsed.sha256 or r['finding_id'] not in known for r in reviews):
                raise ValueError('Human review does not belong to the supplied machine findings.')
    files['human_review.json']=canonical(reviews or [])
    files['VERIFY.txt']=b'''Verify without extracting: python tools/verify_evidence.py package.zip
For an independently retained reference: add --expected-manifest-sha256 HASH
For an operator signature: add --trusted-public-key operator-public.pem
Checksums alone detect inconsistencies, not a full rewrite. Retain the manifest hash
or signing public key through an independent channel. Embedded keys are not trust anchors.
Reviewers are self-asserted, and machine findings remain unchanged.
'''
    manifest={'format':'SignGuard evidence package','version':1,
              'files':{name:{'sha256':hashlib.sha256(data).hexdigest(),'size':len(data)} for name,data in sorted(files.items())}}
    manifest_bytes=canonical(manifest)
    manifest_sha=hashlib.sha256(manifest_bytes).hexdigest()
    signing_key=os.environ.get('SIGNGUARD_EVIDENCE_SIGNING_KEY')
    if signing_key:
        private=serialization.load_pem_private_key(Path(signing_key).read_bytes(),password=None)
        if not isinstance(private,Ed25519PrivateKey):raise ValueError('Evidence signing requires an Ed25519 PEM private key.')
        files['manifest.sig']=private.sign(manifest_bytes)
        files['signer-public.pem']=private.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo)
    files['manifest.json']=manifest_bytes
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
        for name,data in sorted(files.items()):archive.writestr(name,data)
    return output.getvalue(),manifest_sha


def verify_bundle(raw,expected_manifest_sha256=None,trusted_public_key=None):
    """Never extract or execute package contents. Reject traversal, duplicates and oversized members."""
    from pathlib import PurePosixPath
    if len(raw)>100*1024*1024:return {'valid':False,'error':'Archive exceeds size limit.'}
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            infos=archive.infolist();names=[i.filename for i in infos]
            if len(infos)>500 or len(names)!=len(set(names)):raise ValueError('Too many or duplicate archive entries.')
            if sum(i.file_size for i in infos)>100*1024*1024:raise ValueError('Uncompressed size exceeds limit.')
            for name in names:
                p=PurePosixPath(name)
                if p.is_absolute() or '..' in p.parts or '\\' in name:raise ValueError('Unsafe archive path.')
            manifest_info=archive.getinfo('manifest.json')
            if manifest_info.file_size>1024*1024:raise ValueError('Manifest exceeds limit.')
            manifest_bytes=archive.read('manifest.json');manifest=json.loads(manifest_bytes)
            if manifest.get('format')!='SignGuard evidence package' or manifest.get('version')!=1:raise ValueError('Unsupported manifest format.')
            entries=manifest['files']
            if not isinstance(entries,dict):raise ValueError('Invalid manifest members.')
            signed='manifest.sig' in names or 'signer-public.pem' in names
            required=set(entries)|{'manifest.json'}|({'manifest.sig','signer-public.pem'} if signed else set())
            if set(names)!=required:raise ValueError('Manifest membership mismatch.')
            manifest_sha=hashlib.sha256(manifest_bytes).hexdigest()
            if expected_manifest_sha256 and expected_manifest_sha256.lower()!=manifest_sha:raise ValueError('Independent manifest reference does not match.')
            for name,entry in entries.items():
                info=archive.getinfo(name)
                if info.file_size!=entry['size']:raise ValueError('Size mismatch: '+name)
                digest=hashlib.sha256()
                with archive.open(name) as handle:
                    while True:
                        block=handle.read(1024*1024)
                        if not block:break
                        digest.update(block)
                if digest.hexdigest()!=entry['sha256']:raise ValueError('Checksum mismatch: '+name)
            signer_trusted=False;signature_valid=None
            if signed:
                embedded=archive.read('signer-public.pem')
                key_bytes=trusted_public_key or embedded
                key=serialization.load_pem_public_key(key_bytes)
                embedded_key=serialization.load_pem_public_key(embedded)
                if trusted_public_key and key.public_bytes(serialization.Encoding.DER,serialization.PublicFormat.SubjectPublicKeyInfo)!=embedded_key.public_bytes(serialization.Encoding.DER,serialization.PublicFormat.SubjectPublicKeyInfo):
                    raise ValueError('Embedded signing key does not match the independent trust key.')
                if not isinstance(key,Ed25519PublicKey):raise ValueError('Unsupported signing key.')
                key.verify(archive.read('manifest.sig'),manifest_bytes)
                signature_valid=True;signer_trusted=trusted_public_key is not None
            elif trusted_public_key:raise ValueError('Package has no operator signature.')
            if 'human_review.json' in entries:
                from core.review import verify_reviews
                if not verify_reviews(json.loads(archive.read('human_review.json'))):raise ValueError('Human review chain is inconsistent.')
            return {'valid':True,'manifest_sha256':manifest_sha,'files_checked':len(entries),
                    'signature_valid':signature_valid,'signer_trusted':signer_trusted,
                    'independent_reference_matches':bool(expected_manifest_sha256),
                    'note':'Checksums establish consistency. Authenticity requires an independently trusted manifest reference or operator signing key.'}
    except Exception as exc:return {'valid':False,'error':f'{type(exc).__name__}: {exc}'}
