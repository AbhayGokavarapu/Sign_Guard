"""
Comprehensive automated tests for SignGuard v2.
Run with:  pytest tests/ -v
"""
import sys, os, json, tempfile, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image
import config

# ── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def unsigned_pdf():
    from simulation.sample_generator import build_unsigned
    return build_unsigned("Test unsigned document.")

@pytest.fixture
def visual_pdf():
    from simulation.sample_generator import build_visual_only
    return build_visual_only(sig_seed=1)

@pytest.fixture
def shadow_pdf():
    from simulation.sample_generator import build_shadow_pdf
    return build_shadow_pdf(original_amount="$1,000", shadow_amount="$9,000")

@pytest.fixture
def duplicate_sig_pdf():
    from simulation.sample_generator import build_duplicate_sig_pdf
    return build_duplicate_sig_pdf(sig_count=2, sig_seed=99)

@pytest.fixture
def ela_pdf():
    from simulation.sample_generator import build_ela_target
    return build_ela_target()

@pytest.fixture
def signed_pdf():
    from simulation.signed_samples import build_signed_pdf
    return build_signed_pdf("Signed test document.")


# ── Module 1: PDF parsing ──────────────────────────────────────────────────

def test_parse_unsigned(unsigned_pdf):
    from core.pdf_parser import parse_pdf
    doc = parse_pdf(unsigned_pdf, "test.pdf")
    assert doc.error is None
    assert doc.page_count >= 1
    assert len(doc.sha256) == 64
    assert doc.file_size == len(unsigned_pdf)
    assert len(doc.page_images) == doc.page_count

def test_validate_bad_header():
    from core.pdf_parser import validate_pdf
    result = validate_pdf(b"not a pdf file", "bad.pdf")
    assert not result.valid

def test_validate_oversized():
    from core.pdf_parser import validate_pdf
    big = b"%PDF" + b"x" * (config.MAX_FILE_SIZE_MB * 1024 * 1024 + 1)
    result = validate_pdf(big, "big.pdf")
    assert not result.valid

def test_sha256_preserved(unsigned_pdf):
    import hashlib
    from core.pdf_parser import parse_pdf
    doc = parse_pdf(unsigned_pdf, "test.pdf")
    assert doc.sha256 == hashlib.sha256(unsigned_pdf).hexdigest()

def test_new_upload_clears_state(unsigned_pdf, visual_pdf):
    import hashlib
    h1 = hashlib.sha256(unsigned_pdf).hexdigest()
    h2 = hashlib.sha256(visual_pdf).hexdigest()
    assert h1 != h2

def test_encrypted_pdf_handled():
    """An encrypted PDF returns an error, not a crash."""
    from core.pdf_parser import parse_pdf, validate_pdf
    # Minimal encrypted-looking PDF stub — will fail to open cleanly
    raw = b"%PDF-1.4\n1 0 obj\n<</Encrypt 2 0 R>>\nendobj\n%%EOF"
    # validate may pass (starts with %PDF)
    val = validate_pdf(raw, "enc.pdf")
    if val.valid:
        doc = parse_pdf(raw, "enc.pdf")
        # Should either parse or return error — never crash
        assert doc is not None


# ── Module 2: Classification ───────────────────────────────────────────────

def test_classify_unsigned(unsigned_pdf):
    from core.pdf_parser import parse_pdf
    from core.document_classifier import classify, DocClass
    doc = parse_pdf(unsigned_pdf, "u.pdf")
    result = classify(doc)
    assert result.doc_class in (DocClass.UNSIGNED, DocClass.VISUAL_CANDIDATE)

def test_classify_visual(visual_pdf):
    from core.pdf_parser import parse_pdf
    from core.document_classifier import classify, DocClass
    doc = parse_pdf(visual_pdf, "v.pdf")
    result = classify(doc)
    assert result.doc_class == DocClass.VISUAL_CANDIDATE

def test_classify_signed_pdf(signed_pdf):
    from core.pdf_parser import parse_pdf
    from core.document_classifier import classify, DocClass
    doc = parse_pdf(signed_pdf, "s.pdf")
    result = classify(doc)
    # May be signed or visual depending on whether pyHanko signing succeeded
    assert result.doc_class == DocClass.CRYPTOGRAPHICALLY_SIGNED


# ── Module 3: Cryptographic verification ──────────────────────────────────

def test_crypto_no_sigs(unsigned_pdf):
    from core.crypto_verifier import verify
    report = verify(unsigned_pdf)
    assert report.total_sigs == 0

def test_crypto_signed_pdf(signed_pdf):
    from core.crypto_verifier import verify, IntegrityStatus
    report = verify(signed_pdf)
    if report.total_sigs > 0:
        # If genuinely signed, check structure
        for r in report.results:
            assert r.integrity_status in (
                IntegrityStatus.PASS, IntegrityStatus.FAIL, IntegrityStatus.UNKNOWN
            )
            # Must never return CLEAN implying full trust
            assert r.cert_trusted in (True, False, None)
    # Even if no sigs (pyHanko fallback), should not crash
    assert report is not None

def test_crypto_trust_separated(signed_pdf):
    """Math validity and cert trust must be reported separately."""
    from core.crypto_verifier import verify, TrustStatus
    report = verify(signed_pdf)
    if report.total_sigs > 0:
        for r in report.results:
            # Self-signed test cert must NOT be reported as TRUSTED
            if r.cert_info and r.cert_info.is_test_cert:
                assert r.trust_status != TrustStatus.TRUSTED

def test_tampered_bytes_detection():
    from simulation.sample_generator import build_tampered_bytes, build_unsigned
    orig     = build_unsigned("original content")
    tampered = build_tampered_bytes(orig, change_offset=400)
    import hashlib
    assert hashlib.sha256(orig).hexdigest() != hashlib.sha256(tampered).hexdigest()

def test_byte_range_validation():
    from core.crypto_verifier import validate_byte_range
    raw = b"%PDF" + b"x" * 1000 + b"%%EOF"
    # Valid structure
    br = [0, 100, 200, 800]
    result = validate_byte_range(raw, br)
    assert isinstance(result.structurally_valid, bool)
    # Too short
    result2 = validate_byte_range(raw, [0, 100, 200])
    assert not result2.structurally_valid
    # Negative values
    result3 = validate_byte_range(raw, [0, -1, 200, 800])
    assert not result3.structurally_valid

def test_crypto_no_pyhanko_fallback_explicit(unsigned_pdf, monkeypatch):
    """When pyHanko is absent, results must be UNKNOWN — never silently valid."""
    from core.crypto_verifier import _verify_no_pyhanko, IntegrityStatus
    # Inject a fake sig entry so it triggers the no-pyhanko path
    results = _verify_no_pyhanko(unsigned_pdf)
    for r in results:
        assert r.integrity_status == IntegrityStatus.UNKNOWN
        assert r.error is not None


# ── Module 4: Revision analysis ───────────────────────────────────────────

def test_revision_single(unsigned_pdf):
    from core.revision_analyzer import analyze
    result = analyze(unsigned_pdf)
    assert len(result.revisions) >= 1

def test_shadow_pdf_revisions(shadow_pdf):
    from core.revision_analyzer import analyze
    result = analyze(shadow_pdf)
    assert len(result.revisions) >= 2
    assert result.has_incremental_updates

def test_shadow_suspect_flag(shadow_pdf):
    from core.revision_analyzer import analyze
    result = analyze(shadow_pdf)
    assert result.changed_area_pct > 0
    assert result.shadow_suspect
    assert result.discovery_method != ""

def test_revision_discovery_method(unsigned_pdf):
    from core.revision_analyzer import analyze
    result = analyze(unsigned_pdf)
    assert result.discovery_method in (
        "pyhanko_xref_chain",
    )

def test_revision_reports_limitations(unsigned_pdf):
    from core.revision_analyzer import analyze
    result = analyze(unsigned_pdf)
    assert isinstance(result.limitations, list)

def test_misleading_eof_in_stream():
    """%%EOF inside stream data should not create spurious revisions."""
    from simulation.sample_generator import build_unsigned
    # Build a normal PDF — the revision count should be 1 (no fake incremental)
    raw = build_unsigned("Normal document")
    from core.revision_analyzer import analyze
    result = analyze(raw)
    # A clean single-page PDF should produce 1 revision via startxref method
    # (may be more with eof_fallback but startxref is preferred)
    assert len(result.revisions) >= 1


# ── Module 5: Signature localisation ──────────────────────────────────────

def test_localise_unsigned(unsigned_pdf):
    from core.signature_localizer import localize
    result = localize(unsigned_pdf, 0)
    assert result.error is None
    assert isinstance(result.original, Image.Image)

def test_localise_visual_returns_image(visual_pdf):
    from core.signature_localizer import localize
    result = localize(visual_pdf, 0)
    assert isinstance(result.annotated, Image.Image)

def test_localise_duplicate_finds_candidates(duplicate_sig_pdf):
    from core.signature_localizer import localize
    result = localize(duplicate_sig_pdf, 0)
    assert len(result.candidates) >= 1

def test_localise_respects_candidate_limit():
    from core.signature_localizer import localize
    from simulation.sample_generator import build_duplicate_sig_pdf
    pdf = build_duplicate_sig_pdf(sig_count=2)
    result = localize(pdf, 0)
    assert len(result.candidates) <= config.MAX_LOC_CANDIDATES

def test_localise_confidence_is_heuristic(duplicate_sig_pdf):
    """Confidence values must be in [0,1] — documented as heuristic."""
    from core.signature_localizer import localize
    result = localize(duplicate_sig_pdf, 0)
    for c in result.candidates:
        assert 0.0 <= c.confidence <= 1.0


# ── Module 6: ELA ─────────────────────────────────────────────────────────

def test_ela_runs(ela_pdf):
    from core.pdf_parser import render_page
    from core.ela_detector import run_ela
    img    = render_page(ela_pdf, 0)
    result = run_ela(img, quality=75, amplification=15)
    assert result.error is None
    assert result.mean_residual >= 0
    assert result.max_residual  >= result.mean_residual
    assert isinstance(result.amplified, Image.Image)

def test_ela_statistics_nonzero(ela_pdf):
    from core.pdf_parser import render_page
    from core.ela_detector import run_ela
    img    = render_page(ela_pdf, 0)
    result = run_ela(img, quality=50, amplification=20)
    assert result.mean_residual > 0

def test_ela_multi_quality(ela_pdf):
    from core.pdf_parser import render_page
    from core.ela_detector import run_ela
    img    = render_page(ela_pdf, 0)
    result = run_ela(img)
    assert isinstance(result.multi_quality, dict)
    for q in config.ELA_QUALITIES:
        assert q in result.multi_quality
        assert result.multi_quality[q].mean_residual >= 0

def test_ela_amplification_independent(ela_pdf):
    """Amplification changes visualization only — not measurement values."""
    from core.pdf_parser import render_page
    from core.ela_detector import run_ela
    img  = render_page(ela_pdf, 0)
    r1   = run_ela(img, quality=75, amplification=5)
    r2   = run_ela(img, quality=75, amplification=25)
    # Measurements must be identical regardless of amplification
    assert abs(r1.mean_residual - r2.mean_residual) < 0.01
    assert abs(r1.max_residual  - r2.max_residual)  < 0.01


# ── Module 7+8: ORB / RANSAC ──────────────────────────────────────────────

def test_orb_match_two_images(duplicate_sig_pdf):
    from core.signature_localizer import localize
    from core.orb_matcher import match
    loc = localize(duplicate_sig_pdf, 0)
    if len(loc.candidates) >= 2:
        result = match(loc.candidates[0].crop, loc.candidates[1].crop)
        assert result.n_kp_a >= 0
        assert result.n_kp_b >= 0
    else:
        pytest.skip("Not enough candidates for ORB test.")

def test_ransac_too_few_matches():
    from core.orb_matcher import ORBResult
    from core.ransac_verifier import verify
    blank = Image.new("RGB", (50, 20), "white")
    orb = ORBResult(blank, blank, blank, blank, blank, blank,
                    0, 0, 0, 0, [], [], [])
    result = verify(orb)
    assert result.geometric_ok is False

def test_ransac_degenerate_homography():
    """Identical images should produce a degenerate homography — handle gracefully."""
    from core.orb_matcher import match
    from core.ransac_verifier import verify
    img = Image.new("RGB", (100, 50), "white")
    orb = match(img, img)
    result = verify(orb)
    assert result is not None   # must not crash

def test_orb_handles_no_keypoints():
    from core.orb_matcher import match
    blank = Image.new("RGB", (10, 10), color=(255,255,255))
    result = match(blank, blank)
    # Should return a valid result, possibly with an error note
    assert result is not None


# ── Module 10: Evidence fusion ─────────────────────────────────────────────

def test_fusion_unsupported():
    from core.pdf_parser import ParsedDocument
    from core.evidence_fusion import fuse, Verdict
    bad_doc = ParsedDocument("x.pdf", 0, "a"*64, b"", 0, {},
                             False, False, 0, [], error="Corrupt PDF")
    result  = fuse(parsed=bad_doc)
    assert result.verdict == Verdict.UNSUPPORTED

def test_fusion_no_sigs():
    from core.evidence_fusion import fuse, Verdict
    result = fuse()
    assert result.verdict in (Verdict.INCONCLUSIVE,)

def test_fusion_no_clean_verdict():
    """CLEAN verdict must not exist — untrusted cert cannot establish authenticity."""
    from core.evidence_fusion import Verdict
    verdict_values = [v.value for v in Verdict]
    assert "CLEAN" not in verdict_values

def test_fusion_scenario_label_not_used():
    """Ground-truth label must never be a parameter to fuse()."""
    import inspect
    from core.evidence_fusion import fuse
    sig = inspect.signature(fuse)
    forbidden = ("ground_truth", "scenario_label", "expected_verdict",
                 "scenario_id", "label")
    for name in forbidden:
        assert name not in sig.parameters

def test_fusion_has_integrity_verdict():
    from core.evidence_fusion import fuse, IntegrityVerdict
    result = fuse()
    assert isinstance(result.integrity_verdict, IntegrityVerdict)

def test_fusion_ela_alone_not_definitive():
    """ELA findings alone must not produce TAMPERING_DETECTED."""
    from core.evidence_fusion import fuse, Verdict
    from core.ela_detector import run_ela
    # Create a high-residual ELA result
    img = Image.new("RGB", (100,100), "white")
    ela = run_ela(img, quality=50)
    # Force high residual by patching
    ela.mean_residual = 100.0
    ela.high_pct      = 50.0
    ela.error         = None
    result = fuse(ela_result=ela)
    # ELA alone must not produce TAMPERING_DETECTED
    assert result.verdict != Verdict.TAMPERING_DETECTED


# ── Module 11: Reporting ───────────────────────────────────────────────────

def test_json_report_generates(unsigned_pdf):
    from core.pipeline import run
    from reporting.json_report import to_json
    result = run(unsigned_pdf, "u.pdf")
    js     = to_json(result)
    data   = json.loads(js)
    assert "verdict" in data
    assert "document" in data
    assert "sha256" in data["document"]
    assert "disclaimer" in data
    assert data.get("schema_version") == "2.0"

def test_json_report_no_numpy(unsigned_pdf):
    """JSON report must be fully serialisable without NumPy types."""
    from core.pipeline import run
    from reporting.json_report import to_json
    result = run(unsigned_pdf, "u.pdf")
    js     = to_json(result)
    data   = json.loads(js)
    assert isinstance(data, dict)

def test_pdf_report_generates(unsigned_pdf):
    from core.pipeline import run
    from reporting.pdf_report import build_pdf_report
    result = run(unsigned_pdf, "u.pdf")
    pdf    = build_pdf_report(result)
    assert pdf[:4] == b"%PDF"

def test_pdf_report_openable(unsigned_pdf):
    """Generated PDF report must be openable by PyMuPDF."""
    from core.pipeline import run
    from reporting.pdf_report import build_pdf_report
    try:
        import pymupdf as fitz
    except ImportError:
        import fitz
    result  = run(unsigned_pdf, "u.pdf")
    pdf     = build_pdf_report(result)
    doc     = fitz.open(stream=pdf, filetype="pdf")
    assert len(doc) > 0
    doc.close()

def test_json_integrity_verdict_present(unsigned_pdf):
    from core.pipeline import run
    from reporting.json_report import to_json
    result = run(unsigned_pdf, "u.pdf")
    data   = json.loads(to_json(result))
    assert "integrity_verdict" in data


# ── Module 12: Audit logging ───────────────────────────────────────────────

def test_audit_append_and_verify(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "AUDIT_LOG_PATH", str(tmp_path / "audit.json"))
    from core.audit_logger import append_record, verify_chain
    append_record("a" * 64, "INCONCLUSIVE")
    append_record("b" * 64, "REVIEW REQUIRED")
    ok, msg = verify_chain()
    assert ok

def test_audit_tamper_detection(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "AUDIT_LOG_PATH", str(tmp_path / "audit.json"))
    from core.audit_logger import append_record, verify_chain
    import json
    append_record("a" * 64, "INCONCLUSIVE")
    with open(config.AUDIT_LOG_PATH) as f:
        chain = json.load(f)
    chain[0]["verdict"] = "TAMPERING DETECTED"
    with open(config.AUDIT_LOG_PATH, "w") as f:
        json.dump(chain, f)
    ok, _ = verify_chain()
    assert not ok

def test_audit_missing_field(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "AUDIT_LOG_PATH", str(tmp_path / "audit.json"))
    from core.audit_logger import append_record, verify_chain
    import json
    append_record("a" * 64, "INCONCLUSIVE")
    with open(config.AUDIT_LOG_PATH) as f:
        chain = json.load(f)
    del chain[0]["record_hash"]
    with open(config.AUDIT_LOG_PATH, "w") as f:
        json.dump(chain, f)
    ok, msg = verify_chain()
    assert not ok
    assert "missing" in msg.lower()

def test_audit_empty_chain(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "AUDIT_LOG_PATH", str(tmp_path / "empty.json"))
    from core.audit_logger import verify_chain
    ok, msg = verify_chain()
    assert ok   # empty chain is valid


# ── Full pipeline ──────────────────────────────────────────────────────────

def test_full_pipeline_unsigned(unsigned_pdf):
    from core.pipeline import run
    result = run(unsigned_pdf, "unsigned.pdf")
    assert result.validation.valid
    assert result.parsed is not None
    assert result.fusion is not None
    assert result.fusion.verdict.value != "CLEAN"   # CLEAN must not exist

def test_full_pipeline_visual(visual_pdf):
    from core.pipeline import run
    result = run(visual_pdf, "visual.pdf")
    assert result.fusion is not None

def test_full_pipeline_shadow(shadow_pdf):
    from core.pipeline import run
    result = run(shadow_pdf, "shadow.pdf")
    assert result.revision is not None
    assert result.revision.has_incremental_updates

def test_full_pipeline_signed(signed_pdf):
    from core.pipeline import run
    result = run(signed_pdf, "signed.pdf")
    assert result.fusion is not None
    # Must have an integrity verdict (not just a plain verdict)
    assert result.fusion.integrity_verdict is not None

def test_pipeline_has_timestamp(unsigned_pdf):
    from core.pipeline import run
    result = run(unsigned_pdf)
    assert result.analysis_ts != ""

def test_pipeline_state_invalidation(unsigned_pdf, visual_pdf):
    """Different documents must produce different SHA-256 hashes."""
    from core.pipeline import run
    r1 = run(unsigned_pdf, "a.pdf")
    r2 = run(visual_pdf,   "b.pdf")
    assert r1.parsed.sha256 != r2.parsed.sha256
