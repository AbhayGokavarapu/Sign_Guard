# SignGuard v2 — Complete Demo Guide for Faculty Presentation

> Last updated to reflect v2 implementation with mandatory pyHanko, multi-quality ELA,
> startxref-based revision analysis, removed CLEAN verdict, and 55/55 tests passing.

---

## Quick-start (before the demo)

```bat
REM From the project root — Windows
venv\Scripts\activate
streamlit run app.py
```

Browser opens at **http://localhost:8502**  
(Port is fixed in `.streamlit/config.toml` — no manual flag needed)

Or just double-click **`launch.bat`**.

---

## What to tell the audience in one sentence

> "SignGuard takes any PDF, runs genuine cryptographic verification plus five image-forensic algorithms, and produces an explainable verdict with visual evidence — all locally, with no AI model."

---

## Suggested total time: ~20 minutes

| Section | Page | Time |
|---|---|---|
| Introduction | Overview | 2 min |
| Live document upload | Document Analysis | 3 min |
| Attack lab (3–4 scenarios) | Attack Simulation Lab | 7 min |
| Algorithm deep-dive | Algorithm Visualizations | 3 min |
| Metrics | Evaluation | 2 min |
| Reports + audit | Reports & Audit | 1 min |
| (Optional) Presentation mode | Presentation Mode | 2 min |

---

## Step 1 — Overview page (2 min)

**Navigate:** Sidebar → 🏠 Overview

1. Point to the **Problem Statement** box — three real PDF attack classes:
   - **Byte tampering** — raw byte modification breaks the SHA-256 digest
   - **Shadow attack** — PDF incremental update overrides visible content after signing
   - **Visual forgery** — copy-pasted handwriting image, no crypto involved

2. Show the **System Pipeline** (right column) — 9 stages from input to verdict.

3. Walk the **three algorithm layers** in the Core Algorithms section:
   - Cryptographic: SHA-256, CMS/PKCS#7, X.509
   - PDF Structure: startxref-based revision discovery, pixel diff
   - Image Forensics: ELA, ORB, RANSAC

4. Highlight the four **Information Security Principles** cards at the bottom.

**Key point to say:** "Every step here is a real algorithm. No machine learning, no trained model — every verdict traces back to a specific cryptographic or image measurement."

---

## Step 2 — Document Analysis (3 min)

**Navigate:** Sidebar → 📄 Document Analysis

1. **Upload a PDF** — drag in any PDF or click Browse. Use your own document or one from `datasets/` for a known result.

2. The page immediately shows:
   - **Document identity banner** — filename, SHA-256 prefix, page count, bytes
   - **Live page preview** — use the page slider for multi-page documents
   - **Metadata panel** — author, creator, creation date, modification date
   - **Classification badge** — Cryptographically Signed / Visual Candidate / Unsigned

3. Click **🔬 Run Full Forensic Analysis**.

4. Walk the results **top to bottom**:

   **Verdict banner**
   - Colour coded: amber = REVIEW REQUIRED, red = TAMPERING DETECTED, grey = INCONCLUSIVE
   - Below the verdict: separate **Integrity Status** (NO TAMPERING DETECTED / INTEGRITY FAILURE / NOT ESTABLISHED / NOT APPLICABLE)
   - **Key point:** "Notice there is no CLEAN verdict. Even if bytes are intact, an untrusted self-signed certificate cannot establish signer identity — so we return INCONCLUSIVE rather than a false sense of security."

   **Findings list**
   - Each finding shows code (CRYPTO-001, SHADOW-001, etc.), severity, description, and a limitation note
   - Critical = red border, High = amber, Medium = blue, Low = grey

   **Cryptographic Verification expander**
   - Three separate checks: Byte integrity / Math valid / Cert trusted
   - ByteRange section: "Structurally valid", "Covers full file", "Covers signed revision" — three separate flags
   - Certificate details: subject, issuer, self-signed, test cert warning
   - **Key point:** "Mathematical validity and certificate trust are shown separately. A self-signed cert can produce a mathematically valid signature but still not prove who signed it."

   **Revision Analysis**
   - Revision count + discovery method (startxref-based is more reliable than raw %%EOF scan)
   - Shadow suspect flag + changed area percentage
   - Side-by-side page images if two revisions exist

   **Signature Localisation**
   - Blue info banner: "confidence scores are heuristic, not calibrated probabilities"
   - Show localisation pipeline expander — 5 intermediate images

   **ELA — Multi-Quality**
   - 4 tabs (Q65, Q75, Q85, Q95) — each shows raw diff and amplified visualization
   - **Key point:** "Amplification changes only the visual brightness — it does not affect the residual measurement or the verdict."

   **Download reports** — JSON (schema v2.0) and PDF

---

## Step 3 — Attack Simulation Lab (7 min — main demo feature)

**Navigate:** Sidebar → ⚗️ Attack Simulation Lab

This is the most impressive section. Each scenario generates synthetic PDF documents and runs the actual detection engine. The ground-truth label is hidden until after the verdict.

**For each scenario:**
1. Click the scenario button
2. Click **⚗️ Generate Synthetic Scenario**
3. Study the comparison view
4. Click **🔬 Run Detection Engine**
5. Read the verdict and evidence tabs
6. Expand **"Reveal ground-truth label"** to prove the detector worked independently

---

### Scenario A — Original Signed

- **What to show:** The document preview, the cryptographic expander showing PASS on integrity
- **What to say:** "This is a genuinely pyHanko-signed document using a local test certificate. Notice the verdict is INCONCLUSIVE — not CLEAN — because a self-signed certificate cannot prove who signed it. Mathematical integrity and signer identity are separate things."
- **Look for:** `integrity_status = PASS`, trust = `SELF-SIGNED (untrusted)`, identity = `UNVERIFIED`

---

### Scenario B — Signed-Byte Tampering

- **What to show:** The comparison view — both pages look identical. Point to the SHA-256 hash badges under each preview.
- **What to say:** "These two pages look completely identical to the human eye. Only one byte was changed deep in the file. The SHA-256 hash prefixes are different — that is the only visible difference. This is exactly why cryptographic verification exists."
- **Look for:** `CRYPTO-001 CRITICAL` finding, `integrity_status = FAIL`, red hash diff warning
- **Key point:** "The detector found the tampering purely from the byte digest. No visual difference was needed."

---

### Scenario C — Shadow Attack

- **What to show:** The side-by-side comparison — left shows "$1,000", right shows "$9,000". The pixel diff image. The revision timeline.
- **What to say:** "This is the most sophisticated attack. The original signature is cryptographically intact — the bytes were never modified. But a second revision was appended to the PDF that overrides the visible amount. This is called a shadow attack."
- **Look for:** `SHADOW-001 HIGH` finding, revision count = 2, changed area percentage, text diff summary
- **Expand:** Revision Analysis tab → show pixel diff and revision timeline
- **Key point:** "Cryptographic validity alone is not enough. You also need to compare what was visible at signing time vs. what is visible now."

---

### Scenario D — Visual Signature Duplication

- **What to show:** The ORB/RANSAC tab — keypoint images, green inlier lines
- **What to say:** "Two near-identical handwriting images appear in the document. ORB finds matching features in both. RANSAC confirms the matches are geometrically consistent — not random coincidence."
- **Look for:** `ORB-001 MEDIUM` finding, inlier count, inlier ratio, green match lines
- **Key point:** "Visual similarity does not prove the signature was stolen. It is evidence that warrants investigation — not proof of fraud."

---

### Scenario E — ELA Manipulation

- **What to show:** The Algorithm Visualizations page → ELA section → Q tabs and multi-quality comparison bar chart
- **What to say:** "ELA recompresses the image at a fixed JPEG quality and measures the residuals. Regions with different compression history produce higher residuals. Here you can compare how the residual changes across four quality settings."
- **Look for:** `ELA-001 MEDIUM` finding if mean residual > 25, sweep summary across Q65/75/85/95
- **Key point:** "High residuals can also be caused by high-contrast edges, printed text, or gradients. ELA is a supporting indicator only — never standalone proof."

---

### Scenario F — Unsigned Document

- **What to show:** The verdict (REVIEW REQUIRED or INCONCLUSIVE), zero crypto signatures, localisation results
- **What to say:** "No digital signature. No cryptographic checks are possible. The detector correctly returns a conservative result."
- **Key point:** "Absence of a signature does not mean the document is forged. It just means we cannot verify integrity cryptographically."

---

## Step 4 — Algorithm Visualizations (3 min)

**Navigate:** Sidebar → 🔬 Algorithm Visualizations

Shows every intermediate image from the last analysis. Walk through each expander:

| Expander | What to point out |
|---|---|
| 🔐 Cryptographic Verification | 4 metrics per signature, certificate code block, test cert warning |
| 📐 ByteRange Coverage | Three separate coverage flags: structural / full file / signed revision |
| 📋 PDF Revision Analysis | Revision timeline list, side-by-side renders, pixel diff, changed area |
| ✍️ Signature Localisation | All 6 intermediate images in a 3×2 grid, candidate crops with heuristic scores |
| 🖼️ ELA Multi-Quality | Bar chart of mean residual across Q65/75/85/95 (with alert threshold line), 4-panel images, amplification note |
| 🎯 ORB Feature Matching | Keypoint images for A and B, raw matches, filtered matches |
| 📐 RANSAC Verification | Coloured inlier/outlier image, 4 metrics |
| ⚖️ Evidence Fusion | Module status bar chart, integrity_verdict + verdict, findings list with limitations |

---

## Step 5 — Evaluation (2 min)

**Navigate:** Sidebar → 📊 Evaluation

The page loads pre-computed results from `benchmarks/evaluation_results.json`.

**Show the actual numbers:**

| Metric | Value |
|---|---|
| Classification accuracy | 80.0% |
| Tampering recall | **100%** (no positive cases missed) |
| Tampering precision | 42.9% (conservative — prefers review over miss) |
| Tampering F1 | 60.0% |
| Localisation detection rate | 83.3% |
| Mean processing time | 0.466 s/file |

**What to say:** "Notice recall is 100% — the system never misses a tampered document in this test set. The precision is lower because it also flags unsigned and legitimate multi-revision documents for review — a deliberately conservative design."

**Show:** Confusion matrix heatmap, dataset distribution chart, per-file results table, runtime histogram.

**Always say:** "These are synthetic benchmarks only. They confirm the algorithms work correctly on the designed test cases. They do not prove real-world accuracy."

---

## Step 6 — Reports & Audit (1 min)

**Navigate:** Sidebar → 📋 Reports & Audit

1. Click **⬇ Download JSON Report** — open in Notepad/VS Code and show:
   - `"schema_version": "2.0"`
   - `"disclaimer"` field — explicitly not an authenticity certificate
   - `"integrity_verdict"` as a top-level field
   - Findings array with codes, severity, measurements, limitations

2. Click **⬇ Download PDF Report** — open and show:
   - Verdict banner with integrity status
   - Per-signature ByteRange section (three coverage flags)
   - ELA multi-quality table
   - Limitations section at the end

3. Scroll to **Audit Chain**:
   - Green ✓ = chain intact
   - Each record: event ID, timestamp, document SHA-256, verdict, prev_hash, record_hash
   - Explain: "Each record's hash depends on the previous one. If any record is modified, the chain breaks. However, detecting a full chain rewrite requires an independently stored chain head."

---

## Step 7 — Presentation Mode (optional, 2 min)

**Navigate:** Sidebar → 🎓 Presentation Mode

This page hides the sidebar for clean projection. Use the **Previous / Next / Reset** buttons to step through:

| Step | What happens |
|---|---|
| 1 — Upload Document | File uploader or one-click demo document |
| 2 — Baseline Verification | Run pipeline, see verdict + integrity status |
| 3 — Attack Demonstration | Scenario selector, generate+detect, ground-truth reveal |
| 4 — Algorithm Evidence | ELA / ORB / Revision diff tabs |
| 5 — Final Verdict & Report | Large verdict, findings, report downloads |

**Tip for projection:** Use this page instead of navigating between pages — the cleaner layout reads better on a projector.

---

## Common viva / faculty questions and answers

| Question | Answer |
|---|---|
| Does it need internet? | No. 100% local. No API key, no cloud, no GPU. |
| Does it use AI or machine learning? | No. All algorithms are traditional: SHA-256, CMS, Otsu thresholding, ORB, RANSAC. Every decision traces to a measured value. |
| Why is there no CLEAN verdict? | A self-signed or untrusted certificate cannot establish signer identity. The best outcome for a signed document is INCONCLUSIVE (no tampering detected, identity unverified) or REVIEW REQUIRED. Claiming CLEAN would be misleading. |
| What is a shadow attack? | A PDF exploit where the signer sees one content (e.g. $1,000) and later readers see different content (e.g. $9,000), achieved by appending a second revision. The original signature remains mathematically valid because the signed bytes were never modified. |
| Why does Scenario B look identical visually? | Byte tampering is invisible to the human eye — only 1 byte was changed. The SHA-256 digest of the signed bytes detects it instantly. This demonstrates why cryptographic verification is necessary. |
| What does the ByteRange check actually verify? | 7 structural properties: 4 non-negative integers, correct ordering, no overlaps, bounds within file, presence of a contents gap, whether the signature covers the full current file or only an earlier revision. |
| What is the difference between integrity and trust? | Integrity: the signed bytes have not been modified since signing. Trust: the certificate was issued by a trusted Certificate Authority. A self-signed cert can have valid integrity but zero trust — the signer's identity cannot be established. |
| Is ELA reliable on PDFs? | ELA was designed for JPEG photographs. Applied to rendered PDF page crops, it measures recompression residuals — but those residuals are affected by the rendering engine's resampling, not necessarily by manipulation. ELA is a supporting indicator only. |
| What does amplification change in ELA? | Only the visual brightness of the heatmap. The residual measurements (mean, max, std) and the verdict logic are computed from the raw difference — amplification is never applied to them. |
| Can ORB/RANSAC prove signature theft? | No. Visual similarity confirms geometric consistency between two regions. It does not establish who created each image, whether copying was unauthorised, or signer identity. It is evidence for further investigation. |
| How reliable is the audit log? | Each record's hash is deterministically computed from its content plus the previous hash. Any modification breaks the chain. Detecting a full chain rewrite or truncation requires an independently stored chain head — the system explains this limitation explicitly. |
| Why is recall 100% but precision only 43%? | The system is designed to be conservative — when in doubt, return REVIEW REQUIRED rather than miss a potentially tampered document. This trades precision for recall intentionally. |
| Does synthetic evaluation prove real-world accuracy? | No. The evaluation dataset was generated by this codebase. The metrics confirm the algorithms function correctly on the designed test cases. Real-world performance would require evaluation on genuine forged documents. |
| Can it detect all shadow attacks? | No. Shadow attack detection compares rendered page images using one rendering engine. Attacks that produce identical renders are not detectable. The limitation is explicitly documented. |

---

## Limitations to state clearly during the demo

1. **ELA** — high residuals can come from high-contrast edges, printed text, or gradients. Not standalone proof.
2. **Test certificates** — demo signed documents use a locally generated self-signed RSA-2048 certificate. Not a trusted root CA.
3. **ORB/RANSAC** — visual similarity does not establish signer identity or prove unauthorised reuse.
4. **Synthetic evaluation** — 30-fixture dataset. Does not establish real-world generalisation.
5. **Python 3.14 / pyHanko** — pyHanko targets Python 3.9–3.12. Some math-validity paths return UNKNOWN on 3.14.
6. **Shadow detection** — one rendering engine. Attacks with identical renders are undetectable.
7. **This is a research tool** — results require qualified expert review before any legal or operational use.

---

## Running the tests (to show during demo)

```bat
REM From the SignGuard directory
venv\Scripts\activate

REM Full pytest suite — 55 tests
python -m pytest tests/ -v

REM Integration + scenario evidence
python run_tests_quick.py

REM Evaluation benchmark (~15–60 s)
python benchmarks\run_evaluation.py
```

Expected:
- pytest: **55 passed, 0 failed**
- run_tests_quick.py: **33 passed, 0 failed**
- Scenario evidence files appear in `outputs/scenario_results/`
