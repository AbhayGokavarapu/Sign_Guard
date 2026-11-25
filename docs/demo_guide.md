# SignGuard v3 faculty demonstration

Use Python 3.12 and the pinned dependencies. Start with `python -m streamlit run app.py`; open http://localhost:8502. Run the tests before presenting. Avoid claiming that every PDF or every attack is supported.

## Suggested sequence (20 minutes)

1. **Problem and threat model (3 minutes).** Explain the difference between signed bytes, current visible content, certificate trust and signer identity. State that a valid signature does not establish the truth of a contract. Show `THREAT_MODEL.md`.
2. **Upload and analysis (3 minutes).** Show filename/hash, classification, verification states, findings and coverage. Analysis runs in a disposable worker. A timeout or unsupported result is not an authenticity verdict.
3. **Attack lab (7 minutes).** Generate and detect scenarios A–F. Reveal ground truth afterwards; labels are not detector inputs.
4. **Method comparison (3 minutes).** Show held-out results, false positives and missed image edits. Explain what the combined method adds and what it costs.
5. **Reports, audit and limitations (2 minutes).** Export reports and an independent audit checkpoint.
6. **Questions (2 minutes).** Use the honest answers below.

## Expected scenario observations

| Scenario | What to demonstrate | Expected result |
|---|---|---|
| A | Real CMS signature and self-signed test cert | Integrity PASS, math valid, untrusted identity; INCONCLUSIVE |
| B | Identical page rendering but changed signed metadata bytes | CRYPTO-001; TAMPERING DETECTED |
| C | Original signed amount and valid incremental replacement | Signed bytes remain intact; CRYPTO-003/004 and SHADOW-001/002; REVIEW REQUIRED |
| D | Two repeated raster handwriting regions | ORB features, RANSAC inliers, ORB-001; REVIEW REQUIRED |
| E | The same gradient control on both sides | Multi-quality ELA visualisation; INCONCLUSIVE. No manipulated-image claim |
| F | No digital signature | Integrity not applicable; INCONCLUSIVE |

Signing adds its own revisions, so do not promise an exact revision count of two. Scenario C demonstrates post-signing content replacement, not a complete pre-planned shadow exploit. Scenario B changes a metadata marker, not necessarily exactly one byte.

For benign controls, show the automated tests: a second signature remains policy-compliant and does not create a content-change finding. A text annotation preserves signed-byte integrity but pyHanko can conservatively classify it as a policy violation; report this as a false review alert, not confirmed forgery.

## Explaining the results

Show separate integrity and overall verdict fields. Never call an intact, untrusted signature a verified person's identity. Certificate revocation and trusted timestamps are explicitly not checked. ELA mean, standard deviation and high-energy percentage come from raw residuals; amplification affects only the visualisation.

Every current page is visited. Reports record all per-page candidate boxes and checked candidate pairs; dashboard images are representative intermediate views. Limits can omit candidates or pairs, and coverage must disclose that.

## Evaluation discussion

The benchmark has 13 development and 39 held-out synthetic controls. Thresholds were kept fixed. Held-out seeds still share the generator, so this is not independent real-world validation.

Full pipeline: precision 50%, recall 75%, accuracy 69.2%, F1 60%. TP=9, FP=9, FN=3, TN=18. All three pasted-image controls are missed. Benign annotations, logos and scans trigger false review alerts. Crypto-only has fewer alerts but misses revision/visual attacks; adding layers trades more detections for more false positives. Show the actual method-comparison table.

Localisation IoU results cover only annotated signature pages; they exclude broader non-signature-page false positives. Do not describe them as universal 100% signature-detection accuracy.

## Honest viva answers

- **Does it use AI?** No trained model. It combines cryptographic and classical CV algorithms.
- **Why not CLEAN?** Integrity, certificate trust and real-world authenticity are different claims.
- **Can it catch every shadow attack?** No. One renderer and visible/text comparison have explicit blind spots.
- **Does similarity prove a stolen signature?** No. Legitimate logos and repeated graphics can match too.
- **Can ELA prove a pasted image?** No. Our held-out pasted-image controls are missed; ELA is supporting evidence only.
- **Are timestamps/revocation verified?** No. The reports explicitly say they are not validated.
- **Is the audit log immutable?** No. It is tamper-evident relative to an independently retained checkpoint and a protected host.
- **Is this production-ready?** No. Resource controls and outcome tests improve the prototype; real-world validation and stronger isolation remain necessary.

## Commands

```bash
python -m pytest tests/ -q
python run_tests_quick.py
python benchmarks/run_evaluation.py
```

The benchmark can take several minutes. Use saved measured outputs during the presentation. Never quote historical 100% alert recall as the current result.
