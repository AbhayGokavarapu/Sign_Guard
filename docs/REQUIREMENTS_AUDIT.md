# SignGuard v2 — Requirements Audit

Generated: 2026-11-25 | Based on actual source inspection and test execution.

| # | Requirement | Status | Source File(s) | Test(s) | Evidence / Notes |
|---|---|---|---|---|---|
| 1 | PDF upload and validation | VERIFIED | core/pdf_parser.py::validate_pdf | test_validate_bad_header, test_validate_oversized | 55/55 tests pass |
| 2 | SHA-256 file hashing | VERIFIED | core/pdf_parser.py::parse_pdf | test_sha256_preserved | Hash preserved across runs |
| 3 | Page count limit | VERIFIED | config.py MAX_PAGE_COUNT | test_validate_oversized | Enforced in validate_pdf |
| 4 | File size limit | VERIFIED | config.py MAX_FILE_SIZE_MB | test_validate_oversized | Enforced in validate_pdf |
| 5 | PDF page rendering | VERIFIED | core/pdf_parser.py::render_page | test_parse_unsigned | 144 DPI render |
| 6 | Metadata extraction | VERIFIED | core/pdf_parser.py::parse_pdf | test_parse_unsigned | title, author, dates |
| 7 | Encrypted PDF handling | VERIFIED | core/pdf_parser.py | test_encrypted_pdf_handled | Returns error, no crash |
| 8 | Signature field detection | VERIFIED | core/document_classifier.py | test_classify_signed_pdf | Via PyMuPDF widgets |
| 9 | Document classification | VERIFIED | core/document_classifier.py | test_classify_unsigned/visual/signed | 4 classes |
| 10 | Mandatory pyHanko | VERIFIED | core/crypto_verifier.py, requirements.txt | test_crypto_signed_pdf | pyHanko in requirements.txt |
| 11 | CMS/SignedData parsing | VERIFIED | core/crypto_verifier.py::_verify_with_pyhanko | test_crypto_signed_pdf | Via pyHanko validate_pdf_signature |
| 12 | Signed-byte integrity | VERIFIED | core/crypto_verifier.py IntegrityStatus | test_crypto_signed_pdf, test_tampered_bytes_detection | PASS/FAIL/UNKNOWN |
| 13 | Mathematical signature validity | VERIFIED | core/crypto_verifier.py SigVerificationResult.math_valid | test_crypto_signed_pdf | Separate from integrity |
| 14 | Certificate trust | VERIFIED | core/crypto_verifier.py TrustStatus | test_crypto_trust_separated | TRUSTED/SELF-SIGNED/UNKNOWN |
| 15 | Modification policy check | VERIFIED | core/crypto_verifier.py ModpolicyStatus | test_crypto_signed_pdf | DocMDP via pyHanko |
| 16 | Signer identity status | VERIFIED | core/crypto_verifier.py IdentityStatus | test_crypto_trust_separated | ESTABLISHED/UNVERIFIED/NOT ESTABLISHED |
| 17 | No-pyHanko fallback explicit | VERIFIED | core/crypto_verifier.py::_verify_no_pyhanko | test_crypto_no_pyhanko_fallback_explicit | Returns UNKNOWN, never silently valid |
| 18 | ByteRange structural validation | VERIFIED | core/crypto_verifier.py::validate_byte_range | test_byte_range_validation | 7 structural checks |
| 19 | ByteRange covers full file | VERIFIED | core/crypto_verifier.py ByteRangeInfo.covers_full_file | test_byte_range_validation | Separate flag |
| 20 | Signed revision coverage | VERIFIED | core/crypto_verifier.py ByteRangeInfo.covers_signed_rev | test_byte_range_validation | Separate flag |
| 21 | PDF revision discovery (reliable) | VERIFIED | core/revision_analyzer.py::_discover_revisions_pymupdf | test_revision_discovery_method | startxref-based, not raw %%EOF |
| 22 | %%EOF fallback documented | VERIFIED | core/revision_analyzer.py::_discover_revisions_fallback | test_revision_reports_limitations | Limitations list populated |
| 23 | Incremental update detection | VERIFIED | core/revision_analyzer.py | test_shadow_pdf_revisions | has_incremental_updates flag |
| 24 | Signed vs current visual diff | VERIFIED | core/revision_analyzer.py::_pixel_diff | test_shadow_suspect_flag | NumPy pixel diff + scipy blobs |
| 25 | Text diff between revisions | VERIFIED | core/revision_analyzer.py::_extract_text_first_page | test_shadow_suspect_flag | text_diff_summary field |
| 26 | Metadata diff between revisions | VERIFIED | core/revision_analyzer.py::_metadata | test_shadow_suspect_flag | metadata_changed field |
| 27 | Shadow suspect flag | VERIFIED | core/revision_analyzer.py | test_shadow_suspect_flag | SHADOW_CHANGE_PCT_MIN threshold |
| 28 | Shadow limitations documented | VERIFIED | core/revision_analyzer.py | test_revision_reports_limitations | limitations list |
| 29 | Signature localisation | VERIFIED | core/signature_localizer.py | test_localise_* | 7-stage CV pipeline |
| 30 | Candidate count limit | VERIFIED | core/signature_localizer.py + config.py | test_localise_respects_candidate_limit | MAX_LOC_CANDIDATES enforced |
| 31 | Confidence as heuristic | VERIFIED | core/signature_localizer.py + dashboard | test_localise_confidence_is_heuristic | Labelled "heuristic score" |
| 32 | Multi-quality ELA | VERIFIED | core/ela_detector.py::run_ela | test_ela_multi_quality | Q65/75/85/95 sweep |
| 33 | Amplification visualization-only | VERIFIED | core/ela_detector.py | test_ela_amplification_independent | Mean residual unchanged by amp |
| 34 | ELA sweep summary | VERIFIED | core/ela_detector.py ELAResult.sweep_summary | test_ela_multi_quality | String with per-Q stats |
| 35 | ORB keypoints | VERIFIED | core/orb_matcher.py | test_orb_match_two_images | cv2.ORB_create(500) |
| 36 | Hamming BF + ratio filter | VERIFIED | core/orb_matcher.py | test_orb_match_two_images | Lowe ratio 0.75 |
| 37 | ORB insufficient keypoints | VERIFIED | core/orb_matcher.py | test_orb_handles_no_keypoints | Returns error, no crash |
| 38 | RANSAC homography | VERIFIED | core/ransac_verifier.py | test_ransac_too_few_matches | cv2.findHomography RANSAC |
| 39 | RANSAC degenerate handling | VERIFIED | core/ransac_verifier.py | test_ransac_degenerate_homography | No crash |
| 40 | RANSAC insufficient features | VERIFIED | core/ransac_verifier.py | test_ransac_too_few_matches | Returns geometric_ok=False |
| 41 | No CLEAN verdict | VERIFIED | core/evidence_fusion.py | test_fusion_no_clean_verdict | CLEAN removed from Verdict enum |
| 42 | Integrity verdict separate | VERIFIED | core/evidence_fusion.py FusionResult.integrity_verdict | test_fusion_has_integrity_verdict | 4 IntegrityVerdict values |
| 43 | ELA alone not definitive | VERIFIED | core/evidence_fusion.py | test_fusion_ela_alone_not_definitive | REVIEW REQUIRED max, not TAMPERING |
| 44 | Scenario label not in fuse() | VERIFIED | core/evidence_fusion.py | test_fusion_scenario_label_not_used | Inspected signature |
| 45 | JSON report schema v2.0 | VERIFIED | reporting/json_report.py | test_json_report_generates | schema_version=2.0 |
| 46 | JSON has disclaimer | VERIFIED | reporting/json_report.py | test_json_report_generates | disclaimer field |
| 47 | JSON integrity_verdict | VERIFIED | reporting/json_report.py | test_json_integrity_verdict_present | Top-level field |
| 48 | JSON no NumPy types | VERIFIED | reporting/json_report.py::_safe | test_json_report_no_numpy | _safe() handles np.integer/float |
| 49 | PDF report openable | VERIFIED | reporting/pdf_report.py | test_pdf_report_openable | PyMuPDF opens generated PDF |
| 50 | Hash-chained audit log | VERIFIED | core/audit_logger.py | test_audit_append_and_verify | SHA-256 chain |
| 51 | Audit tamper detection | VERIFIED | core/audit_logger.py::verify_chain | test_audit_tamper_detection | Broken chain detected |
| 52 | Audit missing field | VERIFIED | core/audit_logger.py::verify_chain | test_audit_missing_field | Explicit error |
| 53 | Atomic audit writes | VERIFIED | core/audit_logger.py::_save_chain | Manual inspection | tempfile + os.replace |
| 54 | 6 attack scenarios | VERIFIED | simulation/controlled_scenarios.py | integration test | A/B/C/D/E/F all generate+run |
| 55 | Scenario evidence saved | VERIFIED | run_tests_quick.py | integration test | outputs/scenario_results/ |
| 56 | Genuine pyHanko signing | VERIFIED | simulation/signed_samples.py | test_crypto_signed_pdf | Real CMS signature |
| 57 | Evaluation dataset generated | VERIFIED | simulation/fixture_manager.py | benchmarks/run_evaluation.py | 30 labeled fixtures |
| 58 | Evaluation metrics computed | VERIFIED | benchmarks/run_evaluation.py | evaluation_run.txt | B:F1=60% A:Acc=80% C:rate=83% |
| 59 | Config security limits | VERIFIED | config.py | Multiple tests | SIZE/PAGE/RENDER/REV/SIG limits |
| 60 | Streamlit localhost binding | VERIFIED | .streamlit/config.toml | Manual | address=localhost |
| 61 | Port 8502 fixed | VERIFIED | .streamlit/config.toml | Manual | port=8502 |

## Items with known limitations (PARTIALLY IMPLEMENTED)

| # | Requirement | Status | Limitation |
|---|---|---|---|
| L1 | IoU-based localisation metrics | PARTIALLY IMPLEMENTED | Requires ground-truth bounding boxes; detection rate proxy used |
| L2 | Per-class P/R/F1 for classification | PARTIALLY IMPLEMENTED | Requires more samples per class; accuracy reported |
| L3 | Browser automation screenshots | NOT IMPLEMENTED | No browser automation available; dashboard verified manually |
| L4 | Processing timeout enforcement | IMPLEMENTED BUT UNVERIFIED | config.PROCESSING_TIMEOUT_S defined; not wired to subprocess |
| L5 | PDF page dimension limits | IMPLEMENTED BUT UNVERIFIED | MAX_PAGE_WIDTH/HEIGHT_PX in config; applied in render_at_dpi |
| L6 | Dependency vulnerability audit | NOT IMPLEMENTED | Offline environment; pip-audit not available |

## Corrected misleading claims

| Claim | Old status | Corrected to |
|---|---|---|
| pyHanko is optional | Was fallback | Now mandatory in requirements.txt |
| CLEAN verdict | Was in Verdict enum | Removed — untrusted cert cannot establish authenticity |
| Raw %%EOF scanning | Primary method | Replaced with startxref-based discovery |
| ELA proves forgery | Stated in finding | Corrected to "supporting indicator only" |
| Amplification affects measurements | Ambiguous | Explicitly: amplification is visualization-only |
| Full-file coverage proves valid signature | Implied | ByteRange has 7 structural checks now |
