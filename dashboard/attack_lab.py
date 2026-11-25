"""Page 3 — Attack Simulation Laboratory."""
from __future__ import annotations
import streamlit as st
from dashboard.components import (
    page_header, section_header, verdict_badge,
    status_pill, finding_card, show_image, empty_state
)
from simulation.controlled_scenarios import ALL_SCENARIOS, get_scenario
from core.pipeline import run as run_pipeline


SCENARIO_ICONS = {"A":"✅","B":"💥","C":"👥","D":"🔁","E":"🖼️","F":"📄"}
SCENARIO_COLORS = {
    "A": ("#F0FDF4","#15803D","#86EFAC"),
    "B": ("#FEF2F2","#B91C1C","#FCA5A5"),
    "C": ("#FFFBEB","#92400E","#FCD34D"),
    "D": ("#EFF6FF","#1D4ED8","#BFDBFE"),
    "E": ("#FDF4FF","#7C3AED","#E9D5FF"),
    "F": ("#F8FAFC","#475569","#CBD5E1"),
}


def render() -> None:
    page_header(
        "Attack Simulation Lab",
        "Controlled synthetic scenarios — ground-truth labels are strictly separate from the detector.",
        badge="SIMULATION"
    )

    st.markdown("""
<div style="background:linear-gradient(135deg,#1E293B,#1e3a5f);
  border-radius:10px;padding:0.9rem 1.2rem;margin-bottom:1.2rem;
  display:flex;gap:12px;align-items:center;">
  <span style="font-size:1.5rem;">🧪</span>
  <div>
    <div style="font-weight:700;color:#F8FAFC;font-size:0.9rem;">
      How this lab works
    </div>
    <div style="color:#94A3B8;font-size:0.82rem;margin-top:3px;">
      Select a scenario → Generate synthetic documents → Run the actual detection engine →
      Ground-truth label is revealed <em>after</em> the verdict (never before).
    </div>
  </div>
</div>""", unsafe_allow_html=True)

    # ── Scenario selector cards ────────────────────────────────────────────
    section_header("Select Attack Scenario", "⚗️")

    sel_id = st.session_state.get("selected_scenario", "A")
    cols = st.columns(3)
    for i, s in enumerate(ALL_SCENARIOS):
        bg, fg, border = SCENARIO_COLORS[s.id]
        icon = SCENARIO_ICONS[s.id]
        is_sel = (s.id == sel_id)
        with cols[i % 3]:
            if st.button(
                f"{icon}  {s.name}",
                key=f"sc_{s.id}",
                help=s.description,
            ):
                sel_id = s.id
                st.session_state["selected_scenario"] = s.id
                for k in [f"sim_{s.id}_orig", f"sim_{s.id}_demo",
                          f"sim_{s.id}_gt",   f"sim_{s.id}_result"]:
                    st.session_state.pop(k, None)

    st.session_state["selected_scenario"] = sel_id
    scenario = get_scenario(sel_id)
    if scenario is None:
        st.error("Scenario not found.")
        return

    # Scenario info card
    bg, fg, border = SCENARIO_COLORS[sel_id]
    st.markdown(f"""
<div style="background:{bg};border:1.5px solid {border};border-radius:10px;
  padding:1rem 1.2rem;margin:0.8rem 0;">
  <div style="display:flex;gap:12px;align-items:flex-start;">
    <span style="font-size:2rem;">{SCENARIO_ICONS[sel_id]}</span>
    <div>
      <div style="font-weight:800;color:{fg};font-size:1rem;">{scenario.name}</div>
      <div style="color:#334155;font-size:0.85rem;margin-top:4px;line-height:1.6;">
        {scenario.description}
      </div>
      <div style="margin-top:6px;">
        <span style="background:{border}66;color:{fg};font-size:0.72rem;
          font-weight:700;padding:2px 8px;border-radius:12px;
          text-transform:uppercase;letter-spacing:0.06em;">
          {scenario.category}
        </span>
      </div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

    if st.button("⚗️  Generate Synthetic Scenario"):
        with st.spinner("Generating synthetic documents…"):
            try:
                orig_b, demo_b, gt = scenario.factory()
                st.session_state[f"sim_{sel_id}_orig"] = orig_b
                st.session_state[f"sim_{sel_id}_demo"] = demo_b
                st.session_state[f"sim_{sel_id}_gt"]   = gt
                st.session_state.pop(f"sim_{sel_id}_result", None)
                st.success("Scenario generated — ready for detection.")
            except Exception as exc:
                st.error(f"Generation failed: {exc}")
                return

    orig_b = st.session_state.get(f"sim_{sel_id}_orig")
    demo_b = st.session_state.get(f"sim_{sel_id}_demo")
    if orig_b is None:
        empty_state("Click 'Generate Synthetic Scenario' to create the demo documents.", "⚗️")
        return

    # ── Side-by-side preview ───────────────────────────────────────────────
    section_header("Document Comparison", "🔍")
    from core.pdf_parser import render_page
    import hashlib

    # Scenario-specific explanation banners
    SCENARIO_NOTES = {
        "A": ("✅", "#F0FDF4", "#15803D", "#86EFAC",
              "Both sides are identical — this is a clean, unmodified document. "
              "The detector should return CLEAN."),
        "B": ("💥", "#FEF2F2", "#B91C1C", "#FCA5A5",
              "These documents look IDENTICAL visually — the attack is invisible to the eye. "
              "Only ONE BYTE has been flipped deep in the file. "
              "SHA-256 detects it instantly. This is why cryptographic verification matters."),
        "C": ("👥", "#FFFBEB", "#92400E", "#FCD34D",
              "The original (left) was signed showing $1,000. "
              "The shadow document (right) has a second revision overriding it to $9,000. "
              "The signature stays VALID but the visible amount changed — this is a Shadow Attack."),
        "D": ("🔁", "#EFF6FF", "#1D4ED8", "#BFDBFE",
              "Both images contain near-identical handwriting marks. "
              "ORB feature matching and RANSAC will detect the geometric duplication."),
        "E": ("🖼️", "#FDF4FF", "#7C3AED", "#E9D5FF",
              "The original has a clean gradient region. "
              "The attack document has bytes altered in the image area — ELA residuals reveal this."),
        "F": ("📄", "#F8FAFC", "#475569", "#CBD5E1",
              "An unsigned document. No signature exists to verify. "
              "The detector will return INCONCLUSIVE — absence of a signature is NOT evidence of forgery."),
    }

    icon, bg, fg, border, note = SCENARIO_NOTES.get(sel_id, ("❓","#F8FAFC","#475569","#CBD5E1",""))
    st.markdown(f"""
<div style="background:{bg};border:1.5px solid {border};border-radius:10px;
  padding:0.8rem 1.1rem;margin-bottom:1rem;display:flex;gap:10px;align-items:flex-start;">
  <span style="font-size:1.5rem;flex-shrink:0;">{icon}</span>
  <div style="color:{fg};font-size:0.88rem;line-height:1.6;">{note}</div>
</div>""", unsafe_allow_html=True)

    pc1, pc2 = st.columns(2)
    orig_hash = hashlib.sha256(orig_b).hexdigest()[:16]
    demo_hash = hashlib.sha256(demo_b).hexdigest()[:16]
    hashes_match = orig_hash == demo_hash

    with pc1:
        st.markdown("""<div style="background:#F0FDF4;border:1px solid #86EFAC;
          border-radius:8px;padding:6px 10px;margin-bottom:6px;
          font-size:0.78rem;font-weight:700;color:#15803D;">
          📄 ORIGINAL DOCUMENT</div>""", unsafe_allow_html=True)
        try:
            show_image(render_page(orig_b), f"SHA-256 (prefix): {orig_hash}…")
        except Exception as e:
            st.warning(str(e))
    with pc2:
        badge_color = "#F0FDF4" if hashes_match else "#FEF2F2"
        badge_border = "#86EFAC" if hashes_match else "#FCA5A5"
        badge_fg = "#15803D" if hashes_match else "#B91C1C"
        badge_text = "IDENTICAL FILE" if hashes_match else "DIFFERENT FILE DETECTED"
        st.markdown(f"""<div style="background:{badge_color};border:1px solid {badge_border};
          border-radius:8px;padding:6px 10px;margin-bottom:6px;
          font-size:0.78rem;font-weight:700;color:{badge_fg};">
          {SCENARIO_ICONS[sel_id]} ATTACK DOCUMENT — {badge_text}</div>""",
                    unsafe_allow_html=True)
        try:
            show_image(render_page(demo_b), f"SHA-256 (prefix): {demo_hash}…")
        except Exception as e:
            st.warning(str(e))

    if not hashes_match:
        st.markdown(f"""
<div style="background:#FEF2F2;border:1px solid #FCA5A5;border-radius:8px;
  padding:0.6rem 1rem;margin-top:0.4rem;font-size:0.82rem;color:#7F1D1D;">
  ⚠️ <strong>File hashes differ</strong> —
  Original: <code>{orig_hash}…</code> →
  Attack: <code>{demo_hash}…</code>
</div>""", unsafe_allow_html=True)

    st.markdown("---")
    if st.button("🔬  Run Detection Engine"):
        with st.spinner("Running forensic analysis on scenario document…"):
            result = run_pipeline(demo_b, f"scenario_{sel_id}.pdf")
            st.session_state[f"sim_{sel_id}_result"] = result

    result = st.session_state.get(f"sim_{sel_id}_result")
    if result is None:
        return

    # ── Detection results ─────────────────────────────────────────────────
    section_header("Detection Results", "📊")
    if result.fusion:
        fu = result.fusion
        verdict_badge(fu.verdict.value)
        st.markdown(f"""
<div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:10px;
  padding:0.9rem 1.2rem;margin:0.5rem 0;">
  <div style="font-size:0.88rem;color:#334155;line-height:1.65;">{fu.explanation}</div>
</div>""", unsafe_allow_html=True)

        # Reveal ground truth AFTER verdict
        gt = st.session_state.get(f"sim_{sel_id}_gt", "")
        with st.expander("🏷️  Reveal ground-truth label (evaluation only)"):
            match = (gt.replace("_"," ") in fu.verdict.value or
                     fu.verdict.value in gt.replace("_"," ") or
                     gt == fu.verdict.value)
            color = "#15803D" if match else "#B91C1C"
            st.markdown(f"""
<div style="display:flex;gap:10px;align-items:center;">
  <div style="background:#F0FDF4;border:1px solid #86EFAC;border-radius:8px;
    padding:0.6rem 1rem;">
    <div style="font-size:0.72rem;color:#64748B;font-weight:700;
      text-transform:uppercase;letter-spacing:0.06em;">Ground Truth Label</div>
    <div style="font-size:1.1rem;font-weight:800;color:{color};margin-top:4px;">
      {gt}
    </div>
  </div>
  <div style="color:#64748B;font-size:0.82rem;max-width:400px;line-height:1.5;">
    This label was stored independently and was <strong>never passed</strong> to
    the detection engine. The detector produces its verdict from document content only.
  </div>
</div>""", unsafe_allow_html=True)

        if fu.findings:
            section_header("Findings", "🚩")
            for f in fu.findings:
                finding_card(f.code, f.severity.value, f.title, f.description)

    # ── Evidence tabs ─────────────────────────────────────────────────────
    section_header("Evidence Detail", "🔎")
    tab_crypto, tab_rev, tab_loc, tab_ela, tab_orb = st.tabs([
        "🔐 Cryptographic", "📋 Revision", "✍️ Localisation", "🖼️ ELA", "🎯 ORB/RANSAC"
    ])

    with tab_crypto:
        if result.crypto and result.crypto.total_sigs > 0:
            for r in result.crypto.results:
                st.markdown(f"**Field:** `{r.field_name}`")
                ca, cb, cc = st.columns(3)
                with ca:
                    status_pill("Byte integrity", r.integrity_ok)
                    st.markdown("")
                with cb:
                    status_pill("Math valid", r.math_valid)
                    st.markdown("")
                with cc:
                    status_pill("Cert trusted", r.cert_trusted)
                    st.markdown("")
                st.caption(result.crypto.summary)
                if r.cert_info and r.cert_info.is_test_cert:
                    st.warning("⚠️ TEST certificate — not a trusted certificate authority")
        else:
            st.info("No cryptographic signatures in this document.")

    with tab_rev:
        if result.revision:
            rv = result.revision
            m1,m2,m3 = st.columns(3)
            m1.metric("Revisions", len(rv.revisions))
            m2.metric("Shadow suspect", "Yes" if rv.shadow_suspect else "No")
            m3.metric("Changed area", f"{rv.changed_area_pct:.1f}%")
            if rv.signed_rev_image and rv.current_image:
                i1,i2 = st.columns(2)
                with i1: show_image(rv.signed_rev_image, "Signed revision")
                with i2: show_image(rv.current_image,    "Current revision")
            if rv.diff_image:
                show_image(rv.diff_image, "Pixel diff")
            st.caption(rv.summary)
        else:
            st.info("Revision analysis not applicable.")

    with tab_loc:
        if result.localization:
            show_image(result.localization.annotated, "Candidates (blue boxes)")
            st.caption(f"{len(result.localization.candidates)} candidate(s) detected")
        else:
            st.info("Localisation not performed.")

    with tab_ela:
        if result.ela and result.ela.error is None:
            el = result.ela
            ec1,ec2 = st.columns(2)
            with ec1: show_image(el.original,  "Original")
            with ec2: show_image(el.amplified, "Amplified ELA")
            st.metric("Mean residual", f"{el.mean_residual:.2f}")
            st.caption(el.finding)
        else:
            st.info("ELA not performed or not applicable.")

    with tab_orb:
        if result.ransac:
            rs = result.ransac
            show_image(rs.inlier_vis, "Green = inliers | Red = outliers")
            o1,o2 = st.columns(2)
            o1.metric("Inliers",      rs.inlier_count)
            o2.metric("Inlier ratio", f"{rs.inlier_ratio:.0%}")
            st.caption(rs.summary)
        else:
            st.info("ORB/RANSAC requires 2+ signature candidates.")
