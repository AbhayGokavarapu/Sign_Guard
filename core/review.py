"""Human assessments are append-only session records, separate from machine findings."""
import hashlib
import json
from datetime import datetime,timezone

STATUSES=('Confirmed','Benign','Unresolved')


def finding_id(document_sha,finding):
    content={'document_sha256':document_sha,'code':finding.code,'page':finding.page,
             'description':finding.description,'measurements':finding.measurements}
    return hashlib.sha256(json.dumps(content,sort_keys=True,default=str).encode()).hexdigest()


def record_review(history,document_sha,finding,status,note,reviewer=''):
    if status not in STATUSES:raise ValueError('Choose Confirmed, Benign or Unresolved.')
    if not note.strip():raise ValueError('A review reason is required.')
    event={'document_sha256':document_sha,'finding_id':finding_id(document_sha,finding),
           'finding_code':finding.code,'assessment':status,'reason':note.strip()[:4000],
           'reviewer_claimed_name':reviewer.strip()[:120],
           'reviewer_identity':'Self-asserted; not authenticated by this application',
           'timestamp':datetime.now(timezone.utc).isoformat(),
           'previous_review_hash':history[-1]['review_hash'] if history else '0'*64}
    event['review_hash']=hashlib.sha256(json.dumps(event,sort_keys=True).encode()).hexdigest()
    return [*history,event]


def verify_reviews(history):
    previous='0'*64
    for event in history:
        body={k:v for k,v in event.items() if k!='review_hash'}
        if body.get('previous_review_hash')!=previous:return False
        expected=hashlib.sha256(json.dumps(body,sort_keys=True).encode()).hexdigest()
        if event.get('review_hash')!=expected:return False
        previous=expected
    return True
