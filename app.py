"""SignGuard — Streamlit entry point.  Launch:  streamlit run app.py"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st

st.set_page_config(
    page_title="SignGuard — Document Forensics",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Inject base CSS early ──────────────────────────────────────────────────
from dashboard.components import inject_css
inject_css()

# ── Page map ───────────────────────────────────────────────────────────────
PAGES = {
    "🏠  Overview":                  "overview",
    "📄  Document Analysis":         "document_analysis",
    "⚗️  Attack Simulation Lab":     "attack_lab",
    "🔬  Algorithm Visualizations":  "forensic_visualization",
    "📊  Evaluation":                "evaluation",
    "📋  Reports & Audit":           "reports",
    "🎓  Presentation Mode":         "presentation",
}

# ── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    # Logo + brand
    st.markdown("""
<div style="padding:1.2rem 0.5rem 1rem;">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;">
    <div style="width:36px;height:36px;background:linear-gradient(135deg,#2563EB,#3B82F6);
      border-radius:9px;display:flex;align-items:center;justify-content:center;
      font-size:1.2rem;flex-shrink:0;">🔐</div>
    <div>
      <div style="font-size:1.1rem;font-weight:800;color:#F8FAFC;
        letter-spacing:-0.01em;">SignGuard</div>
      <div style="font-size:0.68rem;color:#64748B;margin-top:1px;">
        Document Forensics</div>
    </div>
  </div>
</div>
<div style="height:1px;background:linear-gradient(90deg,transparent,#334155,transparent);
  margin:0 0 0.8rem;"></div>
<div style="font-size:0.68rem;font-weight:700;text-transform:uppercase;
  letter-spacing:0.1em;color:#475569;padding:0 0.5rem;margin-bottom:0.4rem;">
  Navigation
</div>""", unsafe_allow_html=True)

    page_key = st.radio(
        "Navigation",
        list(PAGES.keys()),
        label_visibility="collapsed",
    )

    st.markdown("""
<div style="height:1px;background:linear-gradient(90deg,transparent,#334155,transparent);
  margin:1rem 0;"></div>
<div style="padding:0 0.5rem;">
  <div style="font-size:0.72rem;color:#475569;line-height:1.8;">
    <div style="display:flex;align-items:center;gap:6px;margin-bottom:3px;">
      <span style="color:#15803D;font-size:0.65rem;">●</span>
      <span>Local — no internet required</span>
    </div>
    <div style="display:flex;align-items:center;gap:6px;margin-bottom:3px;">
      <span style="color:#2563EB;font-size:0.65rem;">●</span>
      <span>No GPU or API key needed</span>
    </div>
    <div style="display:flex;align-items:center;gap:6px;">
      <span style="color:#94A3B8;font-size:0.65rem;">●</span>
      <span>Educational / research use</span>
    </div>
  </div>
  <div style="margin-top:1rem;font-size:0.68rem;color:#334155;
    background:rgba(37,99,235,0.1);border:1px solid rgba(37,99,235,0.2);
    border-radius:6px;padding:6px 8px;">
    v1.0 &nbsp;·&nbsp; Python + Streamlit
  </div>
</div>""", unsafe_allow_html=True)

# ── Route ──────────────────────────────────────────────────────────────────
module_name = PAGES[page_key]

if module_name == "overview":
    from dashboard.overview import render
elif module_name == "document_analysis":
    from dashboard.document_analysis import render
elif module_name == "attack_lab":
    from dashboard.attack_lab import render
elif module_name == "forensic_visualization":
    from dashboard.forensic_visualization import render
elif module_name == "evaluation":
    from dashboard.evaluation import render
elif module_name == "reports":
    from dashboard.reports import render
elif module_name == "presentation":
    from dashboard.presentation import render
else:
    def render():
        st.error("Page not found.")

render()
