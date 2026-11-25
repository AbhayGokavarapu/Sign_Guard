"""
Controlled attack scenario definitions.

Each scenario factory returns (original_bytes, attack_bytes, ground_truth_label).
Ground-truth labels are NEVER passed to the detection engine.

Key principle: original and attack documents must be VISUALLY DISTINCT so the
comparison side-by-side is immediately obvious to anyone viewing the dashboard.
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
    """Clean signed document — original = attack (no attack applied)."""
    from simulation.sample_generator import build_signed_looking_pdf
    pdf = build_signed_looking_pdf(
        title="OFFICIAL CONTRACT",
        body_lines=[
            "Contract Reference: SGD-2024-001",
            "Parties: Alpha Corp and Beta Ltd",
            "Payment Amount: $1,000 (One Thousand Dollars)",
            "Date of Signing: 2024-01-15",
            "Clause 1: Both parties agree to the stated terms.",
            "Clause 2: Payment due within 30 days of signing.",
        ],
        status="ORIGINAL — UNMODIFIED",
        status_color=(21, 128, 61),   # green
        footer="Digitally signed. No modifications have been made."
    )
    return pdf, pdf, "CLEAN"


def _scenario_b() -> Tuple[bytes, bytes, str]:
    """Signed-byte tampering — a byte is flipped in the original."""
    from simulation.sample_generator import build_signed_looking_pdf, build_tampered_bytes
    original = build_signed_looking_pdf(
        title="PAYMENT AUTHORISATION",
        body_lines=[
            "Document ID:    PAY-2024-789",
            "Authorised by:  Chief Financial Officer",
            "Payment to:     Supplier XYZ Ltd",
            "Amount:         $5,000 (Five Thousand Dollars)",
            "Account No:     12-3456-7890",
            "Reference:      INV-2024-456",
            "Status:         APPROVED AND SIGNED",
        ],
        status="ORIGINAL — BYTES INTACT",
        status_color=(21, 128, 61),
        footer="SHA-256 digest recorded at time of signing."
    )
    # Flip a byte deep in the content — simulates raw file tampering
    tampered = build_tampered_bytes(original, change_offset=600)
    return original, tampered, "TAMPERING_DETECTED"


def _scenario_c() -> Tuple[bytes, bytes, str]:
    """Shadow attack — revision 1 shows $1,000, revision 2 overrides to $9,000."""
    from simulation.sample_generator import build_shadow_pdf
    original = build_shadow_pdf(
        title="PURCHASE ORDER",
        original_amount="$1,000",
        shadow_amount="$1,000",   # same — this is what was signed
        note="ORIGINAL SIGNED REVISION"
    )
    shadow = build_shadow_pdf(
        title="PURCHASE ORDER",
        original_amount="$1,000",
        shadow_amount="$9,000",   # changed in revision 2
        note="SHADOW REVISION — CONTENT MODIFIED AFTER SIGNING"
    )
    return original, shadow, "REVIEW_REQUIRED"


def _scenario_d() -> Tuple[bytes, bytes, str]:
    """Visual signature duplication — two near-identical handwriting images."""
    from simulation.sample_generator import build_duplicate_sig_pdf
    pdf = build_duplicate_sig_pdf(sig_count=2, sig_seed=99)
    return pdf, pdf, "REVIEW_REQUIRED"


def _scenario_e() -> Tuple[bytes, bytes, str]:
    """ELA manipulation — image region has elevated JPEG residuals."""
    from simulation.sample_generator import build_ela_target, build_tampered_bytes
    original = build_ela_target()
    altered  = build_tampered_bytes(original, change_offset=400)
    return original, altered, "REVIEW_REQUIRED"


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
             "An unchanged synthetic signed PDF. All checks should pass.",
             "clean", _scenario_a, "CLEAN"),
    Scenario("B", "Scenario B — Signed-Byte Tampering",
             "A signed PDF with one byte flipped — SHA-256 digest breaks.",
             "tampered", _scenario_b, "TAMPERING_DETECTED"),
    Scenario("C", "Scenario C — Shadow Attack",
             "Two-revision PDF: signed at $1,000 but current shows $9,000.",
             "shadow", _scenario_c, "REVIEW_REQUIRED"),
    Scenario("D", "Scenario D — Visual Signature Duplication",
             "Two near-identical handwriting images — ORB/RANSAC detects the copy.",
             "visual", _scenario_d, "REVIEW_REQUIRED"),
    Scenario("E", "Scenario E — Image Manipulation (ELA)",
             "Synthetically altered image region with elevated ELA residuals.",
             "ela", _scenario_e, "REVIEW_REQUIRED"),
    Scenario("F", "Scenario F — Unsigned Document",
             "A plain document with no signature. Absence of sig ≠ forgery.",
             "unsigned", _scenario_f, "INCONCLUSIVE"),
]


def get_scenario(scenario_id: str) -> Optional[Scenario]:
    for s in ALL_SCENARIOS:
        if s.id == scenario_id:
            return s
    return None
