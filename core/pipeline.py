"""
Full end-to-end analysis pipeline.
"""
from __future__ import annotations

import hashlib, time
from dataclasses import dataclass, field
from typing import Optional

from core.pdf_parser          import ParsedDocument, parse_pdf, validate_pdf, ValidationResult
from core.document_classifier import ClassificationResult, DocClass, classify
from core.crypto_verifier     import CryptoReport, verify as crypto_verify
from core.revision_analyzer   import RevisionAnalysisResult, analyze as revision_analyze
from core.signature_localizer import LocalizationResult, localize
from core.ela_detector        import ELAResult, run_ela
from core.orb_matcher         import ORBResult, match as orb_match
from core.ransac_verifier     import RANSACResult, verify as ransac_verify
from core.evidence_fusion     import FusionResult, fuse
from core.audit_logger        import append_record
import config


@dataclass
class PipelineResult:
    validation:    ValidationResult
    parsed:        Optional[ParsedDocument]       = None
    classification: Optional[ClassificationResult] = None
    crypto:        Optional[CryptoReport]         = None
    revision:      Optional[RevisionAnalysisResult] = None
    localization:  Optional[LocalizationResult]   = None
    ela:           Optional[ELAResult]            = None
    orb:           Optional[ORBResult]            = None
    ransac:        Optional[RANSACResult]         = None
    fusion:        Optional[FusionResult]         = None
    elapsed_sec:   float                          = 0.0
    stage_times:   dict = field(default_factory=dict)
    analysis_ts:   str  = ""    # ISO timestamp of analysis


def run(raw: bytes, filename: str = "document.pdf",
        run_ela_flag: bool = True,
        run_orb_flag: bool = True,
        ela_quality:  int  = config.ELA_DEFAULT_QUALITY,
        ela_amp:      int  = config.ELA_DEFAULT_AMP) -> PipelineResult:

    t0 = time.perf_counter()
    stage_times: dict = {}
    analysis_ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # Validation
    validation = validate_pdf(raw, filename)
    if not validation.valid:
        return PipelineResult(validation, analysis_ts=analysis_ts)

    # Parse
    t = time.perf_counter()
    parsed = parse_pdf(raw, filename)
    stage_times["parse"] = round(time.perf_counter() - t, 3)

    if parsed.error:
        return PipelineResult(validation, parsed, analysis_ts=analysis_ts)

    # Classify
    t = time.perf_counter()
    classification = classify(parsed)
    stage_times["classify"] = round(time.perf_counter() - t, 3)

    # Cryptographic verification
    crypto = None
    if classification.doc_class == DocClass.CRYPTOGRAPHICALLY_SIGNED:
        t = time.perf_counter()
        crypto = crypto_verify(raw)
        stage_times["crypto"] = round(time.perf_counter() - t, 3)

    # Revision analysis
    t = time.perf_counter()
    revision = revision_analyze(raw, page_index=0)
    stage_times["revision"] = round(time.perf_counter() - t, 3)

    # Signature localisation
    t = time.perf_counter()
    loc = localize(raw, page_index=0)
    stage_times["localise"] = round(time.perf_counter() - t, 3)

    # ELA
    ela = None
    if run_ela_flag:
        t = time.perf_counter()
        if loc.candidates:
            ela_img = loc.candidates[0].crop
        elif parsed.page_images:
            ela_img = parsed.page_images[0]
        else:
            ela_img = None
        if ela_img:
            ela = run_ela(ela_img, quality=ela_quality, amplification=ela_amp)
        stage_times["ela"] = round(time.perf_counter() - t, 3)

    # ORB + RANSAC
    orb = ransac = None
    if run_orb_flag and len(loc.candidates) >= 2:
        t = time.perf_counter()
        orb = orb_match(loc.candidates[0].crop, loc.candidates[1].crop)
        stage_times["orb"] = round(time.perf_counter() - t, 3)

        t = time.perf_counter()
        ransac = ransac_verify(orb)
        stage_times["ransac"] = round(time.perf_counter() - t, 3)

    # Evidence fusion
    t = time.perf_counter()
    fusion = fuse(
        parsed=parsed, classification=classification,
        crypto_report=crypto, revision_result=revision,
        loc_result=loc, ela_result=ela,
        orb_result=orb, ransac_result=ransac,
    )
    stage_times["fusion"] = round(time.perf_counter() - t, 3)

    # Audit log
    try:
        append_record(parsed.sha256, fusion.verdict.value)
    except Exception:
        pass

    total = round(time.perf_counter() - t0, 3)

    return PipelineResult(
        validation=validation, parsed=parsed,
        classification=classification, crypto=crypto,
        revision=revision, localization=loc,
        ela=ela, orb=orb, ransac=ransac, fusion=fusion,
        elapsed_sec=total, stage_times=stage_times,
        analysis_ts=analysis_ts,
    )
