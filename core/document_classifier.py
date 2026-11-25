"""
Module 2 — Signature classification.

Classifies a document as:
  CRYPTOGRAPHICALLY_SIGNED | VISUAL_CANDIDATE | UNSIGNED | UNSUPPORTED
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List

try:
    import pymupdf as fitz
except ImportError:
    import fitz

from core.pdf_parser import ParsedDocument


class DocClass(str, Enum):
    CRYPTOGRAPHICALLY_SIGNED = "Cryptographically Signed"
    VISUAL_CANDIDATE         = "Visual Signature Candidate"
    UNSIGNED                 = "Unsigned"
    UNSUPPORTED              = "Unsupported"


@dataclass
class ClassificationResult:
    doc_class:        DocClass
    crypto_sig_count: int
    visual_candidates: int
    explanation:      str
    completeness:     str
    details:          List[str] = field(default_factory=list)


# Minimum bounding-box size for a visual candidate (pixels at 96 dpi)
_MIN_BLOB_W = 60
_MIN_BLOB_H = 15
_MAX_BLOB_W = 600
_MAX_BLOB_H = 300


def classify(doc: ParsedDocument) -> ClassificationResult:
    if doc.error:
        return ClassificationResult(
            DocClass.UNSUPPORTED, 0, 0,
            f"Document could not be parsed: {doc.error}",
            "No analysis performed."
        )

    details: List[str] = []

    # ── 1. Cryptographic signature fields ─────────────────────────────────
    crypto_count = doc.sig_field_count
    if crypto_count:
        details.append(f"{crypto_count} cryptographic signature field(s) found: "
                       f"{', '.join(doc.sig_field_names)}.")

    # ── 2. AcroForm /Sig entries via raw xref scan ─────────────────────────
    extra_crypto = _scan_sig_dicts(doc.raw_bytes)
    if extra_crypto > crypto_count:
        crypto_count = extra_crypto
        details.append(f"Raw signature dictionary scan found {extra_crypto} entry/entries.")

    # ── 3. Visual candidates from rendered pages ───────────────────────────
    visual_count = _count_visual_candidates(doc)
    if visual_count:
        details.append(f"{visual_count} visual signature-like region(s) detected across pages.")

    # ── Verdict ────────────────────────────────────────────────────────────
    if crypto_count > 0:
        doc_class = DocClass.CRYPTOGRAPHICALLY_SIGNED
        explanation = (
            f"The document contains {crypto_count} embedded cryptographic signature "
            f"field(s).  Mathematical validity will be verified in Module 3."
        )
        completeness = "Full cryptographic and visual analysis applicable."
    elif visual_count > 0:
        doc_class = DocClass.VISUAL_CANDIDATE
        explanation = (
            f"No cryptographic signature fields found, but {visual_count} region(s) "
            f"resemble handwritten or stamped signatures.  "
            f"Only image-forensic checks are applicable."
        )
        completeness = "Visual forensic analysis applicable; cryptographic checks not applicable."
    else:
        doc_class = DocClass.UNSIGNED
        explanation = (
            "No cryptographic signature fields and no visual signature candidates "
            "were detected.  The document appears unsigned.  "
            "Absence of a signature does not establish that the content is authentic."
        )
        completeness = "Limited analysis applicable to unsigned documents."

    return ClassificationResult(
        doc_class=doc_class,
        crypto_sig_count=crypto_count,
        visual_candidates=visual_count,
        explanation=explanation,
        completeness=completeness,
        details=details,
    )


# ── Helpers ────────────────────────────────────────────────────────────────

def _scan_sig_dicts(raw: bytes) -> int:
    """Count /Sig type entries in the raw PDF byte stream."""
    count = 0
    try:
        doc = fitz.open(stream=raw, filetype="pdf")
        # Walk the xref table looking for signature dictionaries
        for xref in range(1, doc.xref_length()):
            try:
                obj_str = doc.xref_object(xref, compressed=False)
                if "/Type /Sig" in obj_str or "/Type/Sig" in obj_str:
                    count += 1
            except Exception:
                pass
        doc.close()
    except Exception:
        pass
    return count


def _count_visual_candidates(doc: ParsedDocument) -> int:
    """
    Heuristic: count image-xref objects whose bounding-box dimensions
    fall within the expected range for a handwritten / stamped signature.
    """
    total = 0
    try:
        pdf = fitz.open(stream=doc.raw_bytes, filetype="pdf")
        for page in pdf:
            for img_info in page.get_images(full=True):
                w = img_info[2]   # width  in pixels
                h = img_info[3]   # height
                if _MIN_BLOB_W <= w <= _MAX_BLOB_W and _MIN_BLOB_H <= h <= _MAX_BLOB_H:
                    total += 1
        pdf.close()
    except Exception:
        pass
    return total
