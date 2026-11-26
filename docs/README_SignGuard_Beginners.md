# SignGuard — A Beginner’s Guide to the Project and Dashboard

**Version:** 3.2 · **Guide prepared:** 27 November 2026
**Current dashboard:** Document analysis, Document comparison, Attack lab and Evidence viewer only.

**Read this if:** You are new to this project, cybersecurity, PDF signatures or the dashboard.

**Dashboard address:** https://signguard-phjtwb7iuwmmiwvvjszrdj.streamlit.app/
**Repository:** https://github.com/AbhayGokavarapu/Sign_Guard

The dashboard address was supplied for the deployed project. Live availability could not be verified from the development workspace because its network blocked access. This guide describes the current source implementation, including the revision-display fix.

## Contents

1. [What are we building?](#1-what-are-we-building)
2. [Security concepts in everyday language](#2-security-concepts-in-everyday-language)
3. [How SignGuard works](#3-how-signguard-works)
4. [Your first complete walkthrough](#4-your-first-complete-walkthrough)
5. [Understanding the main verdict](#5-understanding-the-main-verdict)
6. [Every dashboard page explained](#6-every-dashboard-page-explained)
7. [Understanding images, measurements and findings](#7-understanding-images-measurements-and-findings)
8. [Understanding evaluation results](#8-understanding-evaluation-results)
9. [Technical explanation and project structure](#9-technical-explanation-and-project-structure)
10. [Running the project yourself](#10-running-the-project-yourself)
11. [Troubleshooting](#11-troubleshooting)
12. [Limits and future work](#12-limits-and-future-work)
13. [How to describe the project in a presentation](#13-how-to-describe-the-project-in-a-presentation)

## 1. What are we building?

**SignGuard is a PDF security investigation tool.** It helps answer:

- Has content protected by a digital signature changed?
- What changed after a document was signed?
- How does a suspect PDF differ from a known original?
- Do image regions look suspiciously similar?
- Does the PDF contain scripts, automatic actions or embedded-file structures?
- What evidence supports the result, and what could not be checked?

Imagine receiving an invoice that originally said **$1,000**, but now says **$9,000**. SignGuard examines the cryptographic protection, saved revisions and visible differences. It organizes evidence for a human to interpret.

**What it does not establish:** whether every statement is true, who made a change, whether a change was authorized, or whether somebody committed fraud. A suspicious result is not automatically a legal conclusion.

### What has been built?

A four-page Streamlit dashboard, PDF signature checks, consecutive revision analysis, original–suspect comparison, visual inspection, static-content inventory, manual evidence interpretation, PDF/JSON reports and verifiable evidence packages. Optional features include a second rendering engine, offline certificate revocation checks and timestamp validation.

There is **no trained machine-learning model** in this implementation. The analysis uses cryptographic verification, parsing, comparisons and classical computer vision. A GPU or AI API key is not required.

## 2. Security concepts in everyday language

| Term | Beginner-friendly meaning | Important limit |
|---|---|---|
| Integrity | Whether protected content has changed. | Unchanged content can still contain false statements. |
| Authenticity | Evidence about origin or identity. | A valid calculation alone does not establish a trusted identity. |
| Confidentiality | Keeping information private. | SignGuard is not a document-encryption service. Public uploads reach the hosting server. |
| Availability | Keeping a service usable. | Time and concurrency limits help, but do not guarantee uptime. |
| Hash / SHA-256 | A fingerprint calculated from exact file bytes. | Different hashes establish different bytes, not malicious intent. |
| Private key | Secret material used to create a digital signature. | It must be protected by its owner. |
| Public key | Material used to check the corresponding signature. | Trust in its owner requires more evidence. |
| Certificate | Information linking a public key to a claimed identity. | Trust depends on the issuing chain and validation policy. |
| Revision | A saved version within the PDF’s update history. | Later changes can be legitimate. |
| Finding | A specific observation produced by the tool. | Read its explanation rather than only its severity. |
| False positive | A benign case incorrectly flagged by an evaluation rule. | Alerts need review. |
| False negative | A positive case missed by that rule. | No alert is not a guarantee of safety. |

### A signature picture is not a digital signature

A **signature picture** is a drawing or image of handwriting. It can be copied and pasted.

A **digital signature** is a cryptographic seal associated with specific document bytes. The verifier checks the protected content and signature using a public key.

A PDF can contain either, both or neither. A visible handwritten signature does not establish cryptographic protection.

### Three separate questions

1. **Integrity:** Do the protected bytes still match?
2. **Mathematical validity:** Does the signature calculation verify?
3. **Trust:** Does the certificate lead to an explicitly trusted authority?

For example, integrity and mathematics can pass while certificate trust is not established. This is normal for the project’s self-signed demonstration certificate; it does not identify a trusted real-world signer.

## 3. How SignGuard works

```text
Upload a PDF or an original–suspect pair
                  ↓
Validate input and admit work within resource limits
                  ↓
Run enabled checks in an isolated worker
                  ↓
Collect findings, measurements, coverage and limitations
                  ↓
Present a verdict with supporting evidence
                  ↓
Manual interpretation and report/evidence export
```

The system checks digital signatures, reconstructs parsed revisions, compares ordered text and rendered pages, examines image candidates, and inventories significant PDF structures. Optional independent rendering compares two engines.

**Signature coverage matters:** A signature can protect an earlier revision while later updates change the current document. “Signature valid” is therefore not the same as “the current document has never changed.”

Rendering means turning a PDF page into a picture. An isolated worker is a separate process with processing limits; it is not a complete security sandbox.

## 4. Your first complete walkthrough

Use synthetic samples first. You do not need your own documents.

1. Open **Attack lab** and select Scenario A.
2. Click **Generate scenario**, then **Analyse scenario**. Inspect integrity and certificate trust separately.
3. Select Scenario B and repeat generation/analysis. Observe the integrity failure even though pages may look identical.
4. Select Scenario C and repeat. The later revision changes the displayed amount.
5. Click **Explore the visual evidence** and select the latest lab scenario.
6. In **Revision changes**, inspect the signed/current pages, highlight, zoom and raw difference evidence.
7. Return to Attack lab to download its PDF report and JSON evidence.
8. Optionally open **Document comparison** and use the supplied original/modified sample-pair button.

The application opens directly on Document analysis. There is no separate Presentation page in the current four-page dashboard.

### What the six scenarios teach

| Scenario | Expected main result | Lesson |
|---|---|---|
| A — Original signed | INCONCLUSIVE | Signed bytes and mathematics pass, but the demo certificate is self-signed and untrusted. |
| B — Signed-byte tampering | TAMPERING DETECTED | Signed metadata changes can break integrity without visibly changing the page. |
| C — Post-signing replacement | REVIEW REQUIRED | The current amount changes from $1,000 to $9,000 in a later revision while earlier signed bytes remain intact. |
| D — Visual duplication | REVIEW REQUIRED | Matching handwriting imagery is evidence of similarity, not automatically unauthorized copying. |
| E — ELA demonstration | INCONCLUSIVE | Recompression residuals do not by themselves prove editing. |
| F — Unsigned document | INCONCLUSIVE | Absence of a signature does not establish forgery. |

The scenarios are separate controlled fixtures; generating one does not necessarily modify your uploaded baseline. Check the displayed evidence source.

### Trying normal uploads

Open **Document analysis → Need a document? Download a verified sample**. Download a numbered PDF, then upload it through the input above. Alternatively, download all seven samples and extract the ZIP first.

| Sample file | Expected verdict |
|---|---|
| `01_signed_original.pdf` | INCONCLUSIVE |
| `02_tampered_signed_bytes.pdf` | TAMPERING DETECTED |
| `03_changed_after_signing.pdf` | REVIEW REQUIRED |
| `04_duplicated_signature_images.pdf` | REVIEW REQUIRED |
| `05_unsigned_document.pdf` | INCONCLUSIVE |
| `06_change_on_last_page.pdf` | REVIEW REQUIRED |
| `07_signature_on_last_page.pdf` | INCONCLUSIVE |

## 5. Understanding the main verdict

| Verdict | Meaning | What to do |
|---|---|---|
| **TAMPERING DETECTED** | Signed-byte integrity or mathematical signature verification failed. | Read the specific finding and inspect the document context. This does not identify intent or the person responsible. |
| **REVIEW REQUIRED** | A revision, coverage, policy, certificate or supporting visual issue needs examination. | Inspect affected pages, evidence and legitimate explanations. |
| **INCONCLUSIVE** | No decisive finding establishes authenticity or tampering. | Check signatures, trust, missing evidence and coverage. |
| **UNSUPPORTED** | Input was rejected or processing failed/exceeded limits. | Treat it as unexamined; investigate the reason or retry appropriately. |

There is no **CLEAN** authenticity verdict. **INCONCLUSIVE is not “genuine.”**

A separate integrity label such as **NO TAMPERING DETECTED** concerns the checked signed bytes. It does not certify every later revision, signer identity or the truth of the document.

Read results in this order: **verdict → finding → supporting evidence → coverage → human assessment**.

## 6. Every dashboard page explained

### 6.1 Document analysis

**Purpose:** Examine one PDF.

1. Upload a PDF, or download a supplied sample first.
2. Inspect the preview and settings.
3. Click **Run document analysis**.
4. Read the result tabs and download reports.

Settings include ELA recompression quality, heatmap brightness and optional independent rendering. Heatmap brightness affects display, not the verdict. The optional renderer check can take longer and requires Poppler.

| Result tab | How to read it |
|---|---|
| Findings | Specific observations, descriptions and affected pages. |
| Digital signatures | Integrity, mathematical validity, trust and policy information. |
| Document revisions | Signed/current views, changes and consecutive history. |
| Static content | Scripts, actions, links or embedded-file structures found without execution. |
| Independent rendering | Agreement/disagreement or unavailable/incomplete status. |
| Coverage | Work completed, processing limits and omissions. |

**Signature fields:**

- **Signed-byte integrity:** Whether protected content still matches.
- **Mathematical signature:** Whether its cryptographic verification succeeds.
- **Certificate trust:** Whether an explicit trusted chain is established.
- **ByteRange:** File regions included in the signed digest, excluding the signature container.
- **Coverage:** Which parsed revision/content the signature protects.
- **Modification policy:** Evaluation of changes against signature permissions; it does not establish authorization by itself.
- **Revocation:** Whether sufficient valid evidence establishes a lifecycle state. **UNKNOWN is not revoked and is not proof of non-revocation.**
- **Timestamp:** Integrity and trust of timestamp evidence. A signer-entered date is not a trusted timestamp.

### 6.2 Document comparison

**Purpose:** Compare a known original with a suspect copy, including unsigned PDFs.

Upload both documents and click **Compare documents**, or use the supplied sample-pair button.

- **Page changes:** Added/removed/modified pages and ordered text differences.
- **Visual differences:** Representative original, suspect and difference images.
- **Metadata:** Changes in descriptive file information.
- **Export:** Comparison JSON, PDF and evidence package.

Pages are aligned by position. Page reordering can therefore produce several differences. Different hashes prove different bytes; a metadata difference alone does not prove fraud. The original’s reliability must come from its source.

### 6.3 Attack lab

**Purpose:** Learn using controlled scenarios A–F.

Choose a scenario → **Generate scenario** → compare documents → **Analyse scenario** → inspect findings → reveal the known label.

The ground-truth label is for evaluation and is not passed into the detector. Original and scenario files may render identically. Use **Explore the visual evidence** to open the latest lab result in Evidence viewer.

### 6.4 Evidence viewer

**Purpose:** Inspect images and measurements behind an uploaded-document or latest-lab result. Select the correct evidence source first.

| Tab | Meaning |
|---|---|
| Signature regions | Candidate signature-like areas and localization stages. A candidate is not guaranteed to be a signature. |
| ELA residuals | Original, amplified and raw residuals at available JPEG qualities. |
| Feature matching | Keypoints, filtered correspondences and RANSAC evidence. |
| Revision changes | Signed/current comparison and revision information. |
| Evidence ledger | Coverage, provenance, per-page measurements, compared pairs and supplementary checks. |

Images may be representative rather than a separate displayed result for every page. Use the ledger/report to inspect all-page measurements and omitted work.

### Downloads within the four retained pages

- **Document analysis:** PDF report and JSON evidence after analysis.
- **Attack lab:** PDF report and JSON evidence for the selected analysed scenario.
- **Document comparison:** Comparison PDF, JSON and prepared comparison evidence ZIP.
- **Evidence viewer:** Inspect underlying images, per-page measurements and coverage; use the source analysis/lab workflow for its report downloads.

The dedicated Overview, Evaluation, Reports & audit, Case review and Presentation pages have been removed. This does not change detection algorithms. Saved benchmark data, graphs and research scripts remain in the repository for the PPT.

There is no current UI for saving human assessments, viewing shared audit history or verifying uploaded evidence ZIPs. Backend verification remains available through `python tools/verify_evidence.py package.zip`. A valid checksum manifest demonstrates consistency, not document authenticity; use an independent reference for stronger assurance.

### Sidebar: Clear session

Removes retained uploads, results and review references and returns to Document analysis. Export first. It does not delete your downloaded files or guarantee forensic erasure.

## 7. Understanding images, measurements and findings

### Revision images

- **Signed revision:** The earlier signed reference page.
- **Current revision:** Its current appearance.
- **Red highlight:** A display aid for pixels above the configured difference threshold.
- **Zoomed region:** An enlarged detected-change area, when available.
- **Raw pixel difference:** Black means equal pixels; brighter values mean different pixels.
- **Threshold mask:** White marks pixels exceeding the threshold.

**An all-black difference image usually means no visible difference, not a broken image.** Scenario B can break signed-byte integrity while retaining identical rendering. Scenario C has a visible change. Unsigned scenarios cannot provide a signed baseline.

Changed-area percentage concerns pixels, not importance: a tiny amount-field change can matter greatly. Text findings can trigger review even when the changed visual area is small. Added/removed pages and missing comparisons must be read through the timeline and coverage.

### Visual analysis

**Localization** means finding candidate regions. A heuristic score is not the probability that an image is a genuine signature.

**ORB** finds distinctive visual points. **RANSAC** checks whether matching points fit consistent geometry. Inlier/outlier images help inspect consistency, but repeated legitimate graphics can also match.

**ELA** measures differences associated with JPEG recompression. Text edges and ordinary textures can create bright residuals. Brightness does not establish fraud; ELA alone cannot reliably establish manipulation.

**Independent rendering** compares MuPDF and Poppler. Normal rendering choices can cause disagreement. It does not detect every viewer-dependent attack.

### Example finding identifiers

| Identifier | Broad interpretation |
|---|---|
| CRYPTO-001 | Signed-content digest/integrity failure. |
| CRYPTO-003 / CRYPTO-004 | Post-signing or modification-policy evidence; read the exact descriptions. |
| CRYPTO-006 | Nonstandard signature coverage requiring review. |
| SHADOW-001 / SHADOW-002 | Render/text revision-change evidence, not universal shadow-attack proof. |
| ORB-001 | Supporting geometric duplication evidence. |
| ELA-001 | Elevated residual evidence requiring interpretation. |
| PDF-ACTIVE-001 | Significant PDF actions need review; they were not executed. |
| RENDER-001 | Independent rendering engines disagree. |
| CERT-001 / TIME-001 | Certificate revocation / timestamp verification findings. |

Always prefer the current finding’s full text over guessing from its code or color. Severity describes review priority, not a percentage chance of fraud.

## 8. Understanding evaluation results

The full-pipeline evaluation used **39 held-out synthetic cases**:

| Outcome | Count | Meaning |
|---|---:|---|
| True positive (TP) | 9 | Positive control correctly flagged. |
| False positive (FP) | 9 | Negative control incorrectly flagged. |
| False negative (FN) | 3 | Positive control missed. |
| True negative (TN) | 18 | Negative control correctly left unflagged. |

- **Precision = 9 / (9 + 9) = 50%:** Half the positive alerts matched positive labels.
- **Recall = 9 / (9 + 3) = 75%:** Three-quarters of labelled positives were detected.
- **F1 = 0.60:** A combined precision/recall measure.
- **Accuracy = (9 + 18) / 39 = 69.23%:** Correct classifications across all cases.

These use the benchmark’s alert definitions, not legal fraud judgments. Pasted image edits were missed; benign annotations, repeated logos and scans produced false alerts. Shared synthetic generation limits independence and real-world generalization.

| Method | Precision | Recall | Accuracy |
|---|---:|---:|---:|
| Cryptography only | 100% | 25% | 76.92% |
| Cryptography + revision | 66.67% | 50% | 76.92% |
| Full pipeline | 50% | 75% | 69.23% |

**Why does adding methods reduce accuracy?** It detects more positive cases but also flags more benign cases. More checks do not automatically mean a better result on every metric.

**Software tests are different:** The earlier nine-page suite passed **143 tests**; the current four-page suite passed **142 tests**. See `docs/FOUR_PAGE_WORKSPACE.md` for scope. That verifies tested behavior, not 100% detection accuracy. Eight external fixture expectations matched and the two validators agreed on mathematical validity for eleven signatures; these are separate checks, not real-world accuracy claims.

A saved Python dependency audit checked 69 components with zero known vulnerabilities and none skipped. This is time-specific database evidence, not proof of safety or complete OS/native coverage.

## 9. Technical explanation and project structure

| Technology | Role |
|---|---|
| Streamlit | Four-page interactive dashboard and session state. |
| pyHanko / Certvalidator | PDF signatures, certificate paths, lifecycle evidence and timestamps. |
| PyMuPDF | Parsing, text extraction and bounded rendering. |
| OpenCV / NumPy / SciPy | Image processing, feature matching and geometry. |
| Poppler, optional | Independent rendering and mathematical validation. |
| ReportLab / JSON | Readable and structured reports. |
| Cryptography | Supporting cryptographic operations and optional evidence signing. |
| Pytest / AppTest | Analysis and interface regression checks. |

```text
app.py                  Main dashboard
streamlit_app.py        Public Cloud entry point
config.py               Settings and limits
core/                   Parsing, verification, comparisons, workers and evidence logic
dashboard/              Four pages and shared navigation/evidence components
simulation/             Signed fixtures, scenarios and sample generation
samples/                Ready-to-upload demonstration kit
reporting/              PDF/JSON reports and evidence ZIPs
tests/                  Regression and security outcome tests
benchmarks/             Evaluation scripts and recorded measurements
datasets/               Synthetic inputs and external fixtures
docs/                   Deployment, threat model, verification and detailed design
tools/                  Evidence verifier and dependency inventory utility
```

Current default budgets include 50 MB uploads, 200 pages, 20 revisions, 10 signatures, 20 visual candidate-pair comparisons and a 120-second worker timeout. Aggregate rendering and timeline limits can be reached before other maxima. These are separate limits, not a promise that every document within them will complete.

Two worker slots are the default; busy admission waits briefly before returning a retry message. Linux enforces OS memory/CPU limits and process-group timeout cleanup. Windows currently terminates the direct worker. None of this constitutes a complete exploit sandbox.

Offline CRL/OCSP and timestamp trust need operator-provided evidence/roots. PDF-selected certificate URLs are not fetched. Full long-term archival validation is not claimed.

## 10. Running the project yourself

Use **Python 3.12**. A virtual environment keeps project dependencies separate from other software.

### Linux / macOS

From the repository directory:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python -m streamlit run app.py --server.port 8502
```

### Windows PowerShell

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-lock.txt
python -m streamlit run app.py --server.port 8502
```

If script activation is restricted, invoke the environment directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8502
```

Open **http://localhost:8502** and keep the terminal running. `localhost` means your own computer; it is not a public deployment. A bare Streamlit command normally uses port 8501. The supplied `launch.bat` / `sh launch.sh` use port 8502 after dependencies are installed.

Poppler is optional for independent checks. On Debian/Ubuntu, install `poppler-utils` through the normal package manager. Community Cloud uses `packages.txt`. Without it, optional checks should report unavailable.

### Developer verification commands

```bash
python -m pytest tests/ -q
python run_tests_quick.py
python benchmarks/run_evaluation.py
python -m simulation.build_upload_kit
python tools/verify_evidence.py signguard-evidence.zip
```

The benchmark and sample-kit commands regenerate files; they are developer workflows, not necessary for a beginner demonstration. A full benchmark can take several minutes.

For Community Cloud, use branch `streamlit-deploy`, entry point `streamlit_app.py` and Python 3.12. The public entry point disables shared audit persistence/history and benchmark regeneration. See the repository’s `docs/DEPLOYMENT.md` and `docs/INVESTIGATION_UPGRADE.md` for operator configuration.

## 11. Troubleshooting

| Situation | Meaning / next action |
|---|---|
| `localhost refused to connect` | The local server is stopped or the port is wrong. Start Streamlit and use the address printed in its terminal. |
| Public page is slow | Startup, hosting capacity or processing may take time. Retry when the service is available; inspect the actual error rather than assuming a detector result. |
| Busy workers | Capacity is occupied. Wait briefly and retry; avoid repeated simultaneous requests. |
| Black revision difference | The compared pages look identical. Try Scenario C for visible change evidence. |
| No signed baseline | The PDF is unsigned or no suitable signed-page comparison exists. Use original–suspect comparison if you have a reference. |
| Untrusted demo certificate | Expected for a self-signed test certificate. Do not automatically trust it to make the dashboard green. |
| UNKNOWN revocation | Sufficient trusted/current evidence was not established. It is not proof of non-revocation. |
| No geometric match | Too few suitable regions/features or no consistent pair. This does not prove no copying occurred. |
| Bright ELA residual | May be normal edges, texture or compression. Inspect other evidence. |
| Unsupported / incomplete | Read the reason and coverage. The document is not cleared by failed processing. |
| No result after changing a setting/scenario | Old results may be invalidated intentionally. Run the selected analysis again. |
| Independent renderer unavailable | Install/configure Poppler or proceed with explicitly limited single-engine analysis. |
| Uploading ZIP fails | Extract the sample kit and upload one PDF. ZIP input is for the evidence-package verifier. |
| Exported ZIP verifies without external trust | Internal consistency passed. Retain an independent hash or trusted public key for stronger assurance. |

## 12. Limits and future work

Use synthetic or non-sensitive PDFs on the public demo because uploads are processed on its server. Clearing a session is not a secure-erasure guarantee. Export needed records before clearing or leaving.

Current limitations include missed image edits, benign visual alerts, incomplete processing under budgets, unsigned documents without a signed reference, and reliance on configured certificate evidence. A valid signature does not establish truthful content. Static inventory is not a full malware scanner. Independent rendering cannot detect every shadow attack.

Priority future work: a licensed representative real-world corpus, independent expert adjudication, improved image-edit detection, fewer false alerts, authenticated reviewers, stronger sandboxing and broader OS/native vulnerability checks. These remain future work rather than completed claims.

## 13. How to describe the project in a presentation

> SignGuard is an explainable PDF security investigation system. It combines digital-signature verification, revision analysis, original–suspect comparison and visual evidence, then supports manual interpretation and reproducible export. It separates content integrity, certificate trust and suspicious visual similarity. Its measured limitations are disclosed rather than treating every alert as proof of fraud.

Before explaining any result, answer:

1. Which document/scenario and page am I examining?
2. What did the tool actually check?
3. What finding and evidence support the verdict?
4. What work or trust information is missing?
5. Could there be a legitimate explanation?
6. What assessment can I reasonably make, and what should I leave unresolved?

**Remember:** valid mathematics is not automatically trusted identity; a later change is not automatically malicious; and an inconclusive result is not a certificate of authenticity.

---

### Where the recorded facts come from

This standalone guide was checked against the project source and recorded outputs, including `app.py`, `dashboard/`, `config.py`, `samples/upload-kit/verified_results.json`, `benchmarks/evaluation_results.json`, `docs/FINAL_VERIFICATION.md` and `docs/DASHBOARD_AUDIT.md`. Counts describe recorded runs, not newly executed tests for this documentation-only task.
