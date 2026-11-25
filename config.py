"""SignGuard — global configuration constants and security limits."""
import os

BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
DATASETS_DIR   = os.path.join(BASE_DIR, "datasets")
OUTPUTS_DIR    = os.path.join(BASE_DIR, "outputs")
LOGS_DIR       = os.path.join(BASE_DIR, "logs")
BENCHMARKS_DIR = os.path.join(BASE_DIR, "benchmarks")
ASSETS_DIR     = os.path.join(BASE_DIR, "assets")
SCENARIO_RESULTS_DIR = os.path.join(OUTPUTS_DIR, "scenario_results")

for _d in (OUTPUTS_DIR, LOGS_DIR, BENCHMARKS_DIR, SCENARIO_RESULTS_DIR,
           os.path.join(DATASETS_DIR, "genuine"),
           os.path.join(DATASETS_DIR, "tampered"),
           os.path.join(DATASETS_DIR, "shadow"),
           os.path.join(DATASETS_DIR, "visual_only"),
           os.path.join(DATASETS_DIR, "unsigned")):
    os.makedirs(_d, exist_ok=True)

# ── PDF / rendering limits ─────────────────────────────────────────────────
MAX_FILE_SIZE_MB     = 50
MAX_PAGE_COUNT       = 200
MAX_PAGE_WIDTH_PX    = 5000
MAX_PAGE_HEIGHT_PX   = 7000
RENDER_DPI           = 144
THUMBNAIL_DPI        = 96
MAX_REVISIONS        = 20
MAX_SIGNATURES       = 10
MAX_LOC_CANDIDATES   = 15
MAX_CANDIDATE_PAIRS  = 20
PROCESSING_TIMEOUT_S = 120   # seconds

# ── ELA ────────────────────────────────────────────────────────────────────
ELA_QUALITIES        = [65, 75, 85, 95]   # multi-quality sweep
ELA_DEFAULT_QUALITY  = 75
ELA_DEFAULT_AMP      = 15
ELA_HIGH_THRESHOLD   = 25.0   # mean residual that raises a finding

# ── ORB / RANSAC ───────────────────────────────────────────────────────────
ORB_N_FEATURES          = 500
ORB_RATIO_THRESH        = 0.75
RANSAC_REPROJ_THRESH    = 5.0
RANSAC_MIN_INLIERS      = 10
RANSAC_INLIER_RATIO_MIN = 0.30

# ── Revision / shadow ─────────────────────────────────────────────────────
DIFF_THRESHOLD_PX       = 30      # pixel intensity diff for change detection
SHADOW_CHANGE_PCT_MIN   = 0.5     # % page area changed to flag shadow suspect

# ── Verdict colours (UI reference) ────────────────────────────────────────
COLOR_PRIMARY = "#1E293B"
COLOR_ACCENT  = "#2563EB"
COLOR_BG      = "#F8FAFC"
COLOR_CARD    = "#FFFFFF"
COLOR_BORDER  = "#E2E8F0"
COLOR_TEXT    = "#0F172A"
COLOR_MUTED   = "#64748B"
COLOR_SUCCESS = "#15803D"
COLOR_WARNING = "#B45309"
COLOR_ERROR   = "#B91C1C"

# ── Audit log ─────────────────────────────────────────────────────────────
AUDIT_LOG_PATH = os.path.join(LOGS_DIR, "audit_chain.json")
