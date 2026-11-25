"""Bounded, isolated PDF analysis with explicit coverage and per-page evidence."""
from __future__ import annotations
import itertools
import time
from dataclasses import dataclass, field
from typing import Optional
from core.pdf_parser import ParsedDocument, parse_pdf, validate_pdf, ValidationResult
from core.document_classifier import ClassificationResult, DocClass, classify
from core.crypto_verifier import CryptoReport, verify as crypto_verify
from core.revision_analyzer import RevisionAnalysisResult, analyze as revision_analyze
from core.signature_localizer import LocalizationResult, localize
from core.ela_detector import ELAResult, run_ela
from core.orb_matcher import ORBResult, match as orb_match
from core.ransac_verifier import RANSACResult, verify as ransac_verify
from core.evidence_fusion import FusionResult, fuse, Verdict, IntegrityVerdict
from core.audit_logger import append_record
import config


@dataclass
class PipelineResult:
    validation: ValidationResult
    parsed: Optional[ParsedDocument] = None
    classification: Optional[ClassificationResult] = None
    crypto: Optional[CryptoReport] = None
    revision: Optional[RevisionAnalysisResult] = None
    localization: Optional[LocalizationResult] = None
    ela: Optional[ELAResult] = None
    orb: Optional[ORBResult] = None
    ransac: Optional[RANSACResult] = None
    fusion: Optional[FusionResult] = None
    elapsed_sec: float = 0.0
    stage_times: dict = field(default_factory=dict)
    analysis_ts: str = ''
    coverage: dict = field(default_factory=dict)
    page_results: list = field(default_factory=list)
    pair_results: list = field(default_factory=list)
    audit_error: Optional[str] = None
    processing_error: Optional[str] = None


def _failure(reason, filename='document.pdf'):
    fusion = fuse()
    fusion.verdict = Verdict.UNSUPPORTED
    fusion.integrity_verdict = IntegrityVerdict.NOT_ESTABLISHED
    fusion.explanation = reason
    fusion.completeness = 'Analysis incomplete; no assurance can be drawn.'
    fusion.limitations.append(reason)
    return PipelineResult(ValidationResult(False, reason), fusion=fusion,
                          processing_error=reason,
                          analysis_ts=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                          coverage={'complete': False})


def run(raw, filename='document.pdf', run_ela_flag=True, run_orb_flag=True,
        ela_quality=config.ELA_DEFAULT_QUALITY, ela_amp=config.ELA_DEFAULT_AMP,
        isolated=True, record_audit=True, analysis_mode='full', timeout=None):
    """Public entry point. UI/CLI default to a disposable resource-limited process."""
    validation = validate_pdf(raw, filename)
    if not validation.valid:
        return _failure(validation.reason, filename)
    options = dict(run_ela_flag=run_ela_flag, run_orb_flag=run_orb_flag,
                   ela_quality=ela_quality, ela_amp=ela_amp, analysis_mode=analysis_mode)
    if isolated:
        from core.worker import execute
        result = execute(raw, filename, options, timeout)
    else:
        result = _run(raw, filename, **options)
    if config.PUBLIC_DEMO:
        result.coverage["audit_persistence"] = "Disabled for public demo; download your report."
    if record_audit and not config.PUBLIC_DEMO and result.parsed and result.fusion:
        try:
            append_record(result.parsed.sha256, result.fusion.verdict.value)
        except Exception as exc:
            result.audit_error = str(exc)
            result.fusion.limitations.append(f'Audit record was NOT saved: {exc}')
    return result


def _run(raw, filename, run_ela_flag=True, run_orb_flag=True,
         ela_quality=config.ELA_DEFAULT_QUALITY, ela_amp=config.ELA_DEFAULT_AMP,
         analysis_mode='full'):
    if analysis_mode not in ('crypto_only', 'crypto_revision', 'full'):
        raise ValueError('Unknown analysis mode')
    start = time.perf_counter()
    parsed = parse_pdf(raw, filename)
    if parsed.error:
        result = _failure(parsed.error, filename)
        result.parsed = parsed
        return result
    cls = classify(parsed)
    crypto = crypto_verify(raw, skip_diff=analysis_mode == "crypto_only") if cls.doc_class == DocClass.CRYPTOGRAPHICALLY_SIGNED else None
    result = PipelineResult(ValidationResult(True, 'OK'), parsed=parsed,
                            classification=cls, crypto=crypto,
                            analysis_ts=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
    incomplete = []
    if crypto and crypto.total_discovered > crypto.total_sigs:
        incomplete.append(f'Only the first {config.MAX_SIGNATURES} signatures were verified.')
    all_candidates = []
    fusions = []
    candidates_seen = 0
    for page in range(parsed.page_count):
        rev = revision_analyze(raw, page) if analysis_mode != 'crypto_only' else None
        loc = localize(raw, page) if analysis_mode == 'full' else None
        if rev and rev.error:
            incomplete.append(f'Page {page + 1} revision analysis: {rev.error}')
        if loc and loc.error:
            incomplete.append(f'Page {page + 1} localisation: {loc.error}')
        candidates = loc.candidates if loc else []
        candidates_seen += loc.total_candidates if loc else 0
        if loc and loc.truncated:
            incomplete.append(f"Page {page+1}: candidate limit reached; analysed {len(candidates)} of {loc.total_candidates} regions.")
        remaining = max(0, config.MAX_ANALYSIS_CANDIDATES - len(all_candidates))
        kept = candidates[:remaining]
        if len(kept) < len(candidates):
            incomplete.append('Document candidate budget reached; some candidates were omitted.')
        all_candidates.extend(kept)
        elas = []
        if run_ela_flag and analysis_mode == 'full':
            images = [c.crop for c in kept] or [parsed.page_images[page]]
            elas = [run_ela(im, quality=ela_quality, amplification=ela_amp) for im in images]
        for e in elas:
            if e.error:
                incomplete.append(f"Page {page+1} ELA incomplete: {e.error}")
        ela = max(elas, key=lambda e: (e.mean_residual > config.ELA_HIGH_THRESHOLD or e.high_pct > 10, e.mean_residual), default=None)
        fu = fuse(parsed=parsed, classification=cls, crypto_report=crypto,
                  revision_result=rev, loc_result=loc, ela_result=ela)
        for finding in fu.findings:
            if finding.module in ('Revision Analysis', 'ELA'):
                finding.page = page
        fusions.append(fu)
        result.page_results.append({'page': page, 'candidate_count': len(candidates),
            'candidates': [{'bbox': [int(v) for v in c.bbox], 'heuristic_score': float(c.confidence)} for c in candidates],
            'revision_changed_area_pct': rev.changed_area_pct if rev else None,
            'shadow_suspect': rev.shadow_suspect if rev else None,
            'ela': [{'mean': e.mean_residual, 'high_pct': e.high_pct, 'error': e.error} for e in elas]})
        if result.revision is None or (rev and rev.shadow_suspect):
            result.revision = rev
        # Keep only representative full-resolution visualisations in memory.
        if result.localization is None or (loc and len(candidates) > len(result.localization.candidates)):
            result.localization = loc
        if ela and (result.ela is None or ela.mean_residual > result.ela.mean_residual):
            result.ela = ela
    pair_count = len(all_candidates) * (len(all_candidates) - 1) // 2
    if run_orb_flag and analysis_mode == 'full':
        for a, b in itertools.islice(itertools.combinations(all_candidates, 2), config.MAX_CANDIDATE_PAIRS):
            orb = orb_match(a.crop, b.crop)
            ransac = ransac_verify(orb)
            result.pair_results.append({'pages': [a.page, b.page], 'boxes': [a.bbox, b.bbox],
                'inliers': ransac.inlier_count, 'ratio': ransac.inlier_ratio,
                'geometric_match': ransac.geometric_ok, 'error': ransac.error or orb.error})
            if result.ransac is None or ransac.inlier_count > result.ransac.inlier_count:
                result.orb, result.ransac = orb, ransac
            if ransac.geometric_ok:
                fu = fuse(orb_result=orb, ransac_result=ransac)
                for finding in fu.findings:
                    finding.page = a.page
                    finding.measurements += f' | pages={a.page + 1},{b.page + 1}'
                fu.affected_pages = sorted({a.page, b.page})
                fusions.append(fu)
        if pair_count > config.MAX_CANDIDATE_PAIRS:
            incomplete.append(f'Compared {config.MAX_CANDIDATE_PAIRS} of {pair_count} candidate pairs; remaining pairs not analysed.')
    priority = {Verdict.UNSUPPORTED: 0, Verdict.INCONCLUSIVE: 1,
                Verdict.REVIEW_REQUIRED: 2, Verdict.TAMPERING_DETECTED: 3}
    fused = max(fusions, key=lambda f: priority[f.verdict])
    base = fuse(parsed=parsed, classification=cls, crypto_report=crypto,
                revision_result=result.revision, loc_result=result.localization,
                ela_result=result.ela, orb_result=result.orb, ransac_result=result.ransac)
    base.verdict, base.explanation, base.confidence_label = fused.verdict, fused.explanation, fused.confidence_label
    seen = set()
    findings = []
    for fu in fusions:
        for finding in fu.findings:
            key = (finding.code, finding.page, finding.measurements, finding.description)
            if key not in seen:
                findings.append(finding)
                seen.add(key)
    base.findings = findings
    base.affected_pages = sorted({f.page for f in findings if f.page is not None} |
                                 {p for fu in fusions for p in fu.affected_pages if fu is not None})
    base.limitations = list(dict.fromkeys(base.limitations + incomplete))
    base.completeness += f' | Pages analysed: {parsed.page_count}/{parsed.page_count} | Mode: {analysis_mode}'
    if incomplete:
        base.confidence_label = "Low (partial coverage)"
        base.completeness += ' | PARTIAL: see coverage limitations'
    result.fusion = base
    result.coverage = {'complete': not incomplete, 'mode': analysis_mode,
        'pages_analysed': parsed.page_count, 'page_count': parsed.page_count,
        'candidates_found': candidates_seen, 'candidates_analysed': len(all_candidates),
        'pairs_available': pair_count, 'pairs_analysed': len(result.pair_results),
        'limitations': incomplete}
    result.elapsed_sec = round(time.perf_counter() - start, 3)
    result.stage_times["analysis_total"] = result.elapsed_sec
    return result
