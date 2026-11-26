# Four-page workspace — 27 November 2026

The dashboard now contains only:

1. Document analysis (default)
2. Document comparison
3. Attack lab
4. Evidence viewer

The Overview, Evaluation, Reports & audit, Case review and Presentation page implementations have been removed. They are not needed by the remaining analysis workflow. Core detector code, saved benchmark data, graphs, fixtures, reporting libraries and independent CLI verification remain available. Historical documents/test counts describe the older nine-page interface unless explicitly updated.

## Retained behavior

- PDF/JSON downloads in Document analysis and analysed Attack lab scenarios.
- PDF/JSON and comparison evidence ZIP export in Document comparison.
- Shared signed/current images, change highlights, crop, raw pixel evidence and timeline in revision views.
- Evidence source selection for uploaded documents and latest lab scenarios.
- Input/settings handling, public-demo privacy defaults and bounded workers.
- Clear session resets to Document analysis.
- A legacy or invalid selected page resets before rendering navigation, rather than breaking an existing session after deployment.

The dedicated UI for human assessments, audit-history viewing and uploaded-package verification is removed. Backend support for verifying previously exported packages is retained.

## Documentation and evaluation

The root README, beginner guide and faculty demonstration instructions describe the four-page flow. Saved evaluation numbers/figures can be used in the PPT; they never affected current-document detection. This navigation change does not alter classification thresholds or benchmark measurements.

## Verification scope

AppTest exercises the real entry point, exact four-item navigation, initial page, removed-page fallback, empty/populated pages for all six scenarios, unchanged/changed/missing revision evidence, lab generation/analysis, comparison export, session clearing and analysis upload/settings/retry. The upload boundary uses injected byte streams because AppTest has no native file-picker action. Core regression tests cover analysis and report behavior.

Production Cloud rendering and automatic redeployment cannot be verified from the workspace network. Local checks are not a claim that the live service has finished rebuilding.

## Executed verification

- Targeted dashboard/public/session checks: **27 passed** in 31.52 seconds.
- Full regression suite: **142 passed**, zero failures, in 111.44 seconds.
- The count changes from the previous 143-test run because obsolete page tests were removed/replaced with four-page and legacy-navigation regressions.
- No detector thresholds or saved benchmark measurements were changed.
