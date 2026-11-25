# SignGuard — Architecture

## Pipeline

```
PDF Input (bytes)
  │
  ▼
[1] pdf_parser.py        — validate, parse, render, hash, extract sigs
  │
  ▼
[2] document_classifier.py — classify: crypto / visual / unsigned / unsupported
  │
  ├──[crypto]──► [3] crypto_verifier.py    — ByteRange, CMS, cert, coverage
  │
  ├──────────► [4] revision_analyzer.py    — revisions, diff, shadow suspect
  │
  ├──────────► [5] signature_localizer.py  — adaptive thresh, components, crops
  │
  ├──[image]──► [6] ela_detector.py        — JPEG recompress, residual stats
  │
  ├──[2 crops]─► [7] orb_matcher.py        — ORB keypoints + Hamming matching
  │
  ├──────────► [8] ransac_verifier.py      — RANSAC homography, inlier filter
  │
  ▼
[9] evidence_fusion.py   — rule-based verdict: TAMPERING/REVIEW/INCONCLUSIVE
  │
  ├──► [10] audit_logger.py    — SHA-256 hash-chained tamper-evident log
  ├──► reporting/json_report.py
  └──► reporting/pdf_report.py
```

## Key design decisions

| Decision | Rationale |
|---|---|
| No ML models | Reproducibility, no training data needed, explainable output |
| pyHanko optional | Graceful fallback to raw ByteRange/CMS parsing |
| Ground-truth kept separate | Prevents scenario labels from influencing detector |
| Local only | No API keys, no cloud, no GPU required |
| Hash-chained audit | Provides tamper evidence for the verification history |
