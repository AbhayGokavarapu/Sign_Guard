# SignGuard 3.2 verification

Historical checks below were executed on 25–26 November 2026 with Python 3.12, on Linux. The current four-page workspace verification is recorded in `FOUR_PAGE_WORKSPACE.md`.

## Current four-page workspace — 27 November 2026

The dashboard now contains Document analysis (default), Document comparison, Attack lab and Evidence viewer only. The full current suite passed **142 tests**, zero failures, in 111.44 seconds. Targeted checks passed 27 tests. Obsolete page tests were replaced/removed; this changes the test count without changing detector thresholds. See `FOUR_PAGE_WORKSPACE.md` for scope and retained exports. Remaining sections below are historical runs.

## Dashboard follow-up — 26 November 2026

The dashboard follow-up adds 24 AppTest and display regression cases. The full suite passed **143 tests**, zero failures, in 152.94 seconds. See `DASHBOARD_AUDIT.md` for the reproduced revision-image issue, fixes, exact interaction coverage and production-access limits. The checks below describe the earlier 25 November run.

## Automated checks

- Earlier suite: **119 passed**, zero failures, 93.54 seconds, including signature coverage, CRL/OCSP freshness and revocation, RFC3161 timestamp integrity/trust, ordered differences, revision history, evidence archive tampering, human review chains, queue saturation and process-group timeout cleanup.
- Quick checks: 29 security tests plus six scenario checks, all passed.
- Upload kit: all seven expected outcomes verified; reports and ZIP regenerated.
- Streamlit AppTest: all nine pages rendered; comparison, review saving, evidence package verification, stale-package invalidation and session clearing passed.
- Eight externally authored, MIT-licensed pyHanko fixtures matched upstream assertions. Poppler and SignGuard agreed on mathematical validity for all 11 signatures; all four nonstandard-coverage documents require review. This is not an independent human adjudication.
- Python dependency audit: 69 components checked, zero known vulnerabilities, zero skipped. Saved database results and CycloneDX inventory are in benchmarks/. OS and native package vulnerability coverage is incomplete.

## Measured detector limitations

The 39 held-out synthetic cases produced TP 9, FP 9, FN 3, TN 18: precision 50%, recall 75%, F1 0.60, accuracy 69.23%. Pasted image edits were missed; legitimate annotations, repeated logos and scans can trigger review. These are review alerts, not proof of fraud. Development and held-out controls share a generator.

## Deployment and trust limits

The public Streamlit domain cannot be reached from this workspace due to network policy; local verification does not establish the current live deployment state. Poppler is configured through packages.txt. Offline revocation evidence and explicit trust roots must be supplied by the operator; online fetching is disabled. Trusted timestamps do not constitute full archival validation. Evidence signing is optional and requires a separately trusted operator public key.

Independent human adjudication and a representative real-world fraud corpus remain pending. Worker limits are not a complete exploit sandbox. Linux process groups are terminated on timeout; Windows currently kills the direct worker. Clear session drops retained references and is not a forensic erasure guarantee.
