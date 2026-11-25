"""Module 11a — JSON forensic report generator."""
from __future__ import annotations
import json, time
from typing import Any
from core.pipeline import PipelineResult
from core.review import finding_id


def _safe(obj: Any) -> Any:
    """Recursively make an object JSON-serialisable."""
    import numpy as np
    if obj is None:
        return None
    if isinstance(obj, (bool, int, str, float)):
        return obj
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.ndarray,)):
        return obj.tolist()
    if hasattr(obj, "value"):            # Enum
        return obj.value
    if isinstance(obj, (list, tuple)):
        return [_safe(i) for i in obj]
    if isinstance(obj, dict):
        return {str(k): _safe(v) for k, v in obj.items()}
    if hasattr(obj, "__dict__"):
        return {k: _safe(v) for k, v in obj.__dict__.items()
                if not k.startswith("_") and not callable(v)}
    return str(obj)


def build_report(result: PipelineResult) -> dict:
    r: dict = {
        "report_type":     "SignGuard Forensic Report",
        "schema_version":  "2.0",
        "generated_at":    time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "analysis_ts":     result.analysis_ts,
        "disclaimer":      (
            "This report is produced by SignGuard for educational and research purposes. "
            "Results require qualified expert review before any legal, compliance, "
            "or operational use. This report is NOT an authenticity certificate."
        ),
        "document":        {},
        "classification":  {},
        "cryptographic":   {},
        "revision":        {},
        "localisation":    {},
        "ela":             {},
        "orb_ransac":      {},
        "verdict":         {},
        "integrity_verdict": "NOT APPLICABLE",
        "limitations":     [],
        "processing":      {},
    }

    # Document
    if result.parsed:
        p = result.parsed
        r["document"] = {
            "filename":   p.file_name,
            "sha256":     p.sha256,
            "size_bytes": p.file_size,
            "page_count": p.page_count,
            "metadata":   _safe(p.metadata),
            "encrypted":  p.is_encrypted,
            "sig_fields": p.sig_field_count,
        }

    # Classification
    if result.classification:
        c = result.classification
        r["classification"] = {
            "class":          c.doc_class.value,
            "crypto_sigs":    c.crypto_sig_count,
            "visual_candidates": c.visual_candidates,
            "explanation":    c.explanation,
            "completeness":   c.completeness,
        }

    # Cryptographic
    if result.crypto:
        cr = result.crypto
        sigs_out = []
        for sig in cr.results:
            entry: dict = {
                "field":              sig.field_name,
                "integrity_status":   sig.integrity_status,
                "math_valid":         sig.math_valid,
                "trust_status":       sig.trust_status,
                "modpolicy_status":   sig.modpolicy_status,
                "identity_status":    sig.identity_status,
                "completeness":       sig.completeness,
                "modification_level": sig.modification_level,
                "coverage_level": sig.coverage_level,
                "revocation_status": sig.revocation_status,
                "timestamp_status": sig.timestamp_status,
                "timestamp_details": _safe(sig.timestamp_details),
                "digest_alg":         sig.digest_alg,
                "sig_alg":            sig.sig_alg,
                "signing_time":       sig.signing_time,
                "signed_attrs_ok":    sig.signed_attrs_ok,
                "details":            sig.details,
            }
            if sig.byte_range:
                br = sig.byte_range
                entry["byte_range"] = {
                    "raw_values":          br.raw_values,
                    "structurally_valid":  br.structurally_valid,
                    "covers_full_file":    br.covers_full_file,
                    "covers_signed_rev":   br.covers_signed_rev,
                    "notes":               br.validation_notes,
                }
            if sig.cert_info:
                ci = sig.cert_info
                entry["cert"] = {
                    "subject":      ci.subject,
                    "issuer":       ci.issuer,
                    "serial":       ci.serial,
                    "not_before":   ci.not_before,
                    "not_after":    ci.not_after,
                    "self_signed":  ci.is_self_signed,
                    "is_test_cert": ci.is_test_cert,
                    "key_alg":      ci.key_algorithm,
                }
            if sig.error:
                entry["error"] = sig.error
            sigs_out.append(entry)

        r["cryptographic"] = {
            "total_sigs":   cr.total_sigs,
            "total_discovered": cr.total_discovered,
            "all_valid":    cr.all_valid,
            "pyhanko_used": cr.pyhanko_used,
            "summary":      cr.summary,
            "signatures":   sigs_out,
        }

    # Revision
    if result.revision:
        rv = result.revision
        r["revision"] = {
            "revision_count":    len(rv.revisions),
            "has_incremental":   rv.has_incremental_updates,
            "shadow_suspect":    rv.shadow_suspect,
            "changed_area_pct":  rv.changed_area_pct,
            "text_diff":         rv.text_diff_summary,
            "metadata_changed":  rv.metadata_changed,
            "discovery_method":  rv.discovery_method,
            "summary":           rv.summary,
            "revisions": [
                {
                    "index":        rev.index,
                    "start":        rev.start_offset,
                    "end":          rev.end_offset,
                    "is_signed":    rev.is_signed,
                    "page_count":   rev.page_count,
                }
                for rev in rv.revisions
            ],
        }

    # Localisation
    if result.localization:
        lc = result.localization
        r["localisation"] = {
            "page":       lc.page_index,
            "candidates": [
                {"page": c.page, "bbox": list(c.bbox),
                 "heuristic_score": round(c.confidence, 3)}
                for c in lc.candidates
            ],
            "note": "Confidence values are heuristic scores, not calibrated probabilities.",
            "error": lc.error,
        }

    # ELA
    if result.ela:
        el = result.ela
        multi = {}
        for q, s in el.multi_quality.items():
            multi[str(q)] = {
                "mean": round(s.mean_residual, 3),
                "max":  round(s.max_residual, 3),
                "std":  round(s.std_residual, 3),
                "high_pct": round(s.high_pct, 2),
            }
        r["ela"] = {
            "quality_active":  el.quality_used,
            "amplification":   el.amp_used,
            "mean_residual":   round(el.mean_residual, 3),
            "max_residual":    round(el.max_residual, 3),
            "std_residual":    round(el.std_residual, 3),
            "high_pct":        round(el.high_pct, 2),
            "finding":         el.finding,
            "sweep_summary":   el.sweep_summary,
            "multi_quality":   multi,
            "error":           el.error,
        }

    # ORB / RANSAC
    orb_data: dict = {}
    if result.orb:
        orb_data.update({
            "n_kp_a":      result.orb.n_kp_a,
            "n_kp_b":      result.orb.n_kp_b,
            "raw_matches": result.orb.n_raw_matches,
            "filtered":    result.orb.n_filtered,
        })
    if result.ransac:
        orb_data.update({
            "ransac_inliers":   result.ransac.inlier_count,
            "ransac_outliers":  result.ransac.outlier_count,
            "inlier_ratio":     round(result.ransac.inlier_ratio, 3),
            "geometric_ok":     result.ransac.geometric_ok,
            "spatial_coverage": round(result.ransac.spatial_coverage, 3),
            "summary":          result.ransac.summary,
        })
    if orb_data:
        r["orb_ransac"] = orb_data

    # Verdict
    if result.fusion:
        fu = result.fusion
        r["integrity_verdict"] = fu.integrity_verdict.value
        r["verdict"] = {
            "verdict":           fu.verdict.value,
            "integrity_verdict": fu.integrity_verdict.value,
            "confidence_label":  fu.confidence_label,
            "explanation":       fu.explanation,
            "completeness":      fu.completeness,
            "findings": [
                {
                    "finding_id": finding_id(result.parsed.sha256 if result.parsed else "", f),
                    "code":        f.code,
                    "severity":    f.severity.value,
                    "title":       f.title,
                    "description": f.description,
                    "module":      f.module,
                    "measurements":f.measurements,
                    "page":        f.page,
                    "limitation":  f.limitation,
                }
                for f in fu.findings
            ],
            "module_scores": fu.module_scores,
        }
        r["limitations"] = fu.limitations

    r["provenance"] = _safe(result.provenance)
    r["static_content"] = _safe(result.active_content)
    r["revision_timeline"] = _safe(result.timeline)
    r["renderer_comparison"] = _safe(result.renderer_comparison)
    r["coverage"] = _safe(result.coverage)
    r["page_results"] = _safe(result.page_results)
    r["candidate_pairs"] = _safe(result.pair_results)
    r["audit_error"] = result.audit_error
    r["processing_error"] = result.processing_error

    # Processing
    r["processing"] = {
        "total_seconds": result.elapsed_sec,
        "stage_times":   result.stage_times,
    }

    return r


def to_json(result: PipelineResult) -> str:
    return json.dumps(_safe(build_report(result)), indent=2, default=str)
