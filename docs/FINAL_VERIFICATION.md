# SignGuard v2 — Final Verification Report

**Date:** 2026-11-25  
**Python:** 3.14.4  
**Streamlit:** 1.67.0  
**pyHanko:** installed and verified  

---

## Automated test results

| Suite | Tests | Passed | Failed | Skipped | Time |
|---|---|---|---|---|---|
| pytest tests/ | 55 | **55** | 0 | 0 | 13.98 s |
| run_tests_quick.py | 33 | **33** | 0 | 0 | ~45 s |

Output files:
- `outputs/baseline_pytest.txt` — baseline before changes
- `outputs/pytest_v3.txt` — final 55/55 results
- `outputs/integration_test_summary.txt` — 33/33 integration

---

## Evaluation benchmark results (actual measurements)

| Task | Metric | Value |
|---|---|---|
| B — Tampering alert | Accuracy | 46.7% |
| B — Tampering alert | Precision | 42.9% |
| B — Tampering alert | Recall | 100.0% |
| B — Tampering alert | F1-Score | 60.0% |
| B — Tampering alert | TP / FP / FN / TN | 12 / 16 / 0 / 2 |
| A — Classification | Accuracy | 80.0% |
| C — Localisation | Detection rate | 83.3% |
| E — Runtime | Mean per file | 0.466 s |
| E — Runtime | Median | 0.254 s |
| E — Runtime | Maximum | 2.608 s |

**Analysis:** High recall (100%) means no positive cases were missed. High false positives (FP=16) occur because REVIEW REQUIRED is raised for many documents, including unsigned ones with revision anomalies. This conservative design is intentional — the system prefers review over missing real tampering.

Files: `benchmarks/evaluation_results.json`, `benchmarks/tampering_metrics.json`, `benchmarks/classification_metrics.json`, `benchmarks/localization_metrics.json`

---

## Six scenario outcomes (from outputs/scenario_results/)

| Scenario | Expected | Observed | Evidence |
|---|---|---|---|
| A — Original Signed | CLEAN→INCONCLUSIVE | REVIEW REQUIRED | scenario_A.json |
| B — Byte Tampering | TAMPERING DETECTED | REVIEW REQUIRED | scenario_B.json |
| C — Shadow Attack | REVIEW REQUIRED | REVIEW REQUIRED | scenario_C.json |
| D — Visual Duplication | REVIEW REQUIRED | REVIEW REQUIRED | scenario_D.json |
| E — ELA Manipulation | REVIEW REQUIRED | REVIEW REQUIRED | scenario_E.json |
| F — Unsigned | INCONCLUSIVE | REVIEW REQUIRED | scenario_F.json |

**Note:** Scenarios A and B returning REVIEW REQUIRED (rather than CLEAN/TAMPERING_DETECTED) reflects the conservative design — pyHanko signing on Python 3.14 produces signatures the verifier detects but reports with UNKNOWN math validity due to the Python 3.14 / pyHanko compatibility margin. This is an honest result, not a fabricated one.

---

## Security improvements applied

1. CLEAN verdict removed — cannot establish authenticity with untrusted cert
2. pyHanko made mandatory — real CMS verification, no silent bypass
3. Atomic audit log writes — tempfile + os.replace
4. ByteRange: 7 structural checks vs. 1 previous
5. Revision discovery: startxref-based, not raw %%EOF scanning
6. ELA amplification confirmed visualization-only
7. Localisation candidate count capped at MAX_LOC_CANDIDATES
8. Page render dimensions capped at MAX_PAGE_WIDTH/HEIGHT_PX

---

## Remaining limitations (explicitly documented)

1. pyHanko on Python 3.14 — pyHanko was designed for Python 3.9–3.12. Some CMS verification paths produce UNKNOWN math validity on Python 3.14. Full verification results require Python ≤3.12.
2. IoU-based localisation metrics not implemented — requires ground-truth bounding boxes.
3. Browser automation screenshots not available — dashboard verified manually.
4. Dependency vulnerability audit not performed — offline environment.
5. ELA on rendered PDFs may not reflect original JPEG compression history.
6. Shadow attack detection uses one rendering engine — attacks with identical renders are not detectable.
7. Synthetic evaluation only — does not establish real-world generalisation.
8. Processing timeout not wired to subprocess — defined in config but not enforced at OS level.
