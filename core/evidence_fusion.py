"""
Module 10 — Explainable evidence fusion.

Rule-based decision engine. Never uses CLEAN — a document with an untrusted
certificate cannot have its authenticity established; the best outcome is
NO TAMPERING DETECTED with an INCONCLUSIVE overall verdict.

Verdicts:
  TAMPERING DETECTED  — cryptographic integrity failure confirmed
  REVIEW REQUIRED     — suspicious findings; manual investigation needed
  INCONCLUSIVE        — insufficient evidence for a definitive verdict
  UNSUPPORTED         — document could not be processed

Integrity statuses (separate from overall verdict):
  NO TAMPERING DETECTED   — signed bytes intact
  INTEGRITY FAILURE       — signed bytes modified
  INTEGRITY NOT ESTABLISHED — no crypto sig or verification incomplete
  NOT APPLICABLE          — unsigned document
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any

import config


class Verdict(str, Enum):
    TAMPERING_DETECTED = "TAMPERING DETECTED"
    REVIEW_REQUIRED    = "REVIEW REQUIRED"
    INCONCLUSIVE       = "INCONCLUSIVE"
    UNSUPPORTED        = "UNSUPPORTED"
    # CLEAN intentionally removed — self-signed cert cannot establish authenticity


class IntegrityVerdict(str, Enum):
    NO_TAMPERING        = "NO TAMPERING DETECTED"
    INTEGRITY_FAILURE   = "INTEGRITY FAILURE"
    NOT_ESTABLISHED     = "INTEGRITY NOT ESTABLISHED"
    NOT_APPLICABLE      = "NOT APPLICABLE"


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH     = "HIGH"
    MEDIUM   = "MEDIUM"
    LOW      = "LOW"
    INFO     = "INFO"


@dataclass
class Finding:
    code:          str
    severity:      Severity
    title:         str
    description:   str
    module:        str
    measurements:  str = ""
    page:          Optional[int] = None
    evidence:      Optional[str] = None
    limitation:    str = ""


@dataclass
class FusionResult:
    verdict:           Verdict
    integrity_verdict: IntegrityVerdict
    confidence_label:  str           # "High" | "Moderate" | "Low"
    explanation:       str
    findings:          List[Finding]
    affected_pages:    List[int]
    completeness:      str
    limitations:       List[str]
    module_scores:     Dict[str, str]


def fuse(
    parsed          = None,
    classification  = None,
    crypto_report   = None,
    revision_result = None,
    loc_result      = None,
    ela_result      = None,
    orb_result      = None,
    ransac_result   = None,
) -> FusionResult:

    findings:       List[Finding]  = []
    limitations:    List[str]      = []
    affected_pages: List[int]      = []
    module_scores:  Dict[str, str] = {}

    # ── UNSUPPORTED ────────────────────────────────────────────────────────
    if parsed is not None and parsed.error:
        return FusionResult(
            Verdict.UNSUPPORTED, IntegrityVerdict.NOT_APPLICABLE, "N/A",
            f"The document could not be processed: {parsed.error}",
            [], [], "No analysis performed.",
            ["Input document was unreadable or unsupported."], {}
        )

    # ── Module 2: Classification ───────────────────────────────────────────
    if classification is not None:
        module_scores["Classification"] = classification.doc_class.value

    # ── Module 3: Cryptographic integrity ─────────────────────────────────
    crypto_done      = False
    integrity_verdict = IntegrityVerdict.NOT_APPLICABLE
    any_crypto_fail  = False
    any_modpol_fail  = False

    if crypto_report is not None and crypto_report.total_sigs > 0:
        crypto_done = True
        from core.crypto_verifier import IntegrityStatus, ModpolicyStatus, TrustStatus

        for r in crypto_report.results:
            # Signed-byte integrity
            if r.integrity_status == IntegrityStatus.FAIL:
                any_crypto_fail = True
                findings.append(Finding(
                    code="CRYPTO-001",
                    severity=Severity.CRITICAL,
                    title="Signed-byte integrity failure",
                    description=(
                        f"Signature field '{r.field_name}': the recorded digest of the "
                        "signed bytes does not match the recorded value. The document "
                        "has been modified after signing."
                    ),
                    module="Cryptographic Verification",
                    measurements=f"integrity_status={r.integrity_status}",
                    evidence=r.error,
                    limitation="This is a definitive cryptographic finding.",
                ))
                affected_pages.extend(range(parsed.page_count) if parsed is not None else [])

            elif r.integrity_status == IntegrityStatus.UNKNOWN:
                findings.append(Finding(
                    code="CRYPTO-005",
                    severity=Severity.MEDIUM,
                    title="Cryptographic integrity could not be established",
                    description=(
                        f"Signature field '{r.field_name}': verification did not "
                        "complete — results are inconclusive."
                    ),
                    module="Cryptographic Verification",
                    measurements=r.completeness,
                    limitation="Install pyHanko for complete CMS verification.",
                ))

            # Mathematical validity failure
            if r.math_valid is False:
                findings.append(Finding(
                    code="CRYPTO-002",
                    severity=Severity.CRITICAL,
                    title="Digital signature mathematically invalid",
                    description=(
                        f"Signature field '{r.field_name}': public-key verification "
                        "over the signed digest failed."
                    ),
                    module="Cryptographic Verification",
                    measurements=f"math_valid={r.math_valid}",
                    limitation="Definitive cryptographic failure.",
                ))
                any_crypto_fail = True

            # Modification policy violation
            from core.crypto_verifier import ModpolicyStatus
            if r.modpolicy_status == ModpolicyStatus.VIOLATION:
                any_modpol_fail = True
                findings.append(Finding(
                    code="CRYPTO-003",
                    severity=Severity.HIGH,
                    title="Modification-policy violation",
                    description=(
                        f"Signature field '{r.field_name}': changes were made that "
                        "violate the document's DocMDP/FieldMDP modification policy."
                    ),
                    module="Cryptographic Verification",
                    measurements=f"modpolicy={r.modpolicy_status}",
                ))

            if r.revocation_status == 'REVOKED':
                findings.append(Finding('CERT-001',Severity.HIGH,'Signing certificate is revoked',
                    "Offline revocation evidence identifies a revoked certificate in the signing path. Byte integrity and certificate status are separate.",
                    'Certificate lifecycle',measurements=r.revocation_status))
            if r.timestamp_status == 'INVALID TIMESTAMP':
                findings.append(Finding('TIME-001',Severity.HIGH,'Timestamp verification failed',
                    'The RFC3161 timestamp did not pass cryptographic checks. Do not rely on its claimed time.',
                    'Certificate lifecycle'))
            if r.integrity_status != 'UNKNOWN' and (r.coverage_level not in ('ENTIRE_FILE','ENTIRE_REVISION') or
                    (r.byte_range and not r.byte_range.structurally_valid)):
                findings.append(Finding('CRYPTO-006',Severity.HIGH,'Nonstandard signature coverage',
                    'The signature does not establish coverage of a complete parsed revision. A matching digest alone is insufficient.',
                    'Cryptographic Verification',measurements=r.coverage_level))
            # Certificate trust note
            from core.crypto_verifier import TrustStatus
            if r.trust_status in (TrustStatus.SELF_SIGNED, TrustStatus.UNKNOWN_ISSUER, TrustStatus.EXPIRED):
                limitations.append(
                    f"Certificate for '{r.field_name}' is {r.trust_status}. "
                    "Mathematical integrity may be valid but signer identity CANNOT "
                    "be established from this certificate alone."
                )

            # ByteRange coverage note
            if r.byte_range and not r.byte_range.covers_full_file:
                findings.append(Finding(
                    code="CRYPTO-004",
                    severity=Severity.LOW,
                    title="Signature does not cover the complete current file",
                    description=(
                        f"Signature field '{r.field_name}' was created on an earlier "
                        "revision. Post-signing incremental updates exist and are not "
                        "covered by this signature."
                    ),
                    module="Cryptographic Verification",
                    measurements=str(r.byte_range.validation_notes),
                    limitation="Incremental updates may be legitimate (e.g. annotations).",
                ))

        # Set integrity verdict
        if any_crypto_fail:
            integrity_verdict = IntegrityVerdict.INTEGRITY_FAILURE
        else:
            all_pass = all(
                r.integrity_status == "PASS" for r in crypto_report.results
            )
            if all_pass:
                integrity_verdict = IntegrityVerdict.NO_TAMPERING
            else:
                integrity_verdict = IntegrityVerdict.NOT_ESTABLISHED

        crypto_status = "FAIL" if any_crypto_fail else ("PASS" if integrity_verdict == IntegrityVerdict.NO_TAMPERING else "INCOMPLETE")
        module_scores["Cryptographic Verification"] = crypto_status

    elif crypto_report is not None and crypto_report.total_sigs == 0:
        integrity_verdict = IntegrityVerdict.NOT_APPLICABLE
        module_scores["Cryptographic Verification"] = "N/A — no signatures"
        limitations.append(
            "No cryptographic signatures found. Document integrity cannot be "
            "verified cryptographically."
        )

    # ── Module 4: Revision / shadow ────────────────────────────────────────
    if revision_result is not None:
        if revision_result.shadow_suspect:
            sev = Severity.HIGH
            findings.append(Finding(
                code="SHADOW-001",
                severity=sev,
                title="Post-signing visible content change",
                description=(
                    f"The signed revision and the current revision differ on "
                    f"{revision_result.changed_area_pct:.1f}% of the page area. "
                    "This is a post-signing content change; it does not by itself establish a pre-planned shadow exploit. Content "
                    "displayed to the signer differs from content shown to later readers."
                ),
                module="Revision Analysis",
                measurements=(
                    f"changed_area={revision_result.changed_area_pct:.1f}% | "
                    f"revisions={len(revision_result.revisions)} | "
                    f"method={revision_result.discovery_method}"
                ),
                page=getattr(revision_result, "page_index", 0),
                limitation=(
                    "Shadow-attack detection uses rendered image comparison. "
                    "Attacks with identical renders are not detectable. "
                    "Legitimate annotations/signatures also create incremental updates."
                ),
            ))
            affected_pages.append(getattr(revision_result, "page_index", 0))

        if revision_result.text_diff_summary:
            findings.append(Finding(
                code="SHADOW-002",
                severity=Severity.MEDIUM,
                title="Text content changed between signed and current revision",
                description=revision_result.text_diff_summary,
                module="Revision Analysis",
                limitation="Text extraction may miss some content types.",
            ))

        if revision_result.metadata_changed:
            findings.append(Finding(
                code="REV-001",
                severity=Severity.LOW,
                title="Document metadata differs between revisions",
                description="Metadata (author, modification date, etc.) was changed in a later revision.",
                module="Revision Analysis",
                limitation="Metadata changes are often legitimate (e.g. viewer updates mod-date).",
            ))

        for lim in revision_result.limitations:
            if lim not in limitations:
                limitations.append(lim)

        module_scores["Revision Analysis"] = (
            f"{len(revision_result.revisions)} revision(s) | "
            f"{'shadow suspect' if revision_result.shadow_suspect else 'no shadow'} | "
            f"method={revision_result.discovery_method}"
        )

    # ── Module 5: Localisation ─────────────────────────────────────────────
    if loc_result is not None:
        n_cand = len(loc_result.candidates)
        module_scores["Signature Localisation"] = (
            f"{n_cand} candidate(s) — heuristic scores, not calibrated probabilities"
        )
        if n_cand == 0:
            limitations.append(
                "No visual signature candidates detected. The document may be "
                "unsigned, the signature may be very faint, or localisation may "
                "have missed it."
            )

    # ── Module 6: ELA ──────────────────────────────────────────────────────
    ela_flag = False
    if ela_result is not None and ela_result.error is None:
        if ela_result.mean_residual > config.ELA_HIGH_THRESHOLD or ela_result.high_pct > 10.0:
            ela_flag = True
            findings.append(Finding(
                code="ELA-001",
                severity=Severity.MEDIUM,
                title="Elevated ELA residual",
                description=(
                    f"Mean residual: {ela_result.mean_residual:.1f} | "
                    f"High-energy pixels: {ela_result.high_pct:.1f}% | "
                    f"Quality: {ela_result.quality_used}."
                ),
                module="ELA",
                measurements=(
                    f"mean={ela_result.mean_residual:.2f} | "
                    f"max={ela_result.max_residual:.2f} | "
                    f"std={ela_result.std_residual:.2f}"
                ),
                limitation=(
                    "ELA elevated residuals can be caused by high-contrast edges, "
                    "fine textures, gradients or printed text — not only manipulation. "
                    "ELA is a supporting indicator, not proof of forgery."
                ),
            ))
        module_scores["ELA"] = (
            f"mean={ela_result.mean_residual:.1f} @ Q{ela_result.quality_used} "
            f"({'elevated' if ela_flag else 'normal'})"
        )
        if ela_result.sweep_summary:
            module_scores["ELA multi-quality"] = ela_result.sweep_summary

        limitations.append(
            "ELA applied to rendered PDF images may not reflect the original "
            "JPEG compression history of embedded content."
        )

    # ── Module 7+8: ORB / RANSAC ───────────────────────────────────────────
    ransac_flag = False
    if ransac_result is not None:
        if ransac_result.geometric_ok:
            ransac_flag = True
            findings.append(Finding(
                code="ORB-001",
                severity=Severity.MEDIUM,
                title="Geometrically consistent duplicate region detected",
                description=(
                    f"{ransac_result.inlier_count}/{ransac_result.matches_before} "
                    f"RANSAC inliers ({ransac_result.inlier_ratio:.0%}) — a possible "
                    "copy-move or visually duplicated signature region."
                ),
                module="ORB/RANSAC",
                measurements=(
                    f"inliers={ransac_result.inlier_count} | "
                    f"ratio={ransac_result.inlier_ratio:.0%} | "
                    f"coverage={ransac_result.spatial_coverage:.0%}"
                ),
                limitation=(
                    "Visual similarity does not establish signer identity or "
                    "prove unauthorised reuse. Legitimate repeated graphics "
                    "can produce false matches."
                ),
            ))
            limitations.append(
                "ORB/RANSAC visual similarity does not prove unauthorised "
                "signature reuse or establish signer identity."
            )
        module_scores["ORB/RANSAC"] = (
            f"inliers={ransac_result.inlier_count} | "
            f"ratio={ransac_result.inlier_ratio:.0%} | "
            f"geometric_ok={ransac_result.geometric_ok}"
        )

    # ── Verdict logic ──────────────────────────────────────────────────────
    critical = [f for f in findings if f.severity == Severity.CRITICAL]
    high     = [f for f in findings if f.severity == Severity.HIGH]

    if critical:
        verdict    = Verdict.TAMPERING_DETECTED
        conf_label = "High"
        explanation = (
            "One or more cryptographic checks failed: signed bytes were altered "
            "or the public-key signature is invalid. "
            + " | ".join(f.title for f in critical)
        )
    elif high:
        verdict    = Verdict.REVIEW_REQUIRED
        conf_label = "Moderate"
        explanation = (
            "No cryptographic integrity failure detected, but significant "
            "anomalies require manual expert review. "
            + " | ".join(f.title for f in high)
        )
    elif ela_flag or ransac_flag:
        verdict    = Verdict.REVIEW_REQUIRED
        conf_label = "Low"
        explanation = (
            "Supporting forensic indicators (ELA or ORB/RANSAC) suggest possible "
            "manipulation, but are insufficient for a definitive conclusion. "
            "Manual expert review is recommended."
        )
    elif crypto_done and integrity_verdict == IntegrityVerdict.NO_TAMPERING:
        verdict    = Verdict.INCONCLUSIVE
        conf_label = "Moderate"
        explanation = (
            "Signed-byte integrity verified — no cryptographic evidence of tampering. "
            "No suspicious revision changes or strong visual evidence detected. "
            "NOTE: This verdict does not establish document authenticity or signer "
            "identity. Certificate trust, revocation, timestamps and signer identity must be "
            "reviewed separately."
        )
    else:
        verdict    = Verdict.INCONCLUSIVE
        conf_label = "Low"
        explanation = (
            "Insufficient or conflicting evidence across the analysed modules. "
            "The document may not contain enough forensic signals for a definitive verdict."
        )

    # Standard limitations
    if not any(
        "expert review" in l.lower() or "automated analysis" in l.lower()
        for l in limitations
    ):
        limitations.append(
            "Results are based on automated analysis. Expert human review is "
            "required before use in any legal, compliance or operational context."
        )

    limitations.append(
        "Synthetic evaluation does not establish real-world generalisation performance."
    )

    # Completeness string
    done = []
    if crypto_done:         done.append("Cryptographic")
    if revision_result:     done.append("Revision")
    if loc_result:          done.append("Localisation")
    if ela_result:          done.append("ELA")
    if ransac_result:       done.append("ORB/RANSAC")
    completeness = ("Modules completed: " + ", ".join(done)) if done else "No modules completed."

    return FusionResult(
        verdict=verdict,
        integrity_verdict=integrity_verdict,
        confidence_label=conf_label,
        explanation=explanation,
        findings=findings,
        affected_pages=sorted(set(affected_pages)),
        completeness=completeness,
        limitations=limitations,
        module_scores=module_scores,
    )
