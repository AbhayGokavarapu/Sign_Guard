"""
Module 1 — PDF upload and parsing.

Validates, opens, and extracts metadata/pages/images/signatures from a PDF.
Returns a ParsedDocument dataclass consumed by all downstream modules.
"""

from __future__ import annotations

import hashlib
import io
import os
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

try:
    import pymupdf as fitz  # PyMuPDF >= 1.24
except ImportError:
    import fitz  # PyMuPDF < 1.24
from PIL import Image

import config


# ── Data structures ────────────────────────────────────────────────────────

@dataclass
class ParsedDocument:
    file_name:    str
    file_size:    int
    sha256:       str
    raw_bytes:    bytes
    page_count:   int
    metadata:     Dict[str, Any]
    is_encrypted: bool
    has_sig_fields: bool
    sig_field_count: int
    sig_field_names: List[str]
    page_images:  List[Image.Image] = field(default_factory=list)   # rendered pages
    text_blocks:  List[List[Dict]]  = field(default_factory=list)   # per-page
    image_xrefs:  List[List[int]]   = field(default_factory=list)   # per-page xref ids
    error:        Optional[str]     = None


@dataclass
class ValidationResult:
    valid:   bool
    reason:  str


def render_bounded(page, dpi, annots=True):
    """Reject excessive dimensions before allocating a pixmap."""
    scale = dpi / 72
    width, height = page.rect.width * scale, page.rect.height * scale
    if width <= 0 or height <= 0 or width > config.MAX_PAGE_WIDTH_PX or height > config.MAX_PAGE_HEIGHT_PX:
        raise ValueError("Page exceeds safe rendering dimensions.")
    return page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False, annots=annots)


# ── Public API ─────────────────────────────────────────────────────────────

def validate_pdf(raw: bytes, filename: str) -> ValidationResult:
    """Light validation before full parsing."""
    size_mb = len(raw) / (1024 * 1024)
    if size_mb > config.MAX_FILE_SIZE_MB:
        return ValidationResult(False,
            f"File exceeds {config.MAX_FILE_SIZE_MB} MB limit ({size_mb:.1f} MB).")
    if not raw.startswith(b"%PDF"):
        return ValidationResult(False, "File does not start with a PDF header (%PDF).")
    return ValidationResult(True, "OK")


def parse_pdf(raw: bytes, filename: str = "document.pdf") -> ParsedDocument:
    """
    Full parsing pipeline.  Returns a ParsedDocument; sets .error on failure.
    """
    sha256 = hashlib.sha256(raw).hexdigest()

    try:
        doc = fitz.open(stream=raw, filetype="pdf")
    except Exception as exc:
        return ParsedDocument(
            file_name=filename, file_size=len(raw), sha256=sha256,
            raw_bytes=raw, page_count=0, metadata={},
            is_encrypted=False, has_sig_fields=False,
            sig_field_count=0, sig_field_names=[],
            error=f"Could not open PDF: {exc}"
        )

    if doc.is_encrypted:
        # Try empty password
        if doc.authenticate("") == 0:
            doc.close()
            return ParsedDocument(
                file_name=filename, file_size=len(raw), sha256=sha256,
                raw_bytes=raw, page_count=0, metadata={},
                is_encrypted=True, has_sig_fields=False,
                sig_field_count=0, sig_field_names=[],
                error="PDF is password-encrypted and could not be opened."
            )

    page_count = len(doc)
    if page_count > config.MAX_PAGE_COUNT:
        doc.close()
        return ParsedDocument(
            file_name=filename, file_size=len(raw), sha256=sha256,
            raw_bytes=raw, page_count=page_count, metadata={},
            is_encrypted=False, has_sig_fields=False,
            sig_field_count=0, sig_field_names=[],
            error=f"Document has {page_count} pages; limit is {config.MAX_PAGE_COUNT}."
        )

    if page_count == 0:
        doc.close()
        return ParsedDocument(filename, len(raw), sha256, raw, 0, {}, False, False, 0, [], error="PDF has no pages.")
    total_pixels = 0
    for page in doc:
        w, h = page.rect.width * config.RENDER_DPI / 72, page.rect.height * config.RENDER_DPI / 72
        total_pixels += w * h
        if w <= 0 or h <= 0 or w > config.MAX_PAGE_WIDTH_PX or h > config.MAX_PAGE_HEIGHT_PX or total_pixels > config.MAX_TOTAL_RENDER_PIXELS:
            doc.close()
            return ParsedDocument(filename, len(raw), sha256, raw, page_count, {}, False, False, 0, [], error="Document exceeds safe rendering budget.")

    # Metadata
    meta_raw = doc.metadata or {}
    metadata: Dict[str, Any] = {
        "title":    meta_raw.get("title", ""),
        "author":   meta_raw.get("author", ""),
        "subject":  meta_raw.get("subject", ""),
        "creator":  meta_raw.get("creator", ""),
        "producer": meta_raw.get("producer", ""),
        "creation_date": meta_raw.get("creationDate", ""),
        "mod_date":      meta_raw.get("modDate", ""),
        "format":        doc.get_pdf_str(1) if hasattr(doc, "get_pdf_str") else "",
        "pdf_version":   doc.pdf_version() if hasattr(doc, "pdf_version") else "",
    }

    # Signature fields
    sig_field_names: List[str] = []
    for page in doc:
        for widget in page.widgets() or []:
            if widget.field_type_string == "Sig":
                sig_field_names.append(widget.field_name or "unnamed")

    # Page images + text
    page_images: List[Image.Image] = []
    text_blocks: List[List[Dict]]  = []
    image_xrefs: List[List[int]]   = []

    mat = fitz.Matrix(config.THUMBNAIL_DPI / 72, config.THUMBNAIL_DPI / 72)
    for page in doc:
        pix = render_bounded(page, config.THUMBNAIL_DPI)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        page_images.append(img)

        blocks = page.get_text("dict")["blocks"]
        text_blocks.append(blocks)

        xrefs = [img_info[0] for img_info in page.get_images(full=True)]
        image_xrefs.append(xrefs)

    doc.close()

    return ParsedDocument(
        file_name=filename,
        file_size=len(raw),
        sha256=sha256,
        raw_bytes=raw,
        page_count=page_count,
        metadata=metadata,
        is_encrypted=False,
        has_sig_fields=bool(sig_field_names),
        sig_field_count=len(sig_field_names),
        sig_field_names=sig_field_names,
        page_images=page_images,
        text_blocks=text_blocks,
        image_xrefs=image_xrefs,
    )


def render_page(raw: bytes, page_index: int = 0, dpi: int = config.RENDER_DPI) -> Image.Image:
    """Render a single page at the requested DPI."""
    doc = fitz.open(stream=raw, filetype="pdf")
    page = doc[page_index]
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    doc.close()
    return img


def extract_embedded_images(raw: bytes, page_index: int = 0) -> List[Image.Image]:
    """Extract raster images embedded on a page."""
    doc  = fitz.open(stream=raw, filetype="pdf")
    page = doc[page_index]
    imgs: List[Image.Image] = []
    for img_info in page.get_images(full=True):
        xref = img_info[0]
        base = doc.extract_image(xref)
        try:
            imgs.append(Image.open(io.BytesIO(base["image"])).convert("RGB"))
        except Exception:
            pass
    doc.close()
    return imgs
