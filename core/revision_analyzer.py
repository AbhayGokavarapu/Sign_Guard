"""
Module 4 — PDF revision and shadow attack analysis.

Uses pyHanko's parsed xref chain for reliable revision reconstruction
rather than raw %%EOF byte scanning (which is fooled by stream data).

Limitations documented inline:
- Only detects shadow attacks where visible content changes in the render.
- Multi-layer overlay attacks with identical rendering are not detectable.
- Comparison uses one rendering engine — different viewers may render differently.
"""

from __future__ import annotations

import io, re
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
    page_index: int = 0
    affected_pages: List[int] = field(default_factory=list)
    pages_compared: int = 0


# ── Revision discovery ─────────────────────────────────────────────────────

def _discover_revisions_pymupdf(raw: bytes) -> Tuple[List[RevisionInfo], str]:
    """Resolve revision offsets from pyHanko's parsed /Prev xref chain.

    Raw startxref strings only locate the EOF belonging to each verified offset;
    arbitrary tokens in content streams cannot introduce additional revisions.
    """
    from pyhanko.pdf_utils.reader import PdfFileReader
    try:
        reader = PdfFileReader(io.BytesIO(raw), strict=True)
        if reader.xrefs.total_revisions > config.MAX_REVISIONS:
            return [], "failed:revision limit exceeded"
        signed = {sig.signed_revision for sig in reader.embedded_signatures}
        boundaries = list(re.finditer(rb"startxref\s+(\d+)\s+%%EOF[\r\n]*", raw))
        revisions = []
        previous_end = 0
        for i in range(reader.xrefs.total_revisions):
            offset = reader.xrefs.get_startxref_for_revision(i)
            candidates = [m for m in boundaries if int(m.group(1)) == offset and m.start() >= offset and m.end() > previous_end]
            if not candidates:
                raise ValueError("Missing EOF for parsed xref revision")
            end = candidates[0].end()
            with fitz.open(stream=raw[:end], filetype="pdf") as doc:
                revisions.append(RevisionInfo(i, previous_end, end, i in signed,
                    doc.xref_length(), len(doc), str(doc.metadata),
                    doc[0].get_text()[:200] if len(doc) else ""))
            previous_end = end
        return revisions, "pyhanko_xref_chain"
    except Exception as exc:
        return [], f"failed:{exc}"


# ── Rendering helpers ──────────────────────────────────────────────────────

def _render_at_dpi(raw: bytes, page_index: int = 0,
                   dpi: int = config.RENDER_DPI) -> Optional[Image.Image]:
    try:
        doc  = fitz.open(stream=raw, filetype="pdf")
        if not doc or len(doc) == 0:
            return None
        if page_index >= len(doc):
            doc.close()
            return None
        pi = page_index
        page = doc[pi]
        from core.pdf_parser import render_bounded
        pix = render_bounded(page, dpi, annots=False)
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


def _extract_text_first_page(raw: bytes, page_index: int = 0) -> str:
    try:
        doc = fitz.open(stream=raw, filetype="pdf")
        if len(doc) == 0:
            return ""
        txt = doc[page_index].get_text() if page_index < len(doc) else ""
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
    Uses the parsed /Prev xref chain. Fails explicitly when reconstruction fails.
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

    # Signed revision = earliest revision containing a /Sig entry
    signed_rev = next((r for r in revisions if r.is_signed), None)
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
        signed_text  = _extract_text_first_page(signed_bytes, page_index)
        current_text = _extract_text_first_page(raw, page_index)
        if signed_text != current_text:
            from core.document_diff import ordered_text_diff
            changes=ordered_text_diff(signed_text,current_text)
            removed=sum(len(change['removed']) for change in changes)
            added=sum(len(change['added']) for change in changes)
            text_diff_summary=f"{removed} line(s) removed, {added} line(s) added; ordered text comparison preserves repetition."

        if text_diff_summary:
            shadow_suspect = True

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
        page_index=page_index,
        affected_pages=[page_index] if shadow_suspect else [],
        pages_compared=1 if signed_image else 0,
    )


def revision_timeline(raw):
    """Compare every consecutive parsed revision, including added/removed pages.

    A bounded page-comparison budget is reported explicitly. No render is retained
    beyond its current comparison; text changes are ordered, never converted to sets.
    """
    from core.document_diff import ordered_text_diff
    revisions,method=_discover_revisions_pymupdf(raw)
    if not revisions:return {'transitions':[], 'complete':False, 'error':method}
    transitions=[];comparisons=0;complete=True
    for before,after in zip(revisions,revisions[1:]):
        with fitz.open(stream=raw[:before.end_offset],filetype='pdf') as a, fitz.open(stream=raw[:after.end_offset],filetype='pdf') as b:
            transition={'from_revision':before.index,'to_revision':after.index,
                'new_signature':after.is_signed,'page_count_before':len(a),'page_count_after':len(b),
                'pages':[], 'metadata_changed':a.metadata!=b.metadata}
            for page in range(max(len(a),len(b))):
                if comparisons>=config.MAX_TIMELINE_PAGE_COMPARISONS:
                    complete=False;break
                comparisons+=1
                if page>=len(a):transition['pages'].append({'page':page,'change':'added'});continue
                if page>=len(b):transition['pages'].append({'page':page,'change':'removed'});continue
                changes=ordered_text_diff(a[page].get_text(),b[page].get_text())
                image_a=_render_at_dpi(raw[:before.end_offset],page,config.THUMBNAIL_DPI)
                image_b=_render_at_dpi(raw[:after.end_offset],page,config.THUMBNAIL_DPI)
                pct=None
                if image_a and image_b:_,_,pct,_=_pixel_diff(image_a,image_b)
                else:complete=False
                transition['pages'].append({'page':page,'change':'modified' if changes or (pct or 0)>0 or a[page].rect!=b[page].rect else 'unchanged',
                    'text_changes':changes,'changed_area_pct':pct,'dimensions_changed':a[page].rect!=b[page].rect})
            transitions.append(transition)
            if not complete and comparisons>=config.MAX_TIMELINE_PAGE_COMPARISONS:break
    return {'transitions':transitions,'complete':complete,'pages_compared':comparisons,
        'revision_count':len(revisions),'discovery_method':method,
        'note':'Consecutive history comparison. A change later restored is still recorded. Added/removed pages are explicit; rendering differences do not prove malicious intent.'}
