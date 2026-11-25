"""Page 7 — Presentation Mode (faculty demo with step navigation)."""
from __future__ import annotations
import streamlit as st
from dashboard.components import (
    page_header, section_header, verdict_badge, show_image, empty_state, status_pill
)
from simulation.controlled_scenarios import ALL_SCENARIOS, get_scenario
from core.pipeline import run as run_pipeline

STEPS = [
    ("1", "Upload Document"),
    ("2", "Baseline Verification"),
    ("3", "Attack Demonstration"),
    ("4", "Algorithm Evidence"),
    ("5", "Final Verdict & Report"),
]


def _step_indicator(current: int) -> None:
    """Draw a horizontal step progress bar."""
    items = ""
    for i, (num, label) in enumerate(STEPS):
        active  = (i == current)
        done    = (i < current)
        bg      = "#2563EB" if active else ("#1E293B" if done else "#E2E8F0")
        fg      = "#FFFFFF" if (active or done) else "#94A3B8"
        txt_col = "#1E293B" if active else ("#475569" if done else "#94A3B8")
        items += (
            f'<div style="display:flex;flex-direction:column;align-items:center;'
            f'flex:1;min-width:80px;">'
            f'<div style="width:28px;height:28px;border-radius:50%;'
            f'background:{bg};color:{fg};font-size:0.78rem;font-weight:700;'
            f'display:flex;align-items:center;justify-content:center;">{num}</div>'
            f'<div style="font-size:0.68rem;color:{txt_col};margin-top:4px;'
            f'text-align:center;font-weight:{"700" if active else "400"};">'
            f'{label}</div>'
            f'</div>'
        )
        if i < len(STEPS) - 1:
            line_color = "#2563EB" if done else "#E2E8F0"
            items += (
                f'<div style="flex:0.5;height:2px;background:{line_color};'
                f'margin-top:14px;"></div>'
            )
    st.markdown(
        f'<div style="display:flex;align-items:flex-start;padding:1rem 0 1.5rem;">'
        f'{items}</div>',
        unsafe_allow_html=True)


def render() -> None:
    # Hide sidebar for cleaner projection view
    st.markdown("""
<style>
[data-testid="stSidebar"] { display: none !important; }
.block-container { max-width: 960px !important; padding-top:1.2rem !important; }
</style>""", unsafe_allow_html=True)

    st.markdown("""
<div style="text-align:center;padding:0.5rem 0 1rem;">
  <div style="font-size:2rem;font-weight:900;color:#1E293B;letter-spacing:-0.02em;">
    🔐 SignGuard
  </div>
  <div style="color:#64748B;font-size:0.9rem;">
    Cryptographic-Forensic Document Security Framework
  </div>
</div>""", unsafe_allow_html=True)

    # Step state
    if "pres_step" not in st.session_state:
        st.session_state["pres_step"] = 0

    step = st.session_state["pres_step"]
    _step_indicator(step)

    # Nav buttons
    nav_left, nav_reset, nav_right = st.columns([1, 1, 1])
    with nav_left:
        if step > 0:
            if st.button("◀  Previous"):
                st.session_state["pres_step"] -= 1
                st.rerun()
    with nav_reset:
        if st.button("↺  Reset"):
            for k in list(st.session_state.keys()):
                if k.startswith("pres_"):
                    del st.session_state[k]
            st.session_state["pres_step"] = 0
            st.rerun()
    with nav_right:
        if step < len(STEPS) - 1:
            if st.button("Next  ▶"):
                st.session_state["pres_step"] += 1
                st.rerun()

    st.markdown("---")

    # ─────────────────────────────────────────────────────────────────────
    if step == 0:
        section_header("Step 1 — Upload Document", "📄")
        uploaded = st.file_uploader("Upload a PDF document", type=["pdf"])
        if uploaded:
            raw = uploaded.read()
            st.session_state["pres_raw"]  = raw
            st.session_state["pres_name"] = uploaded.name
            preview = run_pipeline(raw, uploaded.name, analysis_mode="crypto_only", record_audit=False)
            if preview.parsed and not preview.parsed.error:
                show_image(preview.parsed.page_images[0], "Page 1 preview")
            else:
                st.error(preview.processing_error or preview.validation.reason)
                return
        else:
            st.markdown("**Or use a quick synthetic demo document:**")
            if st.button("Load Synthetic Demo Document"):
                from simulation.security_fixtures import signed_control
                raw = signed_control()
                st.session_state["pres_raw"]  = raw
                st.session_state["pres_name"] = "demo_document.pdf"
                from core.pdf_parser import render_page
                show_image(render_page(raw), "Demo document")
                st.success("Demo document loaded.")
            else:
                empty_state("Upload a PDF or load the demo document to begin.", "📂")

    # ─────────────────────────────────────────────────────────────────────
    elif step == 1:
        section_header("Step 2 — Baseline Verification", "🔬")
        raw = st.session_state.get("pres_raw")
        if raw is None:
            st.warning("Go back to Step 1 and load a document first.")
            return
        st.info(f"Document: **{st.session_state.get('pres_name','doc.pdf')}**")
        if st.button("Run Baseline Analysis"):
            with st.spinner("Analysing…"):
                result = run_pipeline(raw, st.session_state.get("pres_name","doc.pdf"))
            st.session_state["pres_result"] = result

        result = st.session_state.get("pres_result")
        if result and result.fusion:
            verdict_badge(result.fusion.verdict.value)
            st.markdown(f"""
<div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:10px;
  padding:0.9rem 1.2rem;margin:0.5rem 0;">
  <div style="font-size:0.9rem;color:#334155;">{result.fusion.explanation}</div>
  <div style="font-size:0.76rem;color:#94A3B8;margin-top:4px;">
    Integrity: {result.fusion.integrity_verdict.value}
  </div>
</div>""", unsafe_allow_html=True)
            if result.classification:
                st.metric("Classification", result.classification.doc_class.value)

    # ─────────────────────────────────────────────────────────────────────
    elif step == 2:
        section_header("Step 3 — Controlled Attack Demonstration", "⚗️")
        sel = st.selectbox(
            "Select scenario",
            [s.id for s in ALL_SCENARIOS],
            format_func=lambda x: get_scenario(x).name
        )
        sc = get_scenario(sel)
        st.caption(sc.description)

        if st.button("Generate Scenario & Run Detection"):
            with st.spinner("Generating synthetic documents and running detection…"):
                orig_b, demo_b, gt = sc.factory()
                result = run_pipeline(demo_b, f"scenario_{sel}.pdf")
            st.session_state["pres_sc_result"] = result
            st.session_state["pres_sc_orig"]   = orig_b
            st.session_state["pres_sc_demo"]   = demo_b
            st.session_state["pres_sc_gt"]     = gt
            st.session_state["pres_sc_id"]     = sel

        orig_b = st.session_state.get("pres_sc_orig")
        demo_b = st.session_state.get("pres_sc_demo")
        result = st.session_state.get("pres_sc_result")

        if orig_b and demo_b:
            from core.pdf_parser import render_page
            import hashlib
            orig_h = hashlib.sha256(orig_b).hexdigest()[:16]
            demo_h = hashlib.sha256(demo_b).hexdigest()[:16]
            hashes_match = (orig_h == demo_h)

            pc1, pc2 = st.columns(2)
            with pc1:
                st.markdown("**📄 Original document**")
                show_image(render_page(orig_b), f"Hash prefix: {orig_h}…")
            with pc2:
                diff_text = "IDENTICAL FILE" if hashes_match else "DIFFERENT FILE"
                diff_col  = "#15803D" if hashes_match else "#B91C1C"
                st.markdown(f"**Attack document** — <span style='color:{diff_col};font-size:0.8rem;font-weight:700;'>{diff_text}</span>",
                            unsafe_allow_html=True)
                show_image(render_page(demo_b), f"Hash prefix: {demo_h}…")

            if not hashes_match:
                st.error(f"File hashes differ: {orig_h}… → {demo_h}…")

        if result and result.fusion:
            verdict_badge(result.fusion.verdict.value)
            gt = st.session_state.get("pres_sc_gt","")
            with st.expander("Reveal ground-truth label (evaluation only)"):
                st.success(f"Ground truth: **{gt}**")
                st.caption("Never passed to the detector — revealed only for evaluation.")

    # ─────────────────────────────────────────────────────────────────────
    elif step == 3:
        section_header("Step 4 — Algorithm Evidence", "🔎")
        result = (st.session_state.get("pres_sc_result") or
                  st.session_state.get("pres_result"))
        if result is None:
            empty_state("Complete steps 2 or 3 first.", "🔬")
            return

        tab_ela, tab_orb, tab_rev, tab_loc = st.tabs(
            ["🖼️ ELA", "🎯 ORB/RANSAC", "📋 Revision", "✍️ Localisation"]
        )
        with tab_ela:
            if result.ela and result.ela.error is None:
                el = result.ela
                ec1,ec2 = st.columns(2)
                with ec1: show_image(el.original,  "Original")
                with ec2: show_image(el.amplified, f"Amplified ELA (Q{el.quality_used})")
                st.caption(el.sweep_summary)
                st.caption(el.finding)
            else:
                st.info("ELA not available for this scenario.")
        with tab_orb:
            if result.ransac:
                rs = result.ransac
                show_image(rs.inlier_vis, "Green = inliers | Red = outliers")
                o1,o2,o3 = st.columns(3)
                o1.metric("Inliers",   rs.inlier_count)
                o2.metric("Ratio",     f"{rs.inlier_ratio:.0%}")
                o3.metric("Geometric", "✓" if rs.geometric_ok else "✗")
                st.caption(rs.summary)
            else:
                st.info("ORB/RANSAC not available (needs ≥ 2 candidates).")
        with tab_rev:
            if result.revision and result.revision.diff_image:
                rv = result.revision
                r1,r2 = st.columns(2)
                with r1: show_image(rv.signed_rev_image, "Signed revision")
                with r2: show_image(rv.current_image,    "Current revision")
                show_image(rv.diff_image, "Pixel diff")
                st.metric("Changed area", f"{rv.changed_area_pct:.1f}%")
            else:
                st.info("No revision diff available.")
        with tab_loc:
            if result.localization:
                show_image(result.localization.annotated, "Candidates (blue boxes)")
                st.caption(f"{len(result.localization.candidates)} candidate(s)")
            else:
                st.info("Localisation not performed.")

    # ─────────────────────────────────────────────────────────────────────
    elif step == 4:
        section_header("Step 5 — Final Verdict & Report", "📊")
        result = (st.session_state.get("pres_sc_result") or
                  st.session_state.get("pres_result"))
        if result is None:
            empty_state("Complete earlier steps first.", "📋")
            return

        if result.fusion:
            fu = result.fusion
            verdict_badge(fu.verdict.value)
            st.markdown(f"""
<div style="font-size:1rem;font-weight:600;color:#334155;line-height:1.7;
  padding:0.8rem 1rem;background:#F8FAFC;border-radius:10px;margin:0.5rem 0;">
  {fu.explanation}
</div>""", unsafe_allow_html=True)
            st.markdown(f"**Integrity status:** {fu.integrity_verdict.value}")
            if fu.findings:
                st.markdown("**Findings:**")
                for f in fu.findings:
                    st.markdown(f"- **[{f.severity.value}]** {f.code} — {f.title}")
            st.caption(fu.completeness)
            with st.expander("Analysis limitations"):
                for lim in fu.limitations:
                    st.caption(f"⚠ {lim}")

        # Report download
        from reporting.json_report import to_json
        from reporting.pdf_report  import build_pdf_report
        d1, d2 = st.columns(2)
        with d1:
            st.download_button("⬇  JSON Report",
                               to_json(result).encode(),
                               "signguard_report.json", "application/json")
        with d2:
            st.download_button("⬇  PDF Report",
                               build_pdf_report(result),
                               "signguard_report.pdf", "application/pdf")
