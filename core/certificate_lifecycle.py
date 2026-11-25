"""Offline CRL/OCSP and RFC3161 validation support via pyHanko's validation contexts.

No URLs taken from a PDF are fetched. Operators provision evidence files under
SIGNGUARD_REVOCATION_DIR; stale, untrusted or unrelated evidence cannot imply GOOD.
"""
from pathlib import Path
from asn1crypto import crl,ocsp,pem
import config


def load_evidence():
    crls=[];ocsps=[]
    if not config.REVOCATION_DIR:return crls,ocsps
    directory=Path(config.REVOCATION_DIR)
    if not directory.is_dir():raise ValueError('Configured offline revocation evidence directory is unavailable.')
    files=sorted(p for p in directory.iterdir() if p.suffix.lower() in ('.crl','.ocsp','.der','.pem'))
    if len(files)>30:raise ValueError('Too many offline revocation evidence files.')
    for file in files:
        raw=file.read_bytes()
        if len(raw)>2*1024*1024:raise ValueError('Offline revocation evidence exceeds its size budget.')
        if pem.detect(raw):_,_,raw=pem.unarmor(raw)
        if file.suffix.lower()=='.ocsp':ocsps.append(ocsp.OCSPResponse.load(raw));continue
        try:
            item=crl.CertificateList.load(raw);item.native;crls.append(item)
        except Exception:
            item=ocsp.OCSPResponse.load(raw);item.native;ocsps.append(item)
    return crls,ocsps


def revocation_result(status,evidence_supplied):
    problem=str(getattr(status,'trust_problem_indic','') or '').upper()
    details=getattr(status,'revocation_details',None)
    if details is not None or 'REVOKED' in problem:return 'REVOKED'
    if not evidence_supplied:return 'NOT CHECKED (offline)'
    if getattr(status,'trusted',False):return 'GOOD (validated offline evidence)'
    return 'UNKNOWN (offline evidence did not establish a trusted, current non-revoked path)'


def timestamp_result(status,is_document_timestamp=False):
    ts=status if is_document_timestamp else getattr(status,'timestamp_validity',None)
    if ts is None:return 'NOT VALIDATED',{'present':False,'note':'No RFC3161 signature timestamp was validated; a claimed signing date is not a trusted timestamp.'}
    intact=getattr(ts,'intact',None);valid=getattr(ts,'valid',None);trusted=getattr(ts,'trusted',False)
    if intact is False or valid is False:label='INVALID TIMESTAMP'
    elif intact is True and valid is True and trusted:label='VALID / TRUSTED TSA'
    elif intact is True and valid is True:label='VALID / UNTRUSTED TSA'
    else:label='UNKNOWN TIMESTAMP'
    return label,{'present':True,'intact':intact,'math_valid':valid,'tsa_trusted':trusted,
        'timestamp':str(getattr(ts,'timestamp','')),
        'revocation_problem':str(getattr(ts,'trust_problem_indic','') or ''),
        'note':'TSA trust depends on explicit roots and available revocation evidence; this is not complete long-term archival validation.'}
