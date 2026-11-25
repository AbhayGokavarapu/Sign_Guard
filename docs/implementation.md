# SignGuard — Implementation Notes

## Module dependency map

```
app.py
├── dashboard/overview.py
├── dashboard/document_analysis.py  → core/pipeline.py
├── dashboard/attack_lab.py         → simulation/controlled_scenarios.py
│                                   → core/pipeline.py
├── dashboard/forensic_visualization.py
├── dashboard/evaluation.py         → simulation/fixture_manager.py
│                                   → core/pipeline.py
├── dashboard/reports.py            → reporting/json_report.py
│                                   → reporting/pdf_report.py
│                                   → core/audit_logger.py
└── dashboard/presentation.py

core/pipeline.py
├── core/pdf_parser.py
├── core/document_classifier.py
├── core/crypto_verifier.py
├── core/revision_analyzer.py
├── core/signature_localizer.py
├── core/ela_detector.py
├── core/orb_matcher.py
├── core/ransac_verifier.py
├── core/evidence_fusion.py
└── core/audit_logger.py

simulation/
├── sample_generator.py   (ReportLab)
├── signed_samples.py     (pyHanko — optional)
├── controlled_scenarios.py
└── fixture_manager.py
```

## Algorithm details

### ELA (Module 6)
1. Convert image to RGB.
2. JPEG-recompress at `quality` (default 75).
3. Compute absolute pixel difference: `|orig - recomp|`.
4. Amplify: `diff * amplification` clipped to [0, 255].
5. Report mean/max/std of the grayscale residual channel.

### ORB (Module 7)
1. Convert both images to grayscale.
2. Extract up to 500 ORB keypoints with binary BRIEF descriptors.
3. Brute-force Hamming-distance kNN (k=2).
4. Apply Lowe's ratio test (threshold 0.75).
5. Apply mutual-match cross-check filter.

### RANSAC (Module 8)
1. Take filtered ORB match coordinate pairs.
2. Estimate homography with `cv2.findHomography(RANSAC, reproj=5px)`.
3. Classify matches as inliers (mask=1) or outliers (mask=0).
4. Geometric match = inliers ≥ 10 AND inlier ratio ≥ 30%.

### Evidence fusion (Module 10)
Priority order:
1. CRITICAL cryptographic failure → TAMPERING DETECTED
2. HIGH shadow / post-sig mod → REVIEW REQUIRED
3. ELA or RANSAC flag alone → REVIEW REQUIRED (low confidence)
4. No findings + crypto passed → CLEAN
5. Otherwise → INCONCLUSIVE

No numeric "forgery probability" is computed.
