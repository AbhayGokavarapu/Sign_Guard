"""
Evaluation benchmark — generates labeled synthetic dataset and measures metrics.
Saves results to benchmarks/ directory.
"""
import sys, os, json, time, hashlib, csv
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import warnings
warnings.filterwarnings("ignore")

import config
from core.pipeline import run
from simulation.fixture_manager import generate_dataset

BENCH_DIR = config.BENCHMARKS_DIR
os.makedirs(BENCH_DIR, exist_ok=True)

print("Generating evaluation dataset...")
manifest_data = generate_dataset(force=True)
files = manifest_data["files"]
print(f"  {len(files)} fixtures generated.")

print("Running pipeline on all fixtures...")
records = []
t_start = time.perf_counter()

for entry in files:
    path     = os.path.join(config.BASE_DIR, entry["file"])
    label    = entry["label"]
    category = entry["category"]
    if not os.path.exists(path):
        continue

    with open(path, "rb") as f:
        raw = f.read()

    t0 = time.perf_counter()
    try:
        result = run(raw, os.path.basename(path))
        pred   = result.fusion.verdict.value if result.fusion else "UNSUPPORTED"
        cls_pred = result.classification.doc_class.value if result.classification else "UNSUPPORTED"
        n_cands  = len(result.localization.candidates) if result.localization else 0
        elapsed  = round(time.perf_counter() - t0, 3)
    except Exception as exc:
        pred = "UNSUPPORTED"
        cls_pred = "UNSUPPORTED"
        n_cands  = 0
        elapsed  = round(time.perf_counter() - t0, 3)

    records.append({
        "file":     os.path.basename(path),
        "category": category,
        "label":    label,
        "pred":     pred,
        "cls_pred": cls_pred,
        "n_cands":  n_cands,
        "elapsed":  elapsed,
    })

total_time = round(time.perf_counter() - t_start, 3)
print(f"  Evaluation complete in {total_time:.1f}s over {len(records)} files.")

# ── Task B: Tampering alert metrics ───────────────────────────────────────
# Positive = label involves tampering or shadow (TAMPERING_DETECTED / REVIEW_REQUIRED)
# Predicted positive = TAMPERING DETECTED or REVIEW REQUIRED

def is_positive_label(label: str) -> bool:
    return label.upper().replace("_"," ") in (
        "TAMPERING DETECTED", "REVIEW REQUIRED"
    )

def is_positive_pred(pred: str) -> bool:
    return pred.upper() in ("TAMPERING DETECTED", "REVIEW REQUIRED")

TP = FP = TN = FN = unsup = 0
for r in records:
    actual = is_positive_label(r["label"])
    pred_p = is_positive_pred(r["pred"])
    if r["pred"] == "UNSUPPORTED": unsup += 1
    elif actual and pred_p:        TP += 1
    elif not actual and pred_p:    FP += 1
    elif actual and not pred_p:    FN += 1
    else:                          TN += 1

n_eval = len(records) - unsup
precision = TP / max(TP+FP, 1)
recall    = TP / max(TP+FN, 1)
f1        = 2*precision*recall / max(precision+recall, 1e-9)
accuracy  = (TP+TN) / max(n_eval, 1)

tamper_metrics = {
    "task":      "Task B — Tampering Alert Detection",
    "note":      "Synthetic dataset only. Does not establish real-world generalisation.",
    "total":     len(records), "evaluated": n_eval, "unsupported": unsup,
    "TP": TP, "FP": FP, "FN": FN, "TN": TN,
    "accuracy":  round(accuracy,  4),
    "precision": round(precision, 4),
    "recall":    round(recall,    4),
    "f1":        round(f1,        4),
}

# ── Task A: Classification metrics ────────────────────────────────────────
cls_map = {
    "genuine":    "Cryptographically Signed",
    "tampered":   "Cryptographically Signed",
    "shadow":     "Cryptographically Signed",   # shadow docs may have sigs
    "visual_only":"Visual Signature Candidate",
    "unsigned":   "Unsigned",
}
cls_tp = cls_fp = cls_fn = cls_tn = 0
for r in records:
    expected_cls = cls_map.get(r["category"], "")
    predicted_cls = r["cls_pred"]
    if expected_cls == predicted_cls:
        cls_tp += 1
    else:
        cls_fn += 1

cls_acc = cls_tp / max(len(records), 1)
cls_metrics = {
    "task":     "Task A — Document Classification",
    "total":    len(records),
    "correct":  cls_tp,
    "incorrect":cls_fn,
    "accuracy": round(cls_acc, 4),
    "note":     "Per-class P/R/F1 requires more samples per class for statistical validity.",
}

# ── Task E: Runtime performance ───────────────────────────────────────────
times = [r["elapsed"] for r in records]
import statistics
perf = {
    "task":        "Task E — Runtime Performance",
    "total_s":     total_time,
    "n_files":     len(times),
    "mean_s":      round(statistics.mean(times), 3),
    "median_s":    round(statistics.median(times), 3),
    "min_s":       round(min(times), 3),
    "max_s":       round(max(times), 3),
    "stdev_s":     round(statistics.stdev(times) if len(times) > 1 else 0, 3),
    "environment": {
        "python":   sys.version,
        "platform": sys.platform,
    },
}

# ── Task C: Localisation ─────────────────────────────────────────────────
sig_docs     = [r for r in records if r["category"] in ("genuine","visual_only")]
found        = sum(1 for r in sig_docs if r["n_cands"] > 0)
not_found    = len(sig_docs) - found
loc_metrics  = {
    "task":        "Task C — Signature Localisation",
    "sig_documents": len(sig_docs),
    "at_least_one_found": found,
    "none_found":  not_found,
    "detection_rate": round(found/max(len(sig_docs),1), 4),
    "note":        (
        "IoU-based precision/recall requires ground-truth bounding-box annotations, "
        "which are not available for auto-generated synthetic fixtures. "
        "Detection rate measures whether >=1 candidate was found in documents "
        "expected to have visual signature regions."
    ),
}

# ── Save all results ───────────────────────────────────────────────────────
full_results = {
    "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "total_files":  len(records),
    "total_time_s": total_time,
    "note":         "Synthetic dataset evaluation only.",
    "records":      records,
    **tamper_metrics,
}

with open(os.path.join(BENCH_DIR, "evaluation_results.json"), "w") as f:
    json.dump(full_results, f, indent=2)

with open(os.path.join(BENCH_DIR, "classification_metrics.json"), "w") as f:
    json.dump(cls_metrics, f, indent=2)

with open(os.path.join(BENCH_DIR, "tampering_metrics.json"), "w") as f:
    json.dump(tamper_metrics, f, indent=2)

with open(os.path.join(BENCH_DIR, "localization_metrics.json"), "w") as f:
    json.dump(loc_metrics, f, indent=2)

with open(os.path.join(BENCH_DIR, "dataset_manifest.json"), "w") as f:
    json.dump(manifest_data, f, indent=2)

# CSV
with open(os.path.join(BENCH_DIR, "evaluation_results.csv"), "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["file","category","label","pred","cls_pred","n_cands","elapsed"])
    writer.writeheader()
    writer.writerows(records)

with open(os.path.join(BENCH_DIR, "runtime_metrics.json"), "w") as f:
    json.dump(perf, f, indent=2)

print("\n=== Evaluation Results ===")
print(f"  Task B — Tampering: Acc={tamper_metrics['accuracy']:.1%} "
      f"P={tamper_metrics['precision']:.1%} "
      f"R={tamper_metrics['recall']:.1%} "
      f"F1={tamper_metrics['f1']:.1%} "
      f"TP={TP} FP={FP} FN={FN} TN={TN}")
print(f"  Task A — Classification accuracy: {cls_metrics['accuracy']:.1%}")
print(f"  Task C — Localisation rate: {loc_metrics['detection_rate']:.1%}")
print(f"  Task E — Mean processing: {perf['mean_s']:.3f}s | "
      f"Median: {perf['median_s']:.3f}s | Max: {perf['max_s']:.3f}s")
print(f"\n  Results saved to benchmarks/")
print(f"  IMPORTANT: Synthetic evaluation only — does not establish real-world generalisation.")
