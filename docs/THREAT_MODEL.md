# SignGuard threat model

## Assets and trust boundaries

Protect the integrity of signed PDF bytes, distinguish later visible content from the signed revision, preserve honest verification results, and retain an auditable analysis history. The uploaded PDF, its metadata, embedded images, certificate subjects, and claimed signing times are untrusted. Certificate roots are trusted only when explicitly provisioned by the operator. Demo roots are never installed automatically.

The PDF crosses from the Streamlit process into a disposable Python worker. The worker has a wall-clock timeout, Linux address-space/CPU limits, pre-render dimension and aggregate pixel budgets, page/signature/revision/candidate/pair limits. This is resource isolation, not a complete operating-system security sandbox. Native-library vulnerabilities remain possible. Windows enforces timeout/render budgets but lacks the Linux address-space limit.

## Adversaries and outcomes

| Attacker capability | Control | Expected evidence |
|---|---|---|
| Alter signed content or metadata bytes | CMS digest verification | CRYPTO-001, integrity failure |
| Replace CMS public-key signature | Mathematical verification | CRYPTO-002, invalid signature |
| Append a valid revision changing visible content | Parsed /Prev chain, signed revision comparison, pyHanko modification policy | CRYPTO-003 and/or SHADOW-001/002; review |
| Duplicate raster signatures | Candidate localisation, ORB and RANSAC | ORB-001; review, never proof of theft |
| Supply self-signed, unknown-issuer, expired certificate | Explicit offline roots, separate validity/trust/identity | Untrusted or expired status |
| Supply malformed, encrypted or resource-intensive PDF | Bounded worker | Explicit unsupported/incomplete result |
| Modify/corrupt audit records | Hash chain validation | Integrity error; refuse append |
| Rewrite/truncate complete audit history | Independently retained checkpoint | Checkpoint mismatch/truncation |

## Assumptions and exclusions

An intact signature establishes integrity of the signed bytes, not the truth of the document or authority of its signer. A stolen private key can produce valid signatures; SignGuard cannot identify that event. Revocation and trusted timestamps are not validated; the reported signing time is a signer claim. No certificate network fetching is performed. Without a configured trust-root file, no issuer is implicitly trusted.

Post-signing content replacement is a valid incremental-update attack demonstration. It is not a comprehensive reproduction of pre-planned hide/replace/hide-and-replace shadow exploits or cross-viewer parser differentials. The detector uses one renderer. Identical-render attacks and hidden semantic changes may evade it.

Visual similarity cannot distinguish a stolen signature from legitimate repeated artwork. ELA measures recompression residuals of rendered content and cannot establish forgery. Localisation is heuristic; scores are not probabilities. Limits and incomplete coverage are included in the result. Every current page is visited; candidate and pair budgets may leave visual comparisons incomplete.

The local machine, application code, explicitly configured root file, and independently stored audit checkpoint are assumed protected. A host administrator can replace code, logs and checkpoints. File locking prevents cooperating concurrent writers from losing records; it does not defend against arbitrary privileged writers.
