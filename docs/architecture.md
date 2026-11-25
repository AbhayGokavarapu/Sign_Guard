# Architecture

Streamlit calls `core.pipeline.run`, which validates the file size/header and starts `core.worker`. The worker parses and renders within resource budgets, classifies the document, verifies CMS signatures with pyHanko and an explicit offline trust store, reconstructs revisions from the parsed xref chain, and analyses each page.

Each page produces revision/text differences, localisation candidates and raw ELA measurements. Candidate pairs, including cross-page pairs, pass through ORB/Hamming ratio and mutual matching, followed by RANSAC. Rule-based fusion merges findings with page numbers. Crypto-only and crypto-plus-revision modes support method comparison.

The parent process receives the result, appends the audit record under an interprocess lock, and reports any logging error. JSON/PDF reports include coverage and limitations. Representative images support the existing dashboard; per-page measurements and pair records retain the broader analysis results.

`simulation/security_fixtures.py` creates genuine signatures, byte modifications and valid incremental updates. `simulation/evaluation_dataset.py` generates annotated development/held-out controls; labels are never passed to `run` or `fuse`.

See THREAT_MODEL.md for trust boundaries and limitations. The worker is not a complete exploit sandbox.
