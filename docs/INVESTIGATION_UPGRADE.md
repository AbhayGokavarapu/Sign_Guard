# SignGuard 3.2 investigation and evidence upgrade

## Implemented capabilities

| Capability | Entry point | What it establishes |
|---|---|---|
| Precise signature coverage | Digital signatures / JSON | ByteRange must match a parsed signed revision and pyHanko coverage must be ENTIRE_FILE or ENTIRE_REVISION. Matching digests with nonstandard coverage trigger CRYPTO-006 review. |
| Ordered text comparison | Revision analysis and Document comparison | Preserves line order and repeated lines rather than comparing sets. |
| Ranked visual comparisons | Full analysis | Appearance and geometry scores prioritise plausible pairs; page-pair round-robin avoids repeatedly spending the whole budget on the first candidate. Limits remain explicit. |
| Known original versus suspect | Document comparison | Hashes, per-page ordered text, dimensions, visual changes, metadata, added/removed pages; differences are not a forgery verdict. |
| Consecutive revision history | Document revisions → timeline | Every consecutive parsed revision, with explicit additions/removals and a comparison budget. Changes later restored remain in history. |
| Static PDF inventory | Static content result tab | JavaScript, automatic/additional actions, launches, XFA, embedded-file structures and external links. No actions are executed and no link is fetched. |
| Human review | Case review | Append session assessments/reasons to machine finding IDs without replacing detector outcomes. Reviewer names are self-asserted, not authenticated. |
| Reproducibility | report.json → provenance | Code commit, engine source hash, exact installed package versions, thresholds, settings, explicit-root hash and offline evidence hashes. |
| Evidence package | Reports & audit | PDF/JSON report, provenance, representative PNGs, review history and exact checksum membership. Source PDF is excluded unless requested. |
| Package verification | Reports & audit or CLI | Rejects changed files, traversal/duplicate members, extra/missing files and oversized archives without extracting or executing contents. |
| Independent rendering | Optional analysis checkbox | MuPDF versus Poppler; bounded pages, normalised pixel differences and explicit incomplete/unavailable states. Not all viewer differentials are detected. |
| Independent mathematical validator | benchmarks/run_independent_validation.py | Poppler pdfsig with certificate/OCSP network validation disabled; reports disagreements rather than equating different trust policies. |
| Offline CRL/OCSP | Operator-provided evidence directory | Requires trusted, current evidence for a non-revoked path; revoked/stale/untrusted/insufficient cases remain distinct. |
| RFC3161 timestamps | Digital signatures | Cryptographic timestamp integrity, TSA trust and timestamp time are distinct from the signer-reported date. |
| Session clearing | Sidebar Clear session | Drops retained session document/result/review references and rotates uploader keys. Does not delete downloaded files or guarantee forensic erasure. |
| Bounded admission | All worker operations | Cross-process slots limit concurrent analyses; saturated requests return a useful busy result after a bounded wait. |

## Operator configuration

Use Python 3.12. `packages.txt` installs `poppler-utils` on Streamlit Community Cloud; locally install the same package through your normal package manager. If Poppler is absent, optional checks report that explicitly.

- `SIGNGUARD_MAX_CONCURRENT_JOBS`: default 2. Size this for the hosting machine's actual memory.
- `SIGNGUARD_QUEUE_WAIT_S`: default 2 seconds before a busy response.
- `SIGNGUARD_TRUST_ROOTS`: explicit PEM trust-root bundle. Do not automatically trust demo certificates.
- `SIGNGUARD_REVOCATION_DIR`: operator-controlled directory of signed `.crl`, `.ocsp`, DER or PEM evidence. Use a separate directory from the root bundle. Maximum 30 files, 2 MiB each. No PDF-provided network endpoints are fetched.
- `SIGNGUARD_EVIDENCE_SIGNING_KEY`: optional path to an operator-held Ed25519 PEM private key. Keep it outside the repository and provision through protected deployment settings. Packages include its public key and a signature over the manifest. Independently distribute the trusted public key/fingerprint.
- `SIGNGUARD_AUDIT_LOG`: optional local audit file path. Public demo persistence remains disabled.

CRL/OCSP ingestion uses pyHanko's certificate validator with required revocation information when evidence is supplied. OCSP support follows the validator's declared-AIA rules; a response for a certificate without an appropriate declaration may remain UNKNOWN. Stale or unrelated evidence must never become GOOD. Online CRL/OCSP retrieval is deliberately disabled, so the uploaded PDF cannot make the server fetch an attacker-chosen address.

RFC3161 timestamps require an explicit trusted TSA chain to be labelled trusted. Timestamp trust does not imply complete PAdES long-term archival validation or automatic proof of historic non-revocation.

## Verify an evidence package

```bash
python tools/verify_evidence.py signguard-evidence.zip
python tools/verify_evidence.py signguard-evidence.zip --expected-manifest-sha256 YOUR_INDEPENDENT_REFERENCE
python tools/verify_evidence.py signguard-evidence.zip --trusted-public-key operator-public.pem
```

Checksums without an independently retained reference only prove internal consistency. An attacker can rewrite both the files and manifest. A valid signature using an embedded key does not establish that the key belongs to a trusted examiner. The verifier reports these distinctions.

## External evaluation and supply chain

Eight external PDFs are included under `datasets/external-pyhanko/`, with MIT attribution, original paths, source commit, SHA-256 and upstream test references. These include Adobe Reader double signatures and nonstandard signature coverage. They are independently authored fixtures, but are not an independently collected real-world fraud corpus and are not independent of the pyHanko library's own tests.

`python benchmarks/run_independent_validation.py` compares SignGuard with upstream assertions and Poppler and records every outcome. Independent human adjudication remains PENDING; the application cannot substitute for an external examiner.

`python tools/generate_sbom.py` exports the installed Python components as CycloneDX JSON. The saved dependency audit checked all 69 installed components, reported zero known vulnerabilities and skipped none. This is time-specific database evidence, not a proof that all dependencies are safe. The CI workflow runs tests, compatibility checks, a vulnerability audit and the inventory export on pushes/pull requests.

## Limits that remain

On Linux, a timeout terminates the worker process group, including native renderer children. Windows currently terminates the direct worker; OS memory enforcement is Linux-specific.

The worker is resource isolation, not a complete native-code exploit sandbox. A single host administrator can replace code or signing keys. Visual duplication may be benign; image-edit misses and false review alerts remain possible. Renderer disagreement can result from normal antialiasing. No claim of legal authenticity, universal shadow-attack detection or production security is made.
