"""Page 1 — Project Overview."""
import streamlit as st
from dashboard.components import page_header, section_header, card


def render() -> None:
    page_header(
        "SignGuard",
        "Integrated Cryptographic-Forensic Framework for Signature Forgery & Shadow Attack Detection",
        badge="RESEARCH PROJECT"
    )

    # ── Hero stats row ─────────────────────────────────────────────────────
    st.markdown("""
<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;margin-bottom:1.5rem;">
  <div class="sg-metric-card" style="border-top:3px solid #2563EB;">
    <div class="sg-metric-label">Analysis Modules</div>
    <div class="sg-metric-value" style="color:#2563EB;">12</div>
    <div class="sg-metric-sub">Fully integrated</div>
  </div>
  <div class="sg-metric-card" style="border-top:3px solid #15803D;">
    <div class="sg-metric-label">Attack Scenarios</div>
    <div class="sg-metric-value" style="color:#15803D;">6</div>
    <div class="sg-metric-sub">Controlled demos</div>
  </div>
  <div class="sg-metric-card" style="border-top:3px solid #B45309;">
    <div class="sg-metric-label">Algorithms</div>
    <div class="sg-metric-value" style="color:#B45309;">13</div>
    <div class="sg-metric-sub">No ML required</div>
  </div>
  <div class="sg-metric-card" style="border-top:3px solid #7C3AED;">
    <div class="sg-metric-label">Test Cases</div>
    <div class="sg-metric-value" style="color:#7C3AED;">Security</div>
    <div class="sg-metric-sub">Outcome-based tests</div>
  </div>
</div>
""", unsafe_allow_html=True)

    # ── Two-column main content ────────────────────────────────────────────
    col_left, col_right = st.columns([3, 2], gap="large")

    with col_left:
        section_header("Problem Statement", "🎯")
        st.markdown("""
<div class="sg-card">
<p style="color:#334155;font-size:0.92rem;line-height:1.75;margin:0;">
Digital signatures are fundamental to document authenticity and non-repudiation.
However, several attack classes undermine their trustworthiness even when the
<strong>mathematical signature appears valid</strong>:
</p>
<div style="margin-top:0.9rem;display:flex;flex-direction:column;gap:0.6rem;">
  <div style="display:flex;gap:10px;align-items:flex-start;">
    <span style="background:#FEF2F2;color:#B91C1C;border-radius:6px;
      padding:3px 8px;font-size:0.78rem;font-weight:700;flex-shrink:0;
      margin-top:1px;">CRITICAL</span>
    <div>
      <strong style="color:#1E293B;">Signed-byte tampering</strong>
      <span style="color:#64748B;font-size:0.85rem;"> — Raw modification of signed bytes, invalidating the SHA-256 digest.</span>
    </div>
  </div>
  <div style="display:flex;gap:10px;align-items:flex-start;">
    <span style="background:#FFFBEB;color:#B45309;border-radius:6px;
      padding:3px 8px;font-size:0.78rem;font-weight:700;flex-shrink:0;
      margin-top:1px;">HIGH</span>
    <div>
      <strong style="color:#1E293B;">PDF shadow attacks</strong>
      <span style="color:#64748B;font-size:0.85rem;"> — Different visible content shown to signer vs. later readers via incremental updates.</span>
    </div>
  </div>
  <div style="display:flex;gap:10px;align-items:flex-start;">
    <span style="background:#EFF6FF;color:#1D4ED8;border-radius:6px;
      padding:3px 8px;font-size:0.78rem;font-weight:700;flex-shrink:0;
      margin-top:1px;">MEDIUM</span>
    <div>
      <strong style="color:#1E293B;">Visual signature forgery</strong>
      <span style="color:#64748B;font-size:0.85rem;"> — Duplicating or manipulating rasterised handwriting without breaking the crypto signature.</span>
    </div>
  </div>
  <div style="display:flex;gap:10px;align-items:flex-start;">
    <span style="background:#F8FAFC;color:#475569;border-radius:6px;
      padding:3px 8px;font-size:0.78rem;font-weight:700;flex-shrink:0;
      margin-top:1px;">RISK</span>
    <div>
      <strong style="color:#1E293B;">Certificate confusion</strong>
      <span style="color:#64748B;font-size:0.85rem;"> — Treating a self-signed certificate as proof of signer identity.</span>
    </div>
  </div>
</div>
</div>""", unsafe_allow_html=True)

        section_header("Research Gap", "🔬")
        st.markdown("""
<div class="sg-card">
<p style="color:#334155;font-size:0.88rem;line-height:1.7;margin:0 0 0.8rem;">
This project explores integrating five complementary layers of PDF analysis:
</p>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:0.5rem;">
  <div style="background:#F0FDF4;border:1px solid #86EFAC;border-radius:8px;padding:0.6rem 0.8rem;">
    <div style="font-weight:700;color:#15803D;font-size:0.82rem;">1. Cryptographic</div>
    <div style="color:#334155;font-size:0.78rem;margin-top:2px;">ByteRange + CMS + X.509</div>
  </div>
  <div style="background:#EFF6FF;border:1px solid #BFDBFE;border-radius:8px;padding:0.6rem 0.8rem;">
    <div style="font-weight:700;color:#1D4ED8;font-size:0.82rem;">2. PDF Structure</div>
    <div style="color:#334155;font-size:0.78rem;margin-top:2px;">Revision timeline + visual diff</div>
  </div>
  <div style="background:#FFF7ED;border:1px solid #FED7AA;border-radius:8px;padding:0.6rem 0.8rem;">
    <div style="font-weight:700;color:#C2410C;font-size:0.82rem;">3. Localisation</div>
    <div style="color:#334155;font-size:0.78rem;margin-top:2px;">Adaptive threshold + morphology</div>
  </div>
  <div style="background:#FDF4FF;border:1px solid #E9D5FF;border-radius:8px;padding:0.6rem 0.8rem;">
    <div style="font-weight:700;color:#7C3AED;font-size:0.82rem;">4. ELA</div>
    <div style="color:#334155;font-size:0.78rem;margin-top:2px;">JPEG residual analysis</div>
  </div>
  <div style="background:#FFFBEB;border:1px solid #FCD34D;border-radius:8px;padding:0.6rem 0.8rem;grid-column:1/-1;">
    <div style="font-weight:700;color:#92400E;font-size:0.82rem;">5. ORB + RANSAC</div>
    <div style="color:#334155;font-size:0.78rem;margin-top:2px;">Copy-move / duplication detection with geometric verification</div>
  </div>
</div>
</div>""", unsafe_allow_html=True)

        section_header("Information Security Principles", "🛡️")
        col_a, col_b = st.columns(2)
        with col_a:
            card("""<div style="display:flex;gap:10px;align-items:flex-start;">
<span style="font-size:1.5rem;">🔒</span>
<div><strong style="color:#1E293B;">Integrity</strong>
<p style="color:#64748B;font-size:0.82rem;margin:4px 0 0;">SHA-256 file hashing and ByteRange validation confirm signed bytes are unaltered.</p></div></div>""")
            card("""<div style="display:flex;gap:10px;align-items:flex-start;">
<span style="font-size:1.5rem;">📜</span>
<div><strong style="color:#1E293B;">Non-repudiation</strong>
<p style="color:#64748B;font-size:0.82rem;margin:4px 0 0;">Signature and certificate inspection supports (but does not guarantee) signer binding.</p></div></div>""")
        with col_b:
            card("""<div style="display:flex;gap:10px;align-items:flex-start;">
<span style="font-size:1.5rem;">✅</span>
<div><strong style="color:#1E293B;">Authenticity</strong>
<p style="color:#64748B;font-size:0.82rem;margin:4px 0 0;">Multi-layer cross-validation: crypto + revision history + image forensics.</p></div></div>""")
            card("""<div style="display:flex;gap:10px;align-items:flex-start;">
<span style="font-size:1.5rem;">📋</span>
<div><strong style="color:#1E293B;">Accountability</strong>
<p style="color:#64748B;font-size:0.82rem;margin:4px 0 0;">Hash-chained audit log provides tamper-evident verification history.</p></div></div>""")

    with col_right:
        section_header("Analysis Pipeline", "⚡")
        steps = [
            ("📄", "PDF Input & Validation",       "#2563EB"),
            ("🔍", "Signature Classification",      "#0891B2"),
            ("🔐", "Cryptographic Verification",   "#7C3AED"),
            ("📋", "Revision Analysis",             "#B45309"),
            ("✍️", "Signature Localisation",        "#15803D"),
            ("🖼️", "ELA Forensics",                 "#B91C1C"),
            ("🎯", "ORB / RANSAC Matching",         "#0F766E"),
            ("⚖️", "Evidence Fusion",               "#1D4ED8"),
            ("📊", "Verdict & Report",              "#15803D"),
        ]
        for i, (icon, name, color) in enumerate(steps):
            connector = (
                f'<div style="margin-left:16px;width:2px;height:8px;'
                f'background:linear-gradient({color},{steps[i+1][2] if i+1 < len(steps) else color});'
                f'opacity:0.4;"></div>' if i < len(steps) - 1 else ""
            )
            st.markdown(f"""
<div style="display:flex;align-items:center;gap:10px;
  background:#FFFFFF;border:1px solid #E2E8F0;border-radius:9px;
  padding:0.6rem 0.9rem;margin:3px 0;
  box-shadow:0 1px 3px rgba(0,0,0,0.04);">
  <div style="width:30px;height:30px;border-radius:7px;
    background:linear-gradient(135deg,{color}22,{color}44);
    border:1.5px solid {color}44;
    display:flex;align-items:center;justify-content:center;
    font-size:0.9rem;flex-shrink:0;">{icon}</div>
  <div>
    <div style="font-size:0.82rem;font-weight:600;color:#1E293B;">{name}</div>
    <div style="font-size:0.68rem;color:#94A3B8;">Stage {i+1}</div>
  </div>
</div>
{connector}""", unsafe_allow_html=True)

        st.markdown("<div style='margin-top:1.2rem;'></div>", unsafe_allow_html=True)
        section_header("Algorithm Layers", "🧮")

        for layer, algos, color in [
            ("Cryptographic", ["SHA-256 digest","CMS/PKCS#7 parsing","X.509 inspection","ByteRange coverage"], "#2563EB"),
            ("PDF Structure", ["%%EOF boundary detection","Incremental update scan","Pixel-level visual diff","Change bounding boxes"], "#B45309"),
            ("Image Forensics", ["Adaptive thresholding","Connected components","JPEG ELA residuals","ORB + RANSAC homography"], "#15803D"),
        ]:
            st.markdown(f"""
<div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:10px;
  padding:0.9rem 1rem;margin-bottom:0.6rem;">
  <div style="font-weight:700;color:{color};font-size:0.82rem;
    text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.5rem;">
    {layer}
  </div>
  {"".join(f'<div style="font-size:0.8rem;color:#475569;padding:2px 0;display:flex;align-items:center;gap:6px;"><span style="color:{color};font-size:0.6rem;">▶</span>{a}</div>' for a in algos)}
</div>""", unsafe_allow_html=True)

    # ── CTA ───────────────────────────────────────────────────────────────
    st.markdown("""
<div style="background:linear-gradient(135deg,#1E293B,#1e3a5f);
  border-radius:12px;padding:1.5rem 2rem;margin-top:1.5rem;
  display:flex;align-items:center;justify-content:space-between;
  box-shadow:0 4px 20px rgba(0,0,0,0.12);">
  <div>
    <div style="font-size:1.1rem;font-weight:700;color:#F8FAFC;">
      Ready to analyse a document?
    </div>
    <div style="font-size:0.85rem;color:#94A3B8;margin-top:4px;">
      Upload any PDF on the Document Analysis page, or explore controlled scenarios in the Attack Simulation Lab.
    </div>
  </div>
  <div style="color:#60A5FA;font-size:1.8rem;flex-shrink:0;">→</div>
</div>""", unsafe_allow_html=True)
