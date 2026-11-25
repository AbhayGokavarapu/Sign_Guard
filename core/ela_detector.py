"""
Module 6 — Error Level Analysis (ELA).

Implements both single-quality interactive ELA and automatic
multi-quality ELA sweep across documented quality settings.

IMPORTANT LIMITATIONS:
- ELA was designed for JPEG photographs. Rendered PDF page crops may not
  preserve original JPEG compression history, so ELA residuals reflect
  recompression artefacts, NOT necessarily manipulation.
- High residuals can be caused by high-contrast edges, fine textures,
  gradients, or printed text — not only by pasted/altered regions.
- ELA is a supporting forensic indicator only. It never establishes
  definitive manipulation or forgery on its own.
- Changing amplification changes visualization brightness only.
  It does NOT change the underlying residual measurements or verdict logic.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from typing import List, Optional, Dict

import numpy as np
from PIL import Image

import config


@dataclass
class SingleELA:
    """ELA result at one quality setting."""
    quality:        int
    amplification:  int
    recompressed:   Image.Image
    raw_diff:       Image.Image
    amplified:      Image.Image
    mean_residual:  float
    max_residual:   float
    std_residual:   float
    high_pct:       float          # % pixels above HIGH_RESIDUAL_THRESHOLD
    histogram:      List[int]      # 256-bin histogram of gray residuals


@dataclass
class ELAResult:
    """Full ELA result — includes multi-quality sweep + selected view."""
    original:         Image.Image

    # Active (user-selected) quality result
    recompressed:     Image.Image
    raw_diff:         Image.Image
    amplified:        Image.Image
    mean_residual:    float
    max_residual:     float
    std_residual:     float
    high_pct:         float
    quality_used:     int
    amp_used:         int
    finding:          str
    histogram:        List[int]

    # Multi-quality sweep
    multi_quality:    Dict[int, SingleELA] = field(default_factory=dict)
    sweep_summary:    str = ""

    error:            Optional[str] = None


HIGH_RESIDUAL_THRESHOLD = 50   # raw, unamplified grayscale residual


def _ela_single(original_arr: np.ndarray,
                quality: int,
                amplification: int) -> SingleELA:
    """
    Run ELA at one quality setting.
    original_arr: float32 RGB array.
    amplification: visualization-only scaling, does not affect measurements.
    """
    original_img = Image.fromarray(original_arr.clip(0, 255).astype(np.uint8))

    buf = io.BytesIO()
    original_img.save(buf, format="JPEG", quality=quality)
    buf.seek(0)
    recompressed = Image.open(buf).convert("RGB")
    recomp_arr   = np.array(recompressed, dtype=np.float32)

    # Absolute pixel difference (measurement — independent of amplification)
    diff_arr     = np.abs(original_arr - recomp_arr)
    raw_diff_img = Image.fromarray(diff_arr.clip(0, 255).astype(np.uint8))

    # Amplified visualization — does not affect statistics
    amp_arr  = (diff_arr * amplification).clip(0, 255).astype(np.uint8)
    amp_img  = Image.fromarray(amp_arr)

    # Statistics on the RAW (un-amplified) gray residual
    gray = diff_arr.mean(axis=2)
    mean_res = float(gray.mean())
    max_res  = float(gray.max())
    std_res  = float(gray.std())

    high_pct = float((gray > HIGH_RESIDUAL_THRESHOLD).sum()) / max(gray.size, 1) * 100

    histo = np.histogram(gray.flatten(), bins=256, range=(0, 256))[0].tolist()

    return SingleELA(
        quality=quality, amplification=amplification,
        recompressed=recompressed,
        raw_diff=raw_diff_img,
        amplified=amp_img,
        mean_residual=mean_res,
        max_residual=max_res,
        std_residual=std_res,
        high_pct=high_pct,
        histogram=histo,
    )


def run_ela(image: Image.Image,
            quality:       int = config.ELA_DEFAULT_QUALITY,
            amplification: int = config.ELA_DEFAULT_AMP) -> ELAResult:
    """
    Run ELA at the selected quality AND sweep all configured qualities.
    amplification affects visualization only — not measurements or verdict.
    """
    try:
        original = image.convert("RGB")
        orig_arr = np.array(original, dtype=np.float32)

        # ── Active quality ──────────────────────────────────────────────
        active = _ela_single(orig_arr, quality, amplification)

        # ── Multi-quality sweep ─────────────────────────────────────────
        multi: Dict[int, SingleELA] = {}
        for q in config.ELA_QUALITIES:
            multi[q] = _ela_single(orig_arr, q, amplification)

        # Sweep summary: highest mean across all qualities
        max_mean_q   = max(multi, key=lambda q: multi[q].mean_residual)
        max_mean_val = multi[max_mean_q].mean_residual

        sweep_parts = [
            f"Q{q}: mean={multi[q].mean_residual:.1f}" for q in config.ELA_QUALITIES
        ]
        sweep_summary = (
            "Multi-quality sweep — " + " | ".join(sweep_parts) +
            f" — highest at Q{max_mean_q} ({max_mean_val:.1f})."
        )

        finding = _interpret(active.mean_residual, active.high_pct)

        return ELAResult(
            original=original,
            recompressed=active.recompressed,
            raw_diff=active.raw_diff,
            amplified=active.amplified,
            mean_residual=active.mean_residual,
            max_residual=active.max_residual,
            std_residual=active.std_residual,
            high_pct=active.high_pct,
            quality_used=quality,
            amp_used=amplification,
            finding=finding,
            histogram=active.histogram,
            multi_quality=multi,
            sweep_summary=sweep_summary,
        )

    except Exception as exc:
        blank = Image.new("RGB", (200, 60), "white")
        return ELAResult(
            blank, blank, blank, blank,
            0.0, 0.0, 0.0, 0.0,
            quality, amplification,
            "ELA failed.", [], {}, "",
            error=str(exc)
        )


def _interpret(mean: float, high_pct: float) -> str:
    if mean > config.ELA_HIGH_THRESHOLD:
        return (
            f"Mean residual ({mean:.1f}) is elevated relative to the threshold "
            f"({config.ELA_HIGH_THRESHOLD:.0f}). "
            "This may indicate prior JPEG compression history differences or "
            "image manipulation. "
            "However, high-contrast edges, fine textures and printed text also "
            "produce elevated residuals. ELA is a supporting indicator only."
        )
    elif high_pct > 5.0:
        return (
            f"{high_pct:.1f}% of pixels show high raw residual energy. "
            "Localised high-residual regions may warrant investigation but "
            "are not standalone proof of manipulation."
        )
    else:
        return (
            f"Mean residual ({mean:.1f}) is within a typical range for JPEG "
            f"recompression at this quality setting. "
            "No strong ELA anomaly detected. Note: rendered PDF crops may not "
            "carry original JPEG compression history."
        )
