"""
Controlled attack scenario definitions.

Each scenario factory returns (original_bytes, attack_bytes, ground_truth_label).
Ground-truth labels are NEVER passed to the detection engine.

Original and modified documents may render identically. Cryptographic evidence
and visual evidence are demonstrated separately.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Tuple, Optional


@dataclass
class Scenario:
    id:           str
    name:         str
    description:  str
    category:     str
    factory:      Callable[[], Tuple[bytes, bytes, str]]
    ground_truth: str


# ── Scenario factories ─────────────────────────────────────────────────────

def _scenario_a() -> Tuple[bytes, bytes, str]:
    from simulation.security_fixtures import signed_control
    pdf = signed_control()
    return pdf, pdf, "INCONCLUSIVE"


def _scenario_b() -> Tuple[bytes, bytes, str]:
    from simulation.security_fixtures import signed_control, tamper_signed
    original = signed_control()
    return original, tamper_signed(original), "TAMPERING_DETECTED"


def _scenario_c() -> Tuple[bytes, bytes, str]:
    from simulation.security_fixtures import shadow_pair
    original, updated = shadow_pair()
    return original, updated, "REVIEW_REQUIRED"


def _scenario_d() -> Tuple[bytes, bytes, str]:
    """Visual signature duplication — two near-identical handwriting images."""
    from simulation.sample_generator import build_duplicate_sig_pdf
    pdf = build_duplicate_sig_pdf(sig_count=2, sig_seed=99)
    return pdf, pdf, "REVIEW_REQUIRED"


def _scenario_e() -> Tuple[bytes, bytes, str]:
    """ELA manipulation — image region has elevated JPEG residuals."""
    from simulation.sample_generator import build_ela_target
    original = build_ela_target()
    return original, original, "INCONCLUSIVE"



def _scenario_f() -> Tuple[bytes, bytes, str]:
    """Unsigned document — no signature evidence at all."""
    from simulation.sample_generator import build_unsigned
    pdf = build_unsigned(
        "SCENARIO F — UNSIGNED DOCUMENT\n\n"
        "This document contains no digital signature\n"
        "and no handwritten signature image.\n\n"
        "The absence of a signature does NOT prove\n"
        "the document is forged — it is simply unsigned."
    )
    return pdf, pdf, "INCONCLUSIVE"


ALL_SCENARIOS = [
    Scenario("A", "Scenario A — Original Signed",
             "An unchanged synthetic signed PDF. Signature mathematics should pass; the self-signed test certificate is not a trusted identity.",
             "baseline", _scenario_a, "INCONCLUSIVE"),
    Scenario("B", "Scenario B — Signed-Byte Tampering",
             "A signed PDF with one byte flipped — SHA-256 digest breaks.",
             "tampered", _scenario_b, "TAMPERING_DETECTED"),
    Scenario("C", "Scenario C — Post-signing Content Replacement",
             "Signed PDF with valid incremental revision: signed at $1,000 but current shows $9,000.",
             "shadow", _scenario_c, "REVIEW_REQUIRED"),
    Scenario("D", "Scenario D — Visual Signature Duplication",
             "Two near-identical handwriting images — ORB/RANSAC detects the copy.",
             "visual", _scenario_d, "REVIEW_REQUIRED"),
    Scenario("E", "Scenario E — ELA Residual Demonstration",
             "Recompression residual demonstration; does not prove manipulation.",
             "ela", _scenario_e, "INCONCLUSIVE"),
    Scenario("F", "Scenario F — Unsigned Document",
             "A plain document with no signature. Absence of sig ≠ forgery.",
             "unsigned", _scenario_f, "INCONCLUSIVE"),
]


def get_scenario(scenario_id: str) -> Optional[Scenario]:
    for s in ALL_SCENARIOS:
        if s.id == scenario_id:
            return s
    return None
