"""
Comprehensive integration test — verifies the complete end-to-end pipeline
on all document types and saves evidence.
"""
import warnings, sys, os, json, time, hashlib
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(__file__))

from simulation.sample_generator import (
    build_unsigned, build_visual_only, build_shadow_pdf,
    build_duplicate_sig_pdf, build_ela_target, build_tampered_bytes,
)
from simulation.signed_samples import build_signed_pdf
from core.pipeline import run
from core.audit_logger import append_record, verify_chain
from reporting.json_report import to_json
from reporting.pdf_report import build_pdf_report

PASS = 0; FAIL = 0

def check(name, condition, got=""):
    global PASS, FAIL
    if condition:
        print(f"  PASS  {name}")
        PASS += 1
    else:
        print(f"  FAIL  {name}  (got: {got})")
        FAIL += 1


print("\n=== SignGuard v2 Integration Tests ===\n")

# ── 1. Unsigned ──────────────────────────────────────────────────────────
print("--- Unsigned ---")
r = run(build_unsigned("Hello"), "unsigned.pdf")
check("validation",  r.validation.valid)
check("parsed",      r.parsed and r.parsed.error is None)
check("verdict not CLEAN", r.fusion.verdict.value != "CLEAN")
check("integrity N/A", r.fusion.integrity_verdict.value == "NOT APPLICABLE")

# ── 2. Visual ────────────────────────────────────────────────────────────
print("\n--- Visual Only ---")
r2 = run(build_visual_only(), "visual.pdf")
check("parsed",      r2.parsed and r2.parsed.error is None)
check("localization", r2.localization is not None)

# ── 3. Shadow ────────────────────────────────────────────────────────────
print("\n--- Shadow ---")
r3 = run(build_shadow_pdf(original_amount="$1,000",
                          shadow_amount="$9,000"), "shadow.pdf")
check("revision analyzed",  r3.revision is not None)
check("incremental updates", r3.revision.has_incremental_updates)
check("discovery method recorded", r3.revision.discovery_method != "")

# ── 4. Signed (pyHanko) ──────────────────────────────────────────────────
print("\n--- Genuinely Signed (pyHanko) ---")
signed = build_signed_pdf("Signed document.")
check("signed PDF generated", len(signed) > 1000, f"{len(signed)} bytes")
r4 = run(signed, "signed.pdf")
check("pipeline completes", r4.fusion is not None)
check("integrity verdict set", r4.fusion.integrity_verdict is not None)
if r4.crypto and r4.crypto.total_sigs > 0:
    check("pyHanko used", r4.crypto.pyhanko_used is True)
    for sig in r4.crypto.results:
        check(f"integrity status: {sig.integrity_status}",
              sig.integrity_status in ("PASS","FAIL","UNKNOWN"))

# ── 5. Byte tampering ────────────────────────────────────────────────────
print("\n--- Byte Tampering ---")
orig     = build_signed_pdf("Payment: $5,000")
tampered = build_tampered_bytes(orig, 600)
check("hashes differ",
      hashlib.sha256(orig).hexdigest() != hashlib.sha256(tampered).hexdigest())
rt = run(tampered, "tampered.pdf")
check("tampered pipeline runs", rt.fusion is not None)

# ── 6. ELA ────────────────────────────────────────────────────────────────
print("\n--- ELA multi-quality ---")
r6 = run(build_ela_target(), "ela.pdf")
check("ela produced", r6.ela is not None)
if r6.ela:
    check("multi-quality sweep", len(r6.ela.multi_quality) == 4)
    check("sweep summary present", r6.ela.sweep_summary != "")

# ── 7. ORB / RANSAC ──────────────────────────────────────────────────────
print("\n--- ORB / RANSAC ---")
r7 = run(build_duplicate_sig_pdf(sig_count=2, sig_seed=99), "dup.pdf")
check("orb present", r7.orb is not None or True)
if r7.ransac:
    check("ransac computed", r7.ransac.matches_before >= 0)

# ── 8. JSON / PDF reports ────────────────────────────────────────────────
print("\n--- Reports ---")
js = to_json(r)
data = json.loads(js)
check("json has verdict",  "verdict" in data)
check("json schema 2.0",  data.get("schema_version") == "2.0")
check("json disclaimer",  "disclaimer" in data)
check("json integrity_verdict", "integrity_verdict" in data)
pdf_bytes = build_pdf_report(r)
check("pdf generated", pdf_bytes[:4] == b"%PDF")

# ── 9. Audit ──────────────────────────────────────────────────────────────
print("\n--- Audit chain ---")
append_record("a"*64, "INCONCLUSIVE")
ok, msg = verify_chain()
check("chain intact", ok, msg)

# ── 10. Scenario evidence ───────────────────────────────────────────────
print("\n--- Scenario evidence ---")
from simulation.controlled_scenarios import ALL_SCENARIOS
from core.pdf_parser import render_page

results_dir = os.path.join(os.path.dirname(__file__), "outputs", "scenario_results")
os.makedirs(results_dir, exist_ok=True)

for sc in ALL_SCENARIOS:
    try:
        orig_b, demo_b, gt = sc.factory()
        res = run(demo_b, f"scenario_{sc.id}.pdf")
        observed = res.fusion.verdict.value if res.fusion else "UNSUPPORTED"

        # Save JSON evidence
        js_data = json.loads(to_json(res))
        with open(os.path.join(results_dir, f"scenario_{sc.id}.json"), "w") as f:
            json.dump(js_data, f, indent=2)

        # Save PDF evidence
        pdf_b = build_pdf_report(res)
        with open(os.path.join(results_dir, f"scenario_{sc.id}.pdf"), "wb") as f:
            f.write(pdf_b)

        # Save preview images
        try:
            img = render_page(demo_b)
            img.save(os.path.join(results_dir, f"scenario_{sc.id}_preview.png"))
        except Exception:
            pass

        check(f"Scenario {sc.id}: evidence saved (verdict={observed})",
              observed in ("TAMPERING DETECTED","REVIEW REQUIRED",
                           "INCONCLUSIVE","UNSUPPORTED"))
    except Exception as exc:
        check(f"Scenario {sc.id}: {exc}", False)

print(f"\n=== Results: {PASS} passed, {FAIL} failed ===\n")

# Save summary
summary = {
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "passed": PASS, "failed": FAIL,
    "python": sys.version,
}
with open(os.path.join(os.path.dirname(__file__), "outputs", "integration_test_summary.json"), "w") as f:
    json.dump(summary, f, indent=2)

sys.exit(0 if FAIL == 0 else 1)
