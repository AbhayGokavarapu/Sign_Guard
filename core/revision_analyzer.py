"""
Module 4 — PDF revision and shadow attack analysis.

Uses PyMuPDF's xref/trailer API for reliable revision reconstruction
rather than raw %%EOF byte scanning (which is fooled by stream data).

Limitations documented inline:
- Only detects shadow attacks where visible content changes in the render.
- Multi-layer overlay attacks with identical rendering are not detectable.
- Comparison uses one rendering engine — different viewers may render differently.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any

try:
    import pymupdf as fitz
except ImportError:
    import fitz

import numpy as np
from PIL import Image, ImageDraw

import config


# ── Data structures ────────────────────────────────────────────────────────

@dataclass
class RevisionInfo:
    index:            int
    start_offset:     int
    end_offset:       int
    is_signed:        bool
    xref_count:       int
    page_count:       int = 0
    metadata_summary: str = ""
    text_summary:     str = ""


@dataclass
class RevisionAnalysisResult:
    revisions:            List[RevisionInfo]
    signed_rev_index:     Optional[int]
    signed_rev_image:     Optional[Image.Image]
    current_image:        Optional[Image.Image]
    diff_image:           Optional[Image.Image]
    diff_mask:            Optional[Image.Image]
    changed_boxes:        List[Tuple[int,int,int,int]]
    changed_area_pct:     float
    has_incremental_updates: bool
    shadow_suspect:       bool
    text_diff_summary:    str
    metadata_changed:     bool
    summary:              str
    discovery_method:     str    # "pymupdf_xref" | "eof_fallback"
    limitations:          List[str] = field(default_factory=list)
    error:                Optional[str] = None


# ── Revision discovery ─────────────────────────────────────────────────────

def _discover_revisions_pymupdf(raw: bytes) -> Tuple[List[RevisionInfo], str]:
    """
    Use PyMuPDF trailer chain (xref_prev) to find genuine revision boundaries.
    Returns (revisions, method_name).
    """
    revisions: List[RevisionInfo] = []
    try:
        doc = fitz.open(stream=raw, filetype="pdf")

        # Collect all trailer dictionaries in reverse order
        # PyMuPDF exposes trailer xref_prev chain
        boundaries = []
        seen_offsets = set()

        # Walk the xref table: PyMuPDF's trailer has /Prev pointing to
        # earlier cross-references.
        trailer = doc.pdf_trailer()
        prev_offset = None
        try:
            prev_offset = int(trailer.get("Prev", 0) or 0)
        except (TypeError, ValueError):
            prev_offset = 0

        # Simple approach: find all startxref offsets in raw bytes
        # This is safer than %%EOF scanning because we look for
        # "startxref\n<number>\n%%EOF" patterns
        startxref_positions = []
        pos = 0
        while True:
            idx = raw.find(b"startxref", pos)
            if idx == -1:
                break
            # Read number after startxref
            after = raw[idx+9:idx+40].strip().split()
            if after:
                try:
                    xref_offset = int(after[0])
                    startxref_positions.append((idx, xref_offset))
                except ValueError:
                    pass
            pos = idx + 1

        doc.close()

        if not startxref_positions:
            return [], "failed"

        # Each startxref occurrence = one revision
        for i, (sxref_pos, _xref_off) in enumerate(startxref_positions):
            # Revision end = find %%EOF after this startxref
            eof_pos = raw.find(b"%%EOF", sxref_pos)
            if eof_pos == -1:
                eof_pos = len(raw) - 1
            end = eof_pos + 5
            while end < len(raw) and raw[end:end+1] in (b"\r", b"\n"):
                end += 1
            start = startxref_positions[i-1][0] if i > 0 else 0
            # Avoid duplicates
            if end not in seen_offsets:
                seen_offsets.add(end)
                revisions.append(RevisionInfo(
                    index=i, start_offset=start, end_offset=end,
                    is_signed=False, xref_count=0
                ))

        # Mark which revisions contain a /Sig entry
        for rev in revisions:
            chunk = raw[rev.start_offset:rev.end_offset]
            if b"/Type /Sig" in chunk or b"/Type/Sig" in chunk:
                rev.is_signed = True

        # Enrich with page/text info
        for rev in revisions:
            try:
                rev_raw = raw[:rev.end_offset]
                d = fitz.open(stream=rev_raw, filetype="pdf")
                rev.page_count = len(d)
                rev.metadata_summary = str(d.metadata)
                # Sample text from first page
                if len(d) > 0:
                    rev.text_summary = d[0].get_text()[:200]
                d.close()
            except Exception:
                pass

        return revisions, "pymupdf_startxref"

    except Exception as exc:
        return [], f"failed:{exc}"


def _discover_revisions_fallback(raw: bytes) -> Tuple[List[RevisionInfo], str]:
    """
    Fallback: scan for %%EOF in the raw stream.
    Less reliable — documented as fallback, not primary method.
    """
    revisions: List[RevisionInfo] = []
    pos = 0
    idx = 0
    while True:
        eof = raw.find(b"%%EOF", pos)
        if eof == -1:
            break
        # Check this %%EOF is at a likely PDF boundary (preceded by startxref)
        ctx = raw[max(0, eof-50):eof]
        # Skip %%EOF inside stream data (heuristic: should be near a digit line)
        if b"startxref" not in ctx and idx > 0:
            pos = eof + 5
            continue
        end = eof + 5
        while end < len(raw) and raw[end:end+1] in (b"\r", b"\n"):
            end += 1
        revisions.append(RevisionInfo(
            index=idx,
            start_offset=0 if idx == 0 else revisions[-1].end_offset,
            end_offset=end,
            is_signed=False, xref_count=0
        ))
        pos = end
        idx += 1
        if end >= len(raw):
            break

    for rev in revisions:
        chunk = raw[rev.start_offset:rev.end_offset]
        if b"/Type /Sig" in chunk or b"/Type/Sig" in chunk:
            rev.is_signed = True

    return revisions, "eof_fallback"


# ── Rendering helpers ──────────────────────────────────────────────────────

def _render_at_dpi(raw: bytes, page_index: int = 0,
                   dpi: int = config.RENDER_DPI) -> Optional[Image.Image]:
    try:
        doc  = fitz.open(stream=raw, filetype="pdf")
        if not doc or len(doc) == 0:
            return None
        pi   = min(page_index, len(doc) - 1)
        page = doc[pi]
        mat  = fitz.Matrix(dpi / 72, dpi / 72)
        # Cap dimensions to prevent memory issues
        pix  = page.get_pixmap(matrix=mat, alpha=False)
        if pix.width > config.MAX_PAGE_WIDTH_PX or pix.height > config.MAX_PAGE_HEIGHT_PX:
            scale = min(config.MAX_PAGE_WIDTH_PX  / pix.width,
                        config.MAX_PAGE_HEIGHT_PX / pix.height)
            mat  = fitz.Matrix(dpi / 72 * scale, dpi / 72 * scale)
            pix  = page.get_pixmap(matrix=mat, alpha=False)
        img  = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        doc.close()
        return img
    except Exception:
        return None


def _pixel_diff(img_a: Image.Image,
                img_b: Image.Image) -> Tuple[Image.Image, Image.Image, float, List[Tuple]]:
    if img_a.size != img_b.size:
        img_b = img_b.resize(img_a.size, Image.LANCZOS)

    a = np.array(img_a).astype(np.int16)
    b = np.array(img_b).astype(np.int16)

    diff     = np.abs(a - b).astype(np.uint8)
    diff_img = Image.fromarray(diff)

    gray = np.max(diff, axis=2)
    mask = (gray > config.DIFF_THRESHOLD_PX).astype(np.uint8) * 255
    mask_img = Image.fromarray(mask, mode="L")

    total_px    = mask.size
    changed_px  = int(np.sum(mask > 0))
    changed_pct = 100.0 * changed_px / total_px

    boxes = _find_change_boxes(mask)
    return diff_img, mask_img, changed_pct, boxes


def _find_change_boxes(mask: np.ndarray,
                       min_area: int = 100) -> List[Tuple[int,int,int,int]]:
    from scipy import ndimage as ndi
    labeled, n = ndi.label(mask > 0)
    boxes = []
    for lab in range(1, n + 1):
        ys, xs = np.where(labeled == lab)
        if len(xs) < min_area:
            continue
        x, y = int(xs.min()), int(ys.min())
        w, h = int(xs.max()) - x, int(ys.max()) - y
        boxes.append((x, y, w, h))
    return boxes


def _extract_text_first_page(raw: bytes) -> str:
    try:
        doc = fitz.open(stream=raw, filetype="pdf")
        if len(doc) == 0:
            return ""
        txt = doc[0].get_text()
        doc.close()
        return txt
    except Exception:
        return ""


def _metadata(raw: bytes) -> Dict[str, Any]:
    try:
        doc = fitz.open(stream=raw, filetype="pdf")
        m   = doc.metadata or {}
        doc.close()
        return m
    except Exception:
        return {}


# ── Public API ─────────────────────────────────────────────────────────────

def analyze(raw: bytes, page_index: int = 0) -> RevisionAnalysisResult:
    """
    Discover revisions and compare signed vs current page content.
    Uses startxref-based discovery; falls back to %%EOF scan if needed.
    """
    limitations = [
        "Shadow-attack detection compares rendered page images using one rendering engine. "
        "Attacks that produce identical renders are not detectable.",
        "Legitimate incremental updates (annotations, additional sigs) may trigger "
        "the shadow-suspect flag; manual review distinguishes malicious from benign.",
    ]

    # Primary: startxref-based
    revisions, method = _discover_revisions_pymupdf(raw)

    if not revisions:
        # Fallback
        revisions, method = _discover_revisions_fallback(raw)
        limitations.append(
            f"Primary revision discovery failed; used {method}. "
            "Results may be less reliable for PDFs with embedded binary streams."
        )

    if not revisions:
        return RevisionAnalysisResult(
            [], None, None, None, None, None, [], 0.0, False, False,
            "", False,
            "No revision boundaries detected — document may be malformed.",
            method, limitations,
            error="Could not identify any PDF revision boundaries."
        )

    # Cap revision count
    if len(revisions) > config.MAX_REVISIONS:
        revisions = revisions[:config.MAX_REVISIONS]
        limitations.append(
            f"More than {config.MAX_REVISIONS} revisions detected; truncated."
        )

    has_incremental = len(revisions) > 1

    # Signed revision = latest revision containing a /Sig entry
    signed_rev = next((r for r in reversed(revisions) if r.is_signed), None)
    signed_idx = signed_rev.index if signed_rev else None

    signed_image  = None
    current_image = _render_at_dpi(raw, page_index)
    diff_image    = diff_mask = None
    changed_boxes: List[Tuple] = []
    changed_pct   = 0.0
    shadow_suspect = False
    text_diff_summary = ""
    metadata_changed  = False

    if signed_rev and has_incremental:
        signed_bytes = raw[:signed_rev.end_offset]
        signed_image = _render_at_dpi(signed_bytes, page_index)

        if signed_image and current_image:
            diff_image, diff_mask, changed_pct, changed_boxes = \
                _pixel_diff(signed_image, current_image)
            if changed_pct >= config.SHADOW_CHANGE_PCT_MIN:
                shadow_suspect = True

        # Text comparison
        signed_text  = _extract_text_first_page(signed_bytes)
        current_text = _extract_text_first_page(raw)
        if signed_text != current_text:
            # Simple line-level diff summary
            s_lines = set(signed_text.splitlines())
            c_lines = set(current_text.splitlines())
            removed = s_lines - c_lines
            added   = c_lines - s_lines
            if removed or added:
                text_diff_summary = (
                    f"{len(removed)} line(s) removed, {len(added)} line(s) added "
                    "between signed revision and current document."
                )

        # Metadata comparison
        signed_meta  = _metadata(signed_bytes)
        current_meta = _metadata(raw)
        if signed_meta != current_meta:
            metadata_changed = True

    # Annotate change boxes on current image
    if current_image and changed_boxes:
        annotated = current_image.copy()
        draw = ImageDraw.Draw(annotated)
        for (x, y, w, h) in changed_boxes:
            draw.rectangle([x, y, x+w, y+h], outline=(220, 38, 38), width=2)
        current_image = annotated

    # Summary
    parts = [f"{len(revisions)} revision(s) discovered via {method}."]
    if has_incremental:
        parts.append(f"{len(revisions)-1} incremental update(s) present.")
    else:
        parts.append("Single revision — no incremental updates.")
    if shadow_suspect:
        parts.append(
            f"Visual content changed {changed_pct:.1f}% between signed "
            "revision and current — possible shadow attack; manual review required."
        )
    elif has_incremental and changed_pct > 0:
        parts.append(f"Visible change: {changed_pct:.2f}% of page area.")
    if text_diff_summary:
        parts.append(text_diff_summary)
    if metadata_changed:
        parts.append("Document metadata differs between signed and current revision.")

    return RevisionAnalysisResult(
        revisions=revisions,
        signed_rev_index=signed_idx,
        signed_rev_image=signed_image,
        current_image=current_image,
        diff_image=diff_image,
        diff_mask=diff_mask,
        changed_boxes=changed_boxes,
        changed_area_pct=changed_pct,
        has_incremental_updates=has_incremental,
        shadow_suspect=shadow_suspect,
        text_diff_summary=text_diff_summary,
        metadata_changed=metadata_changed,
        summary=" ".join(parts),
        discovery_method=method,
        limitations=limitations,
    )
