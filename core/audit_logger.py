"""
Module 12 — Hash-chained audit logging.

Each record contains a SHA-256 hash of its own content plus the
previous record's hash, forming a tamper-evident chain.

IMPORTANT LIMITATIONS:
- A broken chain indicates an integrity inconsistency but does NOT
  conclusively prove malicious tampering. It may be caused by log
  corruption, incomplete writes, or software bugs.
- Detecting truncation or a full chain rewrite requires an independently
  protected chain head (e.g. stored separately and compared).
- Sensitive document content is never stored in audit records.
"""

from __future__ import annotations

import hashlib, json, os, tempfile, time, uuid
from dataclasses import asdict, dataclass
from typing import List, Optional, Tuple

import config


@dataclass
class AuditRecord:
    event_id:    str
    timestamp:   str
    doc_hash:    str    # SHA-256 of document — not document content
    verdict:     str
    prev_hash:   str
    record_hash: str


def _hash_record(event_id: str, timestamp: str,
                 doc_hash: str, verdict: str, prev_hash: str) -> str:
    """Deterministic SHA-256 of all record fields."""
    payload = "|".join([event_id, timestamp, doc_hash, verdict, prev_hash])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _load_chain() -> List[dict]:
    if not os.path.exists(config.AUDIT_LOG_PATH):
        return []
    try:
        with open(config.AUDIT_LOG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return []
        return data
    except (json.JSONDecodeError, OSError):
        return []


def _save_chain(chain: List[dict]) -> None:
    """Write atomically to avoid partial writes corrupting the chain."""
    os.makedirs(os.path.dirname(config.AUDIT_LOG_PATH), exist_ok=True)
    dir_path = os.path.dirname(config.AUDIT_LOG_PATH)
    fd, tmp_path = tempfile.mkstemp(dir=dir_path, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(chain, f, indent=2)
        os.replace(tmp_path, config.AUDIT_LOG_PATH)
    except Exception:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
        raise


def append_record(doc_hash: str, verdict: str) -> AuditRecord:
    """Append a new record to the chain. Thread-safe via atomic replace."""
    chain    = _load_chain()
    prev_h   = chain[-1]["record_hash"] if chain else "0" * 64
    event_id = str(uuid.uuid4())
    ts       = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    rec_hash = _hash_record(event_id, ts, doc_hash, verdict, prev_h)

    record = AuditRecord(event_id, ts, doc_hash, verdict, prev_h, rec_hash)
    chain.append(asdict(record))
    _save_chain(chain)
    return record


def verify_chain() -> Tuple[bool, str]:
    """
    Walk the entire chain verifying each record hash and prev_hash linkage.
    Returns (is_intact, human_readable_message).
    """
    chain = _load_chain()
    if not chain:
        return True, "Audit chain is empty — no records to verify."

    prev_hash = "0" * 64

    for i, rec in enumerate(chain):
        # Validate required fields exist
        required = ("event_id", "timestamp", "doc_hash", "verdict",
                    "prev_hash", "record_hash")
        missing  = [k for k in required if k not in rec]
        if missing:
            return False, (
                f"Record {i} is missing fields: {missing}. "
                "Chain integrity cannot be verified."
            )

        # Check prev_hash linkage
        if rec["prev_hash"] != prev_hash:
            return False, (
                f"Link broken at record {i} (event_id={rec.get('event_id','?')}): "
                f"expected prev_hash={prev_hash[:16]}… "
                f"got {rec['prev_hash'][:16]}…"
            )

        # Recompute record_hash
        expected = _hash_record(
            rec["event_id"], rec["timestamp"],
            rec["doc_hash"], rec["verdict"], prev_hash
        )
        if expected != rec["record_hash"]:
            return False, (
                f"Record {i} hash mismatch (event_id={rec.get('event_id','?')}): "
                "content may have been modified. "
                "Note: a broken chain indicates an integrity inconsistency but "
                "does not conclusively prove malicious tampering."
            )

        prev_hash = rec["record_hash"]

    return True, (
        f"Audit chain is intact ({len(chain)} record(s) verified). "
        "Note: detecting truncation requires an independently protected chain head."
    )


def get_records() -> List[dict]:
    return _load_chain()
