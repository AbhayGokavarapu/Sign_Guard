# SignGuard v3 executed verification

Executed on 2026-11-25 with Python 3.12.14 on Linux and the dependency versions in `requirements-lock.txt`.

## Test results

- Full suite: **84 passed**, 0 failed, 61.90 seconds.
- Quick validation: **29 security tests passed**, followed by **six scenario outcome/report checks passed** (35 checks total).
- Final signature-limit regression rerun: one passed; truncated signature verification cannot report all signatures valid.
- Streamlit AppTest: all seven pages rendered without application exceptions.
- Attack Lab UI: generated and analysed all six scenarios through button interactions; all expected verdicts rendered without application exceptions.
- Every Python source file parses; `git diff --check` passes.
- Dependency compatibility check: all 69 installed packages compatible. This is not a vulnerability audit.

Saved execution evidence: `outputs/security_verification.txt`, `outputs/integration_test_summary.json`, regenerated `outputs/scenario_results/`, and measured `benchmarks/` outputs. Earlier `outputs/test*`/`pytest*` files are historical and superseded by this report.

## Demonstration results

| Scenario | Observed verdict | Key findings |
|---|---|---|
| A genuine signed baseline | INCONCLUSIVE | No suspicious findings; integrity PASS, math valid, self-signed untrusted |
| B signed metadata tampering | TAMPERING DETECTED | CRYPTO-001 |
| C valid incremental content replacement | REVIEW REQUIRED | CRYPTO-003, CRYPTO-004, SHADOW-001, SHADOW-002 |
| D raster signature duplication | REVIEW REQUIRED | ORB-001 |
| E gradient residual control | INCONCLUSIVE | No suspicious findings |
| F unsigned control | INCONCLUSIVE | Integrity not applicable |

Tests additionally confirm invalid public-key signatures, last-page changes, cross-page duplication, benign second signatures, annotation integrity, explicit-root trust/unknown issuers/expiry, malformed/password-encrypted/huge PDFs, timeout and memory failures, candidate/signature limits, corrupt logs, concurrent thread/process appends, checkpoint truncation detection and visible audit-write failures.

## Held-out evaluation

52 generated synthetic files: 13 development and 39 held-out. Fixed thresholds. Held-out generation shares code with development, so it is not an independent external corpus.

| Mode | TP | FP | FN | TN | Precision | Recall | Accuracy |
|---|---|---|---|---|---|---|---|
| Crypto only | 3 | 0 | 9 | 27 | 100.0% | 25.0% | 76.9% |
| Crypto + revision | 6 | 3 | 6 | 24 | 66.7% | 50.0% | 76.9% |
| Full | 9 | 9 | 3 | 18 | 50.0% | 75.0% | 69.2% |

No unsupported files in this evaluation. Full F1=60.0%. Three confirmed signed-byte failures are reported separately from 15 review alerts. All three pasted-image controls were missed. Three annotations, three repeated-logo documents and three raster text scans caused false review alerts. The scan analyses disclose partial candidate/pair coverage.

Localisation: 12/12 annotated boxes matched at IoU >= 0.5 on nine held-out signature documents, zero extra candidates on those annotated pages. This excludes non-signature-page false positives and is not real-world accuracy.

## Remaining limits

No real-world performance claim; no independently sourced attack corpus; no complete pre-planned shadow exploit suite; one renderer; no certificate revocation or trusted timestamp validation; no complete OS exploit sandbox; Linux-only OS memory enforcement; no dependency vulnerability audit. ELA misses the evaluated image edits; legitimate repeated imagery and annotations can produce review alerts.

The project is a better-tested educational prototype, not an authenticity certification service.
