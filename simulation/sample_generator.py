"""
Synthetic PDF document generator.
All documents are visually rich and clearly distinct so comparisons are obvious.
"""

from __future__ import annotations
import io, random, time
from typing import List, Tuple, Optional
from PIL import Image, ImageDraw
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

W, H = A4   # 595 × 842 pt


# ── Colour helpers ─────────────────────────────────────────────────────────

def _hex(r, g, b):
    return colors.Color(r/255, g/255, b/255)


def _header_band(c: canvas.Canvas, title: str,
                 bg: Tuple, fg: Tuple = (255,255,255)) -> None:
    """Draw a coloured header band across the top of the page."""
    c.setFillColor(_hex(*bg))
    c.rect(0, H - 3*cm, W, 3*cm, fill=1, stroke=0)
    c.setFillColor(_hex(*fg))
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(W/2, H - 2*cm, title)


def _status_badge(c: canvas.Canvas, text: str,
                  bg: Tuple, y: float) -> None:
    """Draw a coloured status badge."""
    tw = len(text) * 7 + 20
    x  = W/2 - tw/2
    c.setFillColor(_hex(*bg))
    c.roundRect(x, y, tw, 22, 5, fill=1, stroke=0)
    c.setFillColor(_hex(255,255,255))
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(W/2, y + 6, text)


def _sig_image(width: int = 240, height: int = 60,
               seed: int = 42) -> Image.Image:
    """Draw a synthetic handwriting-like signature."""
    rng  = random.Random(seed)
    img  = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    n    = rng.randint(7, 12)
    pts  = [(int(width * i / (n-1)),
             height//2 + rng.randint(-height//3, height//3))
            for i in range(n)]
    for i in range(len(pts)-1):
        x1,y1 = pts[i]; x2,y2 = pts[i+1]
        draw.line([(x1,y1),(x2,y2)], fill=(20,20,80), width=rng.randint(2,4))
        for _ in range(rng.randint(0,3)):
            cx = (x1+x2)//2 + rng.randint(-15,15)
            cy = (y1+y2)//2 + rng.randint(-10,10)
            r  = rng.randint(3,9)
            draw.arc([(cx-r,cy-r),(cx+r,cy+r)], 0, 270,
                     fill=(20,20,80), width=2)
    return img


def _embed_pil(c: canvas.Canvas, img: Image.Image,
               x, y, w, h) -> None:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    c.drawImage(ImageReader(buf), x, y, width=w, height=h, mask="auto")


# ── Main builders ──────────────────────────────────────────────────────────

def build_signed_looking_pdf(
    title: str = "SIGNED DOCUMENT",
    body_lines: Optional[List[str]] = None,
    status: str = "VERIFIED",
    status_color: Tuple = (21, 128, 61),
    footer: str = ""
) -> bytes:
    """Rich, clearly labelled document that looks officially signed."""
    if body_lines is None:
        body_lines = ["Document content here."]

    buf = io.BytesIO()
    c   = canvas.Canvas(buf, pagesize=A4)

    # Header band — navy blue
    _header_band(c, title, bg=(30, 41, 59))

    # Thin accent line
    c.setStrokeColor(_hex(37, 99, 235))
    c.setLineWidth(3)
    c.line(1.5*cm, H - 3.2*cm, W - 1.5*cm, H - 3.2*cm)
    c.setLineWidth(1)

    # Body content
    c.setFillColor(_hex(15, 23, 42))
    c.setFont("Helvetica", 11)
    y = H - 4.2*cm
    for line in body_lines:
        if line.startswith("==="):
            c.setFont("Helvetica-Bold", 11)
            c.setFillColor(_hex(30, 41, 59))
        else:
            c.setFont("Helvetica", 11)
            c.setFillColor(_hex(15, 23, 42))
        c.drawString(2*cm, y, line)
        y -= 0.65*cm

    # Divider
    y -= 0.3*cm
    c.setStrokeColor(_hex(226, 232, 240))
    c.line(2*cm, y, W-2*cm, y)
    y -= 0.5*cm

    # Signature box
    c.setStrokeColor(_hex(203, 213, 225))
    c.setFillColor(_hex(248, 250, 252))
    c.roundRect(2*cm, y - 2.5*cm, 8*cm, 2.5*cm, 5, fill=1, stroke=1)
    c.setFillColor(_hex(100, 116, 139))
    c.setFont("Helvetica", 8)
    c.drawString(2.3*cm, y - 0.4*cm, "Authorised Signature:")
    # Synthetic handwriting
    sig = _sig_image(220, 55, seed=42)
    _embed_pil(c, sig, 2.3*cm, y - 2.2*cm, 6*cm, 1.5*cm)

    # Status badge
    _status_badge(c, f"  {status}  ", status_color, y - 3.2*cm)

    # SHA-256 hash area
    import hashlib
    fake_hash = hashlib.sha256(title.encode() + str(body_lines).encode()).hexdigest()
    c.setFont("Courier", 7.5)
    c.setFillColor(_hex(148, 163, 184))
    c.drawString(2*cm, 2.5*cm, f"SHA-256: {fake_hash}")

    # Footer
    c.setFont("Helvetica", 8)
    c.setFillColor(_hex(100, 116, 139))
    c.drawCentredString(W/2, 1.5*cm, footer or f"Generated: {time.strftime('%Y-%m-%d %H:%M UTC')}")
    c.drawCentredString(W/2, 1.0*cm, "SignGuard Synthetic Document — For Testing Purposes Only")

    c.save()
    return buf.getvalue()


def build_unsigned(text: str = "Unsigned document.", pages: int = 1) -> bytes:
    buf = io.BytesIO()
    c   = canvas.Canvas(buf, pagesize=A4)
    for p in range(pages):
        _header_band(c, "DOCUMENT", bg=(71, 85, 105))
        c.setFillColor(_hex(15, 23, 42))
        c.setFont("Helvetica", 11)
        for i, line in enumerate(text.split("\n")):
            c.drawString(2*cm, H - 4.5*cm - i*0.65*cm, line)
        _status_badge(c, "  UNSIGNED — NO SIGNATURE  ", (71, 85, 105), 4*cm)
        c.setFont("Helvetica", 8)
        c.setFillColor(_hex(148, 163, 184))
        c.drawCentredString(W/2, 1.5*cm,
            "SignGuard Synthetic Document — For Testing Purposes Only")
        if p < pages - 1:
            c.showPage()
    c.save()
    return buf.getvalue()


def build_visual_only(sig_seed: int = 1) -> bytes:
    """Document with an embedded handwriting image but NO crypto signature."""
    buf = io.BytesIO()
    c   = canvas.Canvas(buf, pagesize=A4)
    _header_band(c, "CONTRACT AGREEMENT", bg=(30, 41, 59))
    c.setFont("Helvetica", 11)
    c.setFillColor(_hex(15, 23, 42))
    lines = [
        "Agreement Reference: AGR-2024-055",
        "This agreement is entered into by the undersigned parties.",
        "Terms and conditions apply as stated in Schedule A.",
        "All parties agree to the terms on the date of signing.",
        "",
        "Signed by (handwritten):",
    ]
    y = H - 4.5*cm
    for line in lines:
        c.drawString(2*cm, y, line)
        y -= 0.65*cm

    sig = _sig_image(240, 60, seed=sig_seed)
    _embed_pil(c, sig, 2.5*cm, y - 1.6*cm, 6.5*cm, 1.6*cm)

    _status_badge(c, "  VISUAL SIGNATURE ONLY — NO CRYPTO SIG  ",
                  (180, 83, 9), H - 3.5*cm - 10)

    c.setFont("Helvetica", 8)
    c.setFillColor(_hex(148, 163, 184))
    c.drawCentredString(W/2, 1.5*cm,
        "SignGuard Synthetic Document — Visual Candidate Test")
    c.save()
    return buf.getvalue()


def build_shadow_pdf(
    title: str = "INVOICE",
    original_amount: str = "$1,000",
    shadow_amount: str = "$9,000",
    note: str = ""
) -> bytes:
    # Compatibility API: a genuinely signed document plus a valid incremental update.
    from simulation.security_fixtures import shadow_pair
    return shadow_pair(original_amount, shadow_amount)[1]


def build_tampered_bytes(original_pdf: bytes,
                         change_offset: int = 500) -> bytes:
    """Flip one byte in the body — simulates raw tampering."""
    data   = bytearray(original_pdf)
    offset = max(change_offset, 100)
    offset = min(offset, len(data) - 10)
    data[offset] = (data[offset] + 1) % 256
    return bytes(data)


def build_duplicate_sig_pdf(sig_count: int = 2,
                             sig_seed: int = 99) -> bytes:
    """Document with two near-identical signature images for ORB/RANSAC demo."""
    buf = io.BytesIO()
    c   = canvas.Canvas(buf, pagesize=A4)
    _header_band(c, "DUAL WITNESS SIGNATURE FORM", bg=(30, 41, 59))

    c.setFont("Helvetica", 11)
    c.setFillColor(_hex(15, 23, 42))
    c.drawString(2*cm, H - 4.2*cm, "This document requires two independent witness signatures.")
    c.drawString(2*cm, H - 4.9*cm, "Both witnesses must sign in the designated areas below.")

    # Two signature boxes side by side
    for i in range(sig_count):
        bx = 1.5*cm + i * 9*cm
        by = H - 11*cm
        # Box
        c.setStrokeColor(_hex(203, 213, 225))
        c.setFillColor(_hex(248, 250, 252))
        c.roundRect(bx, by, 7.5*cm, 5*cm, 5, fill=1, stroke=1)
        # Label
        c.setFillColor(_hex(100, 116, 139))
        c.setFont("Helvetica-Bold", 9)
        c.drawString(bx + 0.3*cm, by + 4.5*cm, f"Witness {i+1}:")
        # Signature — same seed = nearly identical
        sig = _sig_image(210, 55, seed=sig_seed)
        _embed_pil(c, sig, bx + 0.3*cm, by + 2.5*cm, 5.8*cm, 1.5*cm)
        # Name line
        c.setStrokeColor(_hex(100, 116, 139))
        c.line(bx + 0.3*cm, by + 2.1*cm, bx + 7*cm, by + 2.1*cm)
        c.setFont("Helvetica", 8)
        c.setFillColor(_hex(148, 163, 184))
        c.drawString(bx + 0.3*cm, by + 1.7*cm, "Print name:")
        c.drawString(bx + 0.3*cm, by + 1.1*cm, "Date:")
        # Similarity warning badge
        c.setFillColor(_hex(180, 83, 9) if i == 1 else _hex(21, 128, 61))
        c.setFont("Helvetica-Bold", 7)
        c.drawString(bx + 0.3*cm, by + 0.4*cm,
                     "DUPLICATE DETECTED" if i == 1 else "REFERENCE SIGNATURE")

    _status_badge(c, "  VISUAL DUPLICATION TEST — ORB/RANSAC TARGET  ",
                  (180, 83, 9), H - 13.5*cm)

    c.setFont("Helvetica", 8)
    c.setFillColor(_hex(148, 163, 184))
    c.drawCentredString(W/2, 1.5*cm,
        "SignGuard Synthetic Document — ORB Duplication Test")
    c.save()
    return buf.getvalue()


def build_ela_target() -> bytes:
    """Document with a colourful gradient region for ELA demonstration."""
    buf = io.BytesIO()
    c   = canvas.Canvas(buf, pagesize=A4)
    _header_band(c, "ELA ANALYSIS TARGET", bg=(88, 28, 135))

    c.setFont("Helvetica", 10)
    c.setFillColor(_hex(15, 23, 42))
    c.drawString(2*cm, H - 4.2*cm,
        "This document contains a gradient image region for ELA demonstration.")
    c.drawString(2*cm, H - 4.9*cm,
        "ELA residuals will be measured after JPEG recompression.")

    # Gradient bars
    for i in range(60):
        shade = i / 60
        c.setFillColor(colors.Color(shade, 0.4*(1-shade), 1-shade))
        c.rect(2*cm + i*0.18*cm, H - 10*cm, 0.2*cm, 4.5*cm, fill=1, stroke=0)

    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(_hex(88, 28, 135))
    c.drawCentredString(W/2, H - 10.8*cm,
        "[ GRADIENT REGION — ELA TARGET ABOVE ]")

    _status_badge(c, "  ELA MANIPULATION TARGET  ", (88, 28, 135), H - 12*cm)

    c.setFont("Helvetica", 8)
    c.setFillColor(_hex(148, 163, 184))
    c.drawCentredString(W/2, 1.5*cm,
        "SignGuard Synthetic Document — ELA Test")
    c.save()
    return buf.getvalue()


def build_multi_page_visual(pages: int = 3, sig_seed: int = 7) -> bytes:
    buf = io.BytesIO()
    c   = canvas.Canvas(buf, pagesize=A4)
    for p in range(pages):
        _header_band(c, f"MULTI-PAGE AGREEMENT — Page {p+1} of {pages}",
                     bg=(30, 41, 59))
        c.setFont("Helvetica", 10)
        c.setFillColor(_hex(15, 23, 42))
        for i in range(12):
            c.drawString(2*cm, H - 4.5*cm - i*0.55*cm,
                f"Section {p+1}.{i+1}: Lorem ipsum dolor sit amet, "
                "consectetur adipiscing elit.")
        if p == pages - 1:
            sig = _sig_image(200, 50, seed=sig_seed)
            _embed_pil(c, sig, 3*cm, 4*cm, 5.5*cm, 1.4*cm)
            c.setFont("Helvetica", 8)
            c.setFillColor(_hex(100, 116, 139))
            c.drawString(3*cm, 3.4*cm, "Authorised Signature (last page)")
        if p < pages - 1:
            c.showPage()
    c.save()
    return buf.getvalue()
