"""
Reusable UI components — premium 5-star design.
"""
from __future__ import annotations
import base64, io
from typing import Optional
import streamlit as st
from PIL import Image

C_PRIMARY = "#1E293B"
C_ACCENT  = "#2563EB"
C_BG      = "#F8FAFC"
C_CARD    = "#FFFFFF"
C_BORDER  = "#E2E8F0"
C_TEXT    = "#0F172A"
C_MUTED   = "#64748B"
C_SUCCESS = "#15803D"
C_WARNING = "#B45309"
C_ERROR   = "#B91C1C"


def inject_css() -> None:
    st.markdown(r"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ── Reset & Base ─────────────────────────────────────────────────── */
html, body, [class*="css"] {
    font-family: 'Inter', 'Segoe UI', system-ui, sans-serif !important;
    color: #0F172A;
}
.stApp { background: #F1F5F9 !important; }
.block-container {
    padding: 1.5rem 2rem 2rem !important;
    max-width: 1280px !important;
}

/* ── Sidebar ─────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0F172A 0%, #1E293B 100%) !important;
    border-right: 1px solid #334155 !important;
    min-width: 240px !important;
}
[data-testid="stSidebar"] > div:first-child {
    padding: 1rem 0.8rem !important;
}
[data-testid="stSidebar"] * { color: #CBD5E1 !important; }
[data-testid="stSidebar"] .stRadio > label { display: none !important; }
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] {
    gap: 2px !important;
    display: flex !important;
    flex-direction: column !important;
}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label {
    display: flex !important;
    align-items: center !important;
    padding: 0.5rem 0.75rem !important;
    border-radius: 8px !important;
    cursor: pointer !important;
    transition: background 0.15s !important;
    font-size: 0.875rem !important;
    font-weight: 500 !important;
    color: #94A3B8 !important;
    border: none !important;
    margin: 1px 0 !important;
}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label:hover {
    background: rgba(37,99,235,0.15) !important;
    color: #E2E8F0 !important;
}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label[data-checked="true"],
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label[aria-checked="true"] {
    background: rgba(37,99,235,0.25) !important;
    color: #60A5FA !important;
    font-weight: 600 !important;
}
[data-testid="stSidebar"] .stRadio span[data-baseweb="radio"] { display: none !important; }

/* ── Top header bar ─────────────────────────────────────────────── */
.sg-topbar {
    background: linear-gradient(135deg, #1E293B 0%, #1e3a5f 100%);
    border-radius: 12px;
    padding: 1.2rem 1.8rem;
    margin-bottom: 1.5rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    box-shadow: 0 4px 24px rgba(0,0,0,0.12);
}
.sg-topbar-title {
    font-size: 1.6rem; font-weight: 800;
    color: #F8FAFC; letter-spacing: -0.02em;
}
.sg-topbar-sub {
    font-size: 0.82rem; color: #94A3B8; margin-top: 2px;
}
.sg-topbar-badge {
    background: rgba(37,99,235,0.3);
    border: 1px solid rgba(37,99,235,0.5);
    color: #93C5FD;
    font-size: 0.72rem; font-weight: 600;
    padding: 4px 10px; border-radius: 20px;
    letter-spacing: 0.05em;
}

/* ── Cards ───────────────────────────────────────────────────────── */
.sg-card {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    transition: box-shadow 0.2s;
}
.sg-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.08); }

/* ── Metric cards ────────────────────────────────────────────────── */
.sg-metric-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
    gap: 0.75rem;
    margin: 0.75rem 0;
}
.sg-metric-card {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    padding: 1rem;
    text-align: center;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.sg-metric-label {
    font-size: 0.7rem; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.06em;
    color: #64748B; margin-bottom: 6px;
}
.sg-metric-value {
    font-size: 1.5rem; font-weight: 800; color: #0F172A;
    line-height: 1.1;
}
.sg-metric-sub {
    font-size: 0.72rem; color: #94A3B8; margin-top: 3px;
}

/* ── Section headers ─────────────────────────────────────────────── */
.sg-section {
    display: flex; align-items: center; gap: 10px;
    margin: 1.4rem 0 0.8rem;
}
.sg-section-bar {
    width: 4px; height: 20px;
    background: linear-gradient(180deg, #2563EB, #60A5FA);
    border-radius: 2px; flex-shrink: 0;
}
.sg-section-text {
    font-size: 1rem; font-weight: 700; color: #1E293B;
}

/* ── Verdict banners ─────────────────────────────────────────────── */
.verdict-banner {
    border-radius: 10px; padding: 1rem 1.5rem;
    display: flex; align-items: center; gap: 12px;
    margin: 0.75rem 0; font-weight: 700; font-size: 1.05rem;
}
.verdict-TAMPERING_DETECTED {
    background: linear-gradient(135deg, #FEF2F2, #FFF5F5);
    border: 1.5px solid #FCA5A5; color: #B91C1C;
}
.verdict-REVIEW_REQUIRED {
    background: linear-gradient(135deg, #FFFBEB, #FFFEF5);
    border: 1.5px solid #FCD34D; color: #92400E;
}
.verdict-CLEAN {
    background: linear-gradient(135deg, #F0FDF4, #F7FFF9);
    border: 1.5px solid #86EFAC; color: #15803D;
}
.verdict-INCONCLUSIVE {
    background: linear-gradient(135deg, #F8FAFC, #F1F5F9);
    border: 1.5px solid #CBD5E1; color: #475569;
}
.verdict-UNSUPPORTED {
    background: #F8FAFC; border: 1.5px solid #CBD5E1; color: #475569;
}
.verdict-icon { font-size: 1.5rem; }

/* ── Status pills ────────────────────────────────────────────────── */
.sg-pill {
    display: inline-flex; align-items: center; gap: 5px;
    padding: 3px 10px; border-radius: 20px;
    font-size: 0.78rem; font-weight: 600;
    margin: 2px;
}
.sg-pill-pass {
    background: #F0FDF4; color: #15803D; border: 1px solid #86EFAC;
}
.sg-pill-fail {
    background: #FEF2F2; color: #B91C1C; border: 1px solid #FCA5A5;
}
.sg-pill-unknown {
    background: #F8FAFC; color: #64748B; border: 1px solid #CBD5E1;
}

/* ── Finding cards ───────────────────────────────────────────────── */
.finding-card {
    border-radius: 8px; padding: 0.75rem 1rem;
    margin: 0.4rem 0; border-left: 4px solid;
}
.finding-CRITICAL {
    background: #FEF2F2; border-color: #EF4444;
    color: #7F1D1D;
}
.finding-HIGH {
    background: #FFFBEB; border-color: #F59E0B;
    color: #78350F;
}
.finding-MEDIUM {
    background: #EFF6FF; border-color: #3B82F6;
    color: #1E3A5F;
}
.finding-LOW {
    background: #F8FAFC; border-color: #94A3B8;
    color: #334155;
}
.finding-INFO {
    background: #F8FAFC; border-color: #CBD5E1;
    color: #475569;
}
.finding-title {
    font-weight: 700; font-size: 0.88rem; margin-bottom: 3px;
}
.finding-desc { font-size: 0.82rem; opacity: 0.9; }

/* ── Algorithm pipeline steps ────────────────────────────────────── */
.pipeline-step {
    display: flex; align-items: center; gap: 10px;
    padding: 8px 12px; border-radius: 8px;
    margin: 3px 0; transition: background 0.15s;
}
.pipeline-step:hover { background: #F1F5F9; }
.pipeline-icon {
    width: 32px; height: 32px; border-radius: 8px;
    background: linear-gradient(135deg, #2563EB, #3B82F6);
    display: flex; align-items: center; justify-content: center;
    font-size: 1rem; flex-shrink: 0;
}
.pipeline-name { font-size: 0.85rem; font-weight: 500; color: #1E293B; }

/* ── Image viewer ────────────────────────────────────────────────── */
.sg-img-frame {
    border: 1px solid #E2E8F0; border-radius: 10px;
    overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.sg-img-caption {
    background: #F8FAFC; padding: 6px 10px;
    font-size: 0.75rem; color: #64748B;
    border-top: 1px solid #E2E8F0; text-align: center;
}

/* ── Tables ──────────────────────────────────────────────────────── */
.sg-table { width: 100%; border-collapse: collapse; }
.sg-table th {
    background: #F1F5F9; color: #475569;
    font-size: 0.72rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.05em;
    padding: 8px 12px; text-align: left;
    border-bottom: 2px solid #E2E8F0;
}
.sg-table td {
    padding: 8px 12px; font-size: 0.85rem;
    border-bottom: 1px solid #F1F5F9; color: #1E293B;
}
.sg-table tr:hover td { background: #F8FAFC; }

/* ── Buttons ─────────────────────────────────────────────────────── */
.stButton > button {
    background: linear-gradient(135deg, #2563EB, #3B82F6) !important;
    color: white !important; border: none !important;
    border-radius: 8px !important; font-weight: 600 !important;
    font-size: 0.9rem !important;
    padding: 0.5rem 1.5rem !important;
    box-shadow: 0 2px 8px rgba(37,99,235,0.3) !important;
    transition: all 0.2s !important;
    letter-spacing: 0.01em !important;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #1D4ED8, #2563EB) !important;
    box-shadow: 0 4px 16px rgba(37,99,235,0.4) !important;
    transform: translateY(-1px) !important;
}
.stButton > button:active { transform: translateY(0) !important; }

/* ── Download buttons ────────────────────────────────────────────── */
.stDownloadButton > button {
    background: #FFFFFF !important; color: #2563EB !important;
    border: 1.5px solid #2563EB !important;
    border-radius: 8px !important; font-weight: 600 !important;
}
.stDownloadButton > button:hover {
    background: #EFF6FF !important;
}

/* ── Expanders ───────────────────────────────────────────────────── */
[data-testid="stExpander"] {
    background: #FFFFFF !important;
    border: 1px solid #E2E8F0 !important;
    border-radius: 10px !important;
    margin-bottom: 0.6rem !important;
    overflow: hidden !important;
}
[data-testid="stExpander"] > div:first-child {
    background: #F8FAFC !important;
    padding: 0.6rem 1rem !important;
}
details summary {
    font-weight: 600 !important; color: #1E293B !important;
    font-size: 0.9rem !important;
}

/* ── Metrics ─────────────────────────────────────────────────────── */
[data-testid="metric-container"] {
    background: #FFFFFF !important;
    border: 1px solid #E2E8F0 !important;
    border-radius: 10px !important;
    padding: 0.75rem 1rem !important;
}
[data-testid="stMetricValue"] {
    font-size: 1.4rem !important; font-weight: 800 !important;
}

/* ── Alerts / info boxes ─────────────────────────────────────────── */
.stAlert {
    border-radius: 8px !important;
    border-left-width: 4px !important;
}

/* ── File uploader ───────────────────────────────────────────────── */
[data-testid="stFileUploader"] {
    border: 2px dashed #CBD5E1 !important;
    border-radius: 12px !important;
    background: #F8FAFC !important;
    padding: 1rem !important;
    transition: border-color 0.2s !important;
}
[data-testid="stFileUploader"]:hover {
    border-color: #2563EB !important;
    background: #EFF6FF !important;
}

/* ── Tabs ────────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    background: #F1F5F9 !important;
    border-radius: 10px !important;
    padding: 4px !important;
    gap: 4px !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 7px !important;
    font-weight: 600 !important; font-size: 0.85rem !important;
    color: #64748B !important;
    background: transparent !important;
}
.stTabs [aria-selected="true"] {
    background: #FFFFFF !important;
    color: #2563EB !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.08) !important;
}

/* ── Scrollbar ───────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #F1F5F9; }
::-webkit-scrollbar-thumb {
    background: #CBD5E1; border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover { background: #94A3B8; }

/* ── Hide Streamlit chrome ───────────────────────────────────────── */
#MainMenu, footer, header { visibility: hidden !important; }
.stDeployButton { display: none !important; }
</style>
""", unsafe_allow_html=True)


# ── Component helpers ──────────────────────────────────────────────────────

def page_header(title: str, subtitle: str = "", badge: str = "") -> None:
    badge_html = (
        f'<span class="sg-topbar-badge">{badge}</span>' if badge else
        '<span class="sg-topbar-badge">FORENSIC TOOL</span>'
    )
    st.markdown(f"""
<div class="sg-topbar">
  <div>
    <div class="sg-topbar-title">🔐 {title}</div>
    {"<div class='sg-topbar-sub'>" + subtitle + "</div>" if subtitle else ""}
  </div>
  {badge_html}
</div>""", unsafe_allow_html=True)


def section_header(text: str, icon: str = "") -> None:
    icon_html = f'<span style="font-size:1rem">{icon}</span>' if icon else ""
    st.markdown(f"""
<div class="sg-section">
  <div class="sg-section-bar"></div>
  {icon_html}
  <div class="sg-section-text">{text}</div>
</div>""", unsafe_allow_html=True)


def verdict_badge(verdict_value: str) -> None:
    icons = {
        "TAMPERING DETECTED":  ("🚨", "TAMPERING_DETECTED"),
        "TAMPERING_DETECTED":  ("🚨", "TAMPERING_DETECTED"),
        "REVIEW REQUIRED":     ("⚠️", "REVIEW_REQUIRED"),
        "REVIEW_REQUIRED":     ("⚠️", "REVIEW_REQUIRED"),
        "CLEAN":               ("✅", "CLEAN"),
        "INCONCLUSIVE":        ("❓", "INCONCLUSIVE"),
        "UNSUPPORTED":         ("⛔", "UNSUPPORTED"),
    }
    icon, css_key = icons.get(verdict_value, ("❓", "INCONCLUSIVE"))
    st.markdown(f"""
<div class="verdict-banner verdict-{css_key}">
  <span class="verdict-icon">{icon}</span>
  <span>{verdict_value}</span>
</div>""", unsafe_allow_html=True)


def status_pill(label: str, ok) -> None:
    if ok is True:
        css, icon = "sg-pill-pass", "✓"
    elif ok is False:
        css, icon = "sg-pill-fail", "✗"
    else:
        css, icon = "sg-pill-unknown", "–"
    st.markdown(
        f'<span class="sg-pill {css}">{icon} {label}</span>',
        unsafe_allow_html=True)


def finding_card(code: str, severity: str, title: str, description: str) -> None:
    sev_labels = {
        "CRITICAL": "🔴 CRITICAL",
        "HIGH":     "🟠 HIGH",
        "MEDIUM":   "🔵 MEDIUM",
        "LOW":      "⚪ LOW",
        "INFO":     "ℹ️ INFO",
    }
    sev_label = sev_labels.get(severity, severity)
    st.markdown(f"""
<div class="finding-card finding-{severity}">
  <div class="finding-title">{sev_label} &nbsp;·&nbsp; {code} &nbsp;—&nbsp; {title}</div>
  <div class="finding-desc">{description}</div>
</div>""", unsafe_allow_html=True)


def metric_row(*items) -> None:
    """items = list of (label, value, sub) tuples"""
    cards = ""
    for item in items:
        label = item[0]
        value = item[1]
        sub   = item[2] if len(item) > 2 else ""
        cards += f"""
<div class="sg-metric-card">
  <div class="sg-metric-label">{label}</div>
  <div class="sg-metric-value">{value}</div>
  {"<div class='sg-metric-sub'>" + sub + "</div>" if sub else ""}
</div>"""
    st.markdown(
        f'<div class="sg-metric-grid">{cards}</div>',
        unsafe_allow_html=True)


def card(content_html: str) -> None:
    st.markdown(
        f'<div class="sg-card">{content_html}</div>',
        unsafe_allow_html=True)


def show_image(img: Image.Image, caption: str = "",
               width: Optional[int] = None) -> None:
    if width:
        st.image(img, caption=caption, width=width)
    else:
        st.image(img, caption=caption, width="stretch")


def empty_state(message: str, icon: str = "📂") -> None:
    st.markdown(f"""
<div style="text-align:center; padding:3rem 2rem;
  background:#FFFFFF; border:2px dashed #E2E8F0;
  border-radius:12px; color:#94A3B8;">
  <div style="font-size:2.5rem; margin-bottom:0.75rem">{icon}</div>
  <div style="font-size:0.95rem; color:#64748B; font-weight:500">{message}</div>
</div>""", unsafe_allow_html=True)


def download_button(label: str, data: bytes,
                    filename: str, mime: str) -> None:
    st.download_button(label=label, data=data,
                       file_name=filename, mime=mime)
