# SignGuard v3.2

An explainable PDF signature and forensic analysis research project for Information Security.

SignGuard checks signed-byte integrity, public-key signature validity, certificate trust, post-signing revisions and possible visual duplication. It produces traceable findings and JSON/PDF reports. It uses no trained model, GPU, API key or certificate network fetching.

## Run

Validated with Python 3.12. Create and activate a virtual environment, then:

```bash
python -m pip install -r requirements-lock.txt
python -m streamlit run app.py
```

The launchers bind to http://localhost:8502. A bare Streamlit command uses its default port, usually 8501. Windows: `launch.bat`; Linux/macOS: `sh launch.sh`. The launcher never terminates unrelated processes. A port already in use must be resolved by the operator.

## Implemented security controls

- Genuine pyHanko CMS signatures and attack fixtures. Signing failures stop generation.
- Separate integrity, mathematical validity, certificate trust, modification-policy and identity fields.
- Explicit offline trust roots. Optional `SIGNGUARD_TRUST_ROOTS=/path/to/roots.pem`; no implicit OS roots or automatically trusted demo certificate.
- Revision reconstruction from the parsed /Prev xref chain, signed-revision render/text comparisons across every current page.
- Classical localisation, raw multi-quality ELA at Q65/75/85/95, ORB reciprocal matching and RANSAC.
- Cross-page candidate comparisons, with candidate/pair limits and omitted work reported explicitly.
- Disposable worker with enforced timeout, Linux address-space/CPU limits, and dimension/aggregate pixel checks before rendering.
- Locked, fsynced, atomic hash-chain appends; corrupt logs fail visibly. Export a checkpoint and store it independently.
- Reports with coverage, per-page candidate boxes, pair evidence, unsupported/incomplete status, and audit-write failures.

The dashboard now has exactly four pages, in this order:

1. **Document analysis** — the opening page; upload a PDF, inspect findings and download PDF/JSON reports.
2. **Document comparison** — compare an original with a suspect and export comparison evidence.
3. **Attack lab** — generate and analyse controlled scenarios; download scenario reports.
4. **Evidence viewer** — inspect uploaded-document or lab images, measurements and coverage.

Overview, Evaluation, Reports & audit, Case review and Presentation have been removed from the dashboard. Saved benchmarks and research scripts remain in the repository for the PPT/evaluation discussion. Report generation and detection algorithms are unchanged. Clear session returns to Document analysis; old sessions pointing to removed pages are reset safely.

## Verdicts

| Verdict | Meaning |
|---|---|
| TAMPERING DETECTED | Signed-byte integrity or public-key signature verification failed; inspect the finding |
| REVIEW REQUIRED | Revision/policy or supporting visual evidence needs expert review |
| INCONCLUSIVE | No decisive finding; does not establish authenticity |
| UNSUPPORTED | Rejected, failed or resource-limited processing; no assurance |

Integrity is reported separately. An intact signature protects its signed byte ranges, not all later revisions or the truth of the document. There is no CLEAN verdict.

## Demonstrations

| Scenario | Actual fixture | Expected evidence |
|---|---|---|
| A | Genuinely signed unmodified control | Integrity PASS, math valid, self-signed untrusted; INCONCLUSIVE |
| B | Metadata changed within signed bytes, same page rendering | CRYPTO-001; TAMPERING DETECTED |
| C | Valid incremental content replacement after signing | Integrity PASS, revision/content findings; REVIEW REQUIRED |
| D | Repeated raster handwriting | ORB-001 geometric evidence; REVIEW REQUIRED |
| E | Unmodified gradient control | ELA residual visualisation; INCONCLUSIVE, no claim of forgery |
| F | Unsigned document | Integrity not applicable; INCONCLUSIVE |

Scenario C demonstrates post-signing replacement. It is not a comprehensive implementation of pre-planned shadow exploits. Additional tests cover benign second signatures, annotations, trusted/unknown/expired test certificates, invalid public-key signatures, last-page changes and cross-page duplication.

## Validation

```bash
python -m pytest tests/ -q
python run_tests_quick.py
python benchmarks/run_evaluation.py
```

The current full regression suite passed **142 tests**, covering the four-page workflow, legacy navigation resets, scenario outputs and report exports. The earlier nine-page version passed 143 tests; see the latest verification record for the current run. The quick script passed 29 security tests and six scenario checks (35 total). It asserts security outcomes and regenerates scenario JSON/PDF/PNG evidence. The benchmark generates 52 synthetic controls: 13 development and 39 held-out, across 13 categories. It compares three modes, separates byte failures from review alerts, reports per-category outcomes and measures annotated localisation at IoU >= 0.5. See `docs/FINAL_VERIFICATION.md` for the latest executed checks.

### Measured held-out results

| Mode | Precision | Recall | Accuracy |
|---|---|---|---|
| Crypto only | 100.0% | 25.0% | 76.9% |
| Crypto + revision | 66.7% | 50.0% | 76.9% |
| Full pipeline | 50.0% | 75.0% | 69.2% |

Full pipeline: TP=9, FP=9, FN=3, TN=18, F1=60.0%. The three missed positive controls are pasted image edits. Benign annotations, repeated logos and raster text scans account for false review alerts. Combining methods adds detections and false positives; it does not uniformly improve accuracy.

Annotated localisation matched 12 of 12 signature boxes on nine held-out signature documents at IoU >= 0.5, with zero extra candidates on those annotated pages. This narrow synthetic result excludes non-signature-page localisation false positives and must not be presented as real-world accuracy.

## Structure

`core/`: bounded parsing, verification, revision analysis, CV, fusion, worker and audit.
`simulation/`: genuine signed controls, attack scenarios and annotated evaluation generation.
`dashboard/`: four Streamlit pages and shared UI/navigation helpers.
`reporting/`: JSON and ReportLab exports.
`tests/`: regression and security outcome assertions.
`benchmarks/`: executable benchmark and measured outputs.
`docs/`: threat model, implementation, research comparison, demo and verification.

## Limits

This is an educational research prototype. Offline CRL/OCSP evidence and RFC3161 timestamps can be validated against explicit operator-provided roots. Missing, stale or untrusted evidence remains unchecked/unknown; online certificate fetching is disabled. A signer-reported date is not a trusted timestamp. The test certificate never establishes a real person's identity.

The optional second-renderer comparison does not detect all PDF parser differentials or shadow attacks. ELA cannot reliably establish PDF manipulation. Repeated legitimate graphics can trigger duplication alerts. Localisation is heuristic. Candidate/pair budgets can leave analysis partial; check coverage. OS memory enforcement is Linux-specific; Windows retains timeout and rendering budgets.

The worker provides resource isolation, not a complete exploit sandbox. Real-document generalisation, an independent attack corpus and comprehensive OS/native dependency vulnerability coverage remain unverified. The held-out set shares a synthetic generator with development controls. Do not use these results as an authenticity certificate or a production security guarantee.

See `docs/THREAT_MODEL.md` and `docs/RESEARCH_COMPARISON.md` for assumptions and evaluation boundaries.

## Publish on Streamlit Community Cloud

Use repository `AbhayGokavarapu/Sign_Guard`, branch `streamlit-deploy`, entry point `streamlit_app.py`, and Python **3.12** in Advanced settings. See `docs/DEPLOYMENT.md`. The public entry point disables shared audit persistence/history and benchmark regeneration.

## Ready-to-upload sample documents

Open Document analysis → Need a document? Download a verified sample. Download one PDF or the complete seven-file ZIP, then upload a numbered PDF through the input above. The kit is also in `samples/signguard-upload-kit.zip`. `START_HERE.txt` explains each case, and `verified_results.csv`/JSON records observed outcomes. Detailed local engine reports are in the kit's `verification/` folder.

Regenerate and verify with `python -m simulation.build_upload_kit`. The generator asserts expected verdicts and key findings and checks that the original/tampered pair renders identically.

## Investigation workspace (3.2)

The focused workspace includes **Document analysis**, **Document comparison**, **Attack lab** and **Evidence viewer**. Inspect consecutive revisions and static PDF actions, optionally compare MuPDF/Poppler rendering, and download PDF/JSON reports from analysis/lab results. Document comparison retains its comparison evidence ZIP export. Clear session removes session inputs/results; a bounded queue protects host capacity.

Dedicated human case review, shared audit viewing and the guided presentation are no longer exposed as pages. Backend report/verification utilities and historical evaluation outputs remain available to scripts.
Operators can provision offline CRL/OCSP evidence, trusted TSA roots and an optional evidence-package signing key. No PDF-selected certificate URL is fetched. See `docs/INVESTIGATION_UPGRADE.md` for configuration, verifier commands and limits.

External upstream fixtures, cross-validator outcomes, a CycloneDX dependency inventory and a known-vulnerability audit are included in `datasets/external-pyhanko/` and `benchmarks/`. These do not replace independent human adjudication or a real-world forged-document corpus.
