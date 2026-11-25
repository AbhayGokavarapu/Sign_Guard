"""
Module 5 — Automatic visual signature localisation.

Pipeline:
  render page → greyscale → text mask → adaptive threshold →
  morphology → connected components → candidate bounding boxes → crops
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

try:
    import pymupdf as fitz
except ImportError:
    import fitz
import numpy as np
import cv2
from PIL import Image, ImageDraw

import config


@dataclass
class SignatureCandidate:
    page:       int
    bbox:       Tuple[int,int,int,int]  # x, y, w, h  (pixels at RENDER_DPI)
    crop:       Image.Image
    confidence: float   # heuristic 0-1


@dataclass
class LocalizationResult:
    page_index:     int
    original:       Image.Image
    gray:           Image.Image
    text_masked:    Image.Image
    thresholded:    Image.Image
    components_vis: Image.Image
    annotated:      Image.Image           # blue boxes on original
    candidates:     List[SignatureCandidate]
    error:          Optional[str] = None


# ── Helpers ────────────────────────────────────────────────────────────────

def _pil_to_cv(img: Image.Image) -> np.ndarray:
    return cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR)


def _cv_to_pil(arr: np.ndarray) -> Image.Image:
    return Image.fromarray(cv2.cvtColor(arr, cv2.COLOR_BGR2RGB))


def _build_text_mask(raw: bytes, page_index: int, shape: Tuple[int,int]) -> np.ndarray:
    """
    White mask where PDF text characters live; used to suppress text blobs.
    Shape = (H, W).
    """
    H, W = shape
    mask = np.zeros((H, W), dtype=np.uint8)
    try:
        doc  = fitz.open(stream=raw, filetype="pdf")
        page = doc[page_index]
        scale_x = W / page.rect.width
        scale_y = H / page.rect.height
        words = page.get_text("words")  # list of (x0,y0,x1,y1,word,...)
        for w in words:
            x0 = int(w[0] * scale_x)
            y0 = int(w[1] * scale_y)
            x1 = int(w[2] * scale_x)
            y1 = int(w[3] * scale_y)
            # Inflate slightly
            pad = 4
            cv2.rectangle(mask,
                          (max(0, x0-pad), max(0, y0-pad)),
                          (min(W, x1+pad), min(H, y1+pad)),
                          255, -1)
        doc.close()
    except Exception:
        pass
    return mask


# ── Public API ─────────────────────────────────────────────────────────────

def localize(raw: bytes, page_index: int = 0) -> LocalizationResult:
    # 1. Render
    try:
        doc  = fitz.open(stream=raw, filetype="pdf")
        page = doc[page_index]
        mat  = fitz.Matrix(config.RENDER_DPI / 72, config.RENDER_DPI / 72)
        pix  = page.get_pixmap(matrix=mat, alpha=False)
        original = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        doc.close()
    except Exception as exc:
        return LocalizationResult(
            page_index, Image.new("RGB",(100,100),"white"),
            Image.new("L",(100,100),"white"),
            Image.new("RGB",(100,100),"white"),
            Image.new("L",(100,100),"white"),
            Image.new("RGB",(100,100),"white"),
            Image.new("RGB",(100,100),"white"),
            [],
            error=str(exc)
        )

    H, W = original.height, original.width

    # 2. Greyscale
    gray_arr  = cv2.cvtColor(_pil_to_cv(original), cv2.COLOR_BGR2GRAY)
    gray_img  = Image.fromarray(gray_arr)

    # 3. Text mask
    text_mask = _build_text_mask(raw, page_index, (H, W))
    masked_arr = gray_arr.copy()
    masked_arr[text_mask > 0] = 255          # white out text regions
    text_masked_img = Image.fromarray(masked_arr)

    # 4. Adaptive threshold (invert: dark ink → white blobs)
    blurred = cv2.GaussianBlur(masked_arr, (5, 5), 0)
    _, binary = cv2.threshold(blurred, 0, 255,
                              cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    thresh_img = Image.fromarray(binary)

    # 5. Morphology: close gaps within a stroke
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 3))
    closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)
    # Dilate horizontally to link nearby strokes
    hkernel = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 1))
    dilated = cv2.dilate(closed, hkernel, iterations=1)

    # 6. Connected components
    n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
        dilated, connectivity=8
    )

    # Colour components for visualisation
    comp_vis = cv2.cvtColor(dilated, cv2.COLOR_GRAY2BGR)
    rng = np.random.default_rng(42)
    for lab in range(1, n_labels):
        colour = rng.integers(50, 220, size=3).tolist()
        comp_vis[labels == lab] = colour
    comp_img = _cv_to_pil(comp_vis)

    # 7. Filter candidates
    candidates: List[SignatureCandidate] = []
    annotated   = original.copy()
    draw        = ImageDraw.Draw(annotated)

    MIN_W, MAX_W = 60,  int(W * 0.7)
    MIN_H, MAX_H = 12,  int(H * 0.25)
    MIN_ASPECT   = 1.5   # wider than tall
    MAX_ASPECT   = 20.0

    for lab in range(1, n_labels):
        x  = stats[lab, cv2.CC_STAT_LEFT]
        y  = stats[lab, cv2.CC_STAT_TOP]
        bw = stats[lab, cv2.CC_STAT_WIDTH]
        bh = stats[lab, cv2.CC_STAT_HEIGHT]
        area = stats[lab, cv2.CC_STAT_AREA]

        if not (MIN_W <= bw <= MAX_W and MIN_H <= bh <= MAX_H):
            continue
        aspect = bw / max(bh, 1)
        if not (MIN_ASPECT <= aspect <= MAX_ASPECT):
            continue
        density = area / (bw * bh)
        if density < 0.03 or density > 0.80:
            continue

        confidence = min(1.0, density * aspect / 5.0)
        crop = original.crop((x, y, x+bw, y+bh))
        candidates.append(SignatureCandidate(page_index, (x,y,bw,bh), crop, confidence))
        draw.rectangle([x, y, x+bw, y+bh], outline=(37,99,235), width=3)

    return LocalizationResult(
        page_index=page_index,
        original=original,
        gray=gray_img,
        text_masked=text_masked_img,
        thresholded=thresh_img,
        components_vis=comp_img,
        annotated=annotated,
        candidates=candidates,
    )
