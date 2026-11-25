"""
Fixture manager — generates and caches synthetic dataset files on disk.

Keeps dataset generation strictly separate from detector logic.
Ground-truth labels are stored in a companion JSON only.
"""

from __future__ import annotations

import json
import os
import time
from typing import Dict, List, Tuple

import config
from simulation.sample_generator import (
    build_unsigned, build_visual_only, build_multi_page_visual,
    build_shadow_pdf, build_duplicate_sig_pdf, build_ela_target,
    build_tampered_bytes,
)
from simulation.signed_samples import build_signed_pdf

MANIFEST_PATH = os.path.join(config.DATASETS_DIR, "manifest.json")


def _write(path: str, data: bytes) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)


def generate_dataset(force: bool = False) -> Dict:
    """
    Generate at least 25 synthetic labeled PDF fixtures.
    Returns the manifest dict.
    """
    if os.path.exists(MANIFEST_PATH) and not force:
        with open(MANIFEST_PATH) as f:
            return json.load(f)

    manifest: List[dict] = []

    def add(category: str, filename: str, data: bytes, label: str, notes: str = ""):
        path = os.path.join(config.DATASETS_DIR, category, filename)
        _write(path, data)
        manifest.append({
            "file":     os.path.relpath(path, config.BASE_DIR),
            "category": category,
            "label":    label,
            "notes":    notes,
            "size":     len(data),
        })

    # ── Genuine signed (5) ────────────────────────────────────────────────
    for i in range(5):
        pdf = build_signed_pdf(f"Genuine signed document #{i+1}. "
                               f"Reference: GEN-{1000+i}.")
        add("genuine", f"genuine_{i+1:02d}.pdf", pdf, "CLEAN",
            f"Synthetic signed document, seed={i}")

    # ── Tampered (5) ──────────────────────────────────────────────────────
    for i in range(5):
        orig = build_signed_pdf(f"Tampered document #{i+1}.")
        tampered = build_tampered_bytes(orig, change_offset=400 + i * 50)
        add("tampered", f"tampered_{i+1:02d}.pdf", tampered, "TAMPERING_DETECTED",
            f"Byte flip at offset {400+i*50}")

    # ── Shadow (5) ────────────────────────────────────────────────────────
    amounts = [("$1,000", "$9,000"), ("$100", "$900"),
               ("Approved", "Rejected"), ("2024-01-01", "2025-12-31"),
               ("Section 3 applies", "Section 7 applies")]
    for i, (orig_text, shadow_text) in enumerate(amounts):
        pdf = build_shadow_pdf(original_amount=orig_text, shadow_amount=shadow_text)
        add("shadow", f"shadow_{i+1:02d}.pdf", pdf, "REVIEW_REQUIRED",
            f"shadow: '{orig_text}' → '{shadow_text}'")

    # ── Visual-only (5) ───────────────────────────────────────────────────
    for i in range(3):
        pdf = build_visual_only(sig_seed=i + 10)
        add("visual_only", f"visual_{i+1:02d}.pdf", pdf, "INCONCLUSIVE",
            "Visual signature candidate, no crypto sig")
    for i in range(2):
        pdf = build_multi_page_visual(pages=2 + i, sig_seed=i + 20)
        add("visual_only", f"visual_multi_{i+1:02d}.pdf", pdf, "INCONCLUSIVE",
            f"Multi-page ({2+i} pages)")

    # ── Unsigned (5) ──────────────────────────────────────────────────────
    for i in range(5):
        pdf = build_unsigned(f"Unsigned document #{i+1}. No signature present.")
        add("unsigned", f"unsigned_{i+1:02d}.pdf", pdf, "INCONCLUSIVE",
            "Plain unsigned PDF")

    # ── Edge cases (5) ────────────────────────────────────────────────────
    # Duplicate signature
    add("visual_only", "duplicate_sig_01.pdf",
        build_duplicate_sig_pdf(2, 99), "REVIEW_REQUIRED",
        "Two near-identical signature images")
    # ELA target
    add("visual_only", "ela_target_01.pdf",
        build_ela_target(), "REVIEW_REQUIRED",
        "ELA manipulation target")
    # Rotated / faint mark — unsigned with tiny graphic
    add("unsigned", "faint_mark_01.pdf",
        build_unsigned("Document with minimal graphical content."),
        "INCONCLUSIVE", "Faint graphical marks")
    # Multi-revision without sig
    add("unsigned", "multi_rev_01.pdf",
        build_shadow_pdf(original_amount="$1,000", shadow_amount="$1,000"),
        "INCONCLUSIVE", "Two revisions but no crypto sig")
    # Very small file
    add("unsigned", "minimal_01.pdf",
        build_unsigned(""), "INCONCLUSIVE", "Minimal content")

    result = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total":        len(manifest),
        "files":        manifest,
    }
    with open(MANIFEST_PATH, "w") as f:
        json.dump(result, f, indent=2)

    return result


def load_manifest() -> Dict:
    if not os.path.exists(MANIFEST_PATH):
        return generate_dataset()
    with open(MANIFEST_PATH) as f:
        return json.load(f)
