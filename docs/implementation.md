# Implementation and verification

- Python 3.12 is the validated runtime. Install `requirements-lock.txt` for the tested dependency versions.
- pyHanko is required. Signing failures raise errors; demos never substitute unsigned PDFs for signed controls.
- Offline verification uses no implicit OS roots. Set `SIGNGUARD_TRUST_ROOTS` to a PEM bundle to provision explicit roots. Test roots remain test-only.
- Byte integrity, public-key validity, certificate trust, modification policy, revocation status and timestamp status are separate report fields.
- Revisions follow pyHanko's parsed /Prev chain. `startxref`/EOF tokens locate ends only for parsed offsets; arbitrary stream tokens cannot add revisions.
- Comparisons use the earliest signed revision against each current page, so later signatures cannot hide visible changes relative to the first signature. Annotation appearance is excluded from content rendering; pyHanko's policy assessment remains separate and can conservatively reject annotations.
- ELA statistics and high-energy percentage use unamplified residuals. Amplification changes only displayed pixels.
- ORB uses ratio filtering and actual reciprocal index pairs. RANSAC visualisation draws onto the original image pair.
- Every page is visited. Full-resolution intermediate images are retained for representative pages to bound memory; summary evidence covers all pages. Explicit candidate/pair limits are reported as partial coverage.
- Audit writes use a cross-process file lock, fsync and atomic replacement. Corrupt logs fail verification and cannot be silently overwritten. Export checkpoints and store them independently.
- Analysis defaults to a subprocess with timeout. Linux enforces address-space and CPU limits; rendering budgets are checked before pixmap allocation. Windows lacks the Linux memory cap.

Security regressions are asserted in `tests/test_security_outcomes.py`. The benchmark reports held-out alert metrics, per-category failures, three analysis modes, confirmed byte failures separately from review alerts, and one-to-one localisation IoU >= 0.5. Shared synthetic generators limit the independence of these experiments.

Version 3.2: signature coverage is bound to parsed revision boundaries AND pyHanko coverage. Text differences preserve order/repetition. Candidate pairs are ranked by normalised appearance and geometry and balanced across page-pair groups. New worker operations share a cross-process queue. Reports include provenance, static-content inventory, consecutive history and optional renderer comparisons. Offline lifecycle evidence requires non-revocation information when provisioned. See INVESTIGATION_UPGRADE.md.
