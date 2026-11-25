# Security improvement audit

| Requirement | Implementation and evidence |
|---|---|
| Genuine signed baseline and byte tampering | `simulation/security_fixtures.py`; strict baseline/digest outcome tests |
| Valid incremental content replacement | Preserved signed prefix, parsed xref chain, last-page render/text tests |
| Benign modification controls | Additional signature and annotation tests; annotation false alert documented |
| Trust and validity separated | Explicit roots, cryptography/asn1crypto conversion, unknown issuer and expired certificate tests |
| Invalid signature mathematics | CMS signature mutation regression test |
| Amplification-independent ELA | Raw high-energy statistic and all-measurement/verdict invariance test |
| All-page and cross-page processing | Per-page pipeline, last-page localisation/change and cross-page duplication tests |
| Explicit incomplete coverage | Candidate/pair/signature limits in coverage and reports |
| Resource limits | Subprocess timeout, Linux address-space/CPU limits, dimensions/total pixel checks |
| Malformed/encrypted PDFs | Explicit unsupported outcomes and actual encrypted PDF test |
| Audit robustness | Interprocess lock, fsync/replace, corrupt-log refusal, concurrent writes and checkpoints |
| Visible audit failures | JSON/PDF/UI warning and disk-error regression |
| Held-out evaluation | 13 development + 39 held-out synthetic controls; fixed thresholds |
| Method comparisons | Crypto-only, crypto+revision and full metrics |
| Localisation IoU | Annotated held-out boxes with one-to-one matching |
| Accurate faculty documentation | README, demo guide, threat model, research comparison and final verification |
| Reproducible launch | Python 3.12 dependency lock, loopback Streamlit config, safe launchers |

## Not established

Real-world detection performance; independently sourced forged-document corpus; comprehensive pre-planned shadow exploits; complete long-term archival validation; automatic online certificate retrieval; exploit-proof sandboxing; Windows OS memory limit; complete OS/native-library vulnerability coverage; visual authorship or signer identity from self-signed certificates.

These are limitations, not completed or verified requirements. See FINAL_VERIFICATION.md for executed results.

Version 3.2 adds ordered comparison, bounded/ranked pair selection, precise signature coverage, consecutive timelines, original/suspect comparison, static inspection, review history, evidence packages, optional independent rendering, offline lifecycle validation, session clearing and a shared processing queue. The executed known-vulnerability audit checked all 69 installed Python components with no skipped packages. See INVESTIGATION_UPGRADE.md and FINAL_VERIFICATION.md.
