"""Page 4 — Algorithm Visualizations."""
from __future__ import annotations
import streamlit as st
from dashboard.components import page_header, section_header, show_image, empty_state


def render() -> None:
    page_header("Algorithm Visualizations",
                "Deep-dive into every processing stage of the last analysis.",
                badge="TECHNICAL")

    result = st.session_state.get("pipeline_result")
    if result is None:
        empty_state("Run an analysis on the Document Analysis page first.", "🔬")
        return

    # Stage completion indicators
    stages = {
        "Cryptographic": result.crypto is not None and result.crypto.total_sigs > 0,
        "Revision":      result.revision is not None,
        "Localisation":  result.localization is not None,
        "ELA":           result.ela is not None and result.ela.error is None,
        "ORB":           result.orb is not None and result.orb.error is None,
        "RANSAC":        result.ransac is not None,
        "Fusion":        result.fusion is not None,
    }
    pills = ""
    for name, done in stages.items():
        bg   = "#F0FDF4" if done else "#F8FAFC"
        fg   = "#15803D" if done else "#94A3B8"
        brd  = "#86EFAC" if done else "#E2E8F0"
        icon = "✓" if done else "–"
        pills += (f'<span style="background:{bg};color:{fg};border:1px solid {brd};'
                  f'border-radius:20px;padding:3px 10px;font-size:0.78rem;'
                  f'font-weight:600;margin:2px;">{icon} {name}</span>')
    st.markdown(f'<div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:1rem;">{pills}</div>',
                unsafe_allow_html=True)

    # ── Crypto ─────────────────────────────────────────────────────────────
    with st.expander("🔐  Cryptographic Verification", expanded=True):
        if result.crypto and result.crypto.total_sigs > 0:
            cr = result.crypto
            st.markdown(f"**pyHanko:** `{cr.pyhanko_used}` &nbsp;|&nbsp; **Signatures:** `{cr.total_sigs}`")
            for r in cr.results:
                st.markdown(f"**Field:** `{r.field_name}`")
                c1,c2,c3,c4 = st.columns(4)
                c1.metric("Byte Integrity", "PASS" if r.integrity_ok else ("FAIL" if r.integrity_ok is False else "?"))
                c2.metric("Math Valid",     str(r.math_valid))
                c3.metric("Cert Trusted",   str(r.cert_trusted))
                c4.metric("Post-sig Mods",  str(r.post_signing_mods))
                if r.cert_info:
                    ci = r.cert_info
                    st.code(
                        f"Subject:     {ci.subject}\n"
                        f"Issuer:      {ci.issuer}\n"
                        f"Serial:      {ci.serial}\n"
                        f"Valid from:  {ci.not_before}\n"
                        f"Valid until: {ci.not_after}\n"
                        f"Self-signed: {ci.is_self_signed}  |  Test cert: {ci.is_test_cert}"
                    )
        else:
            st.info("No cryptographic signatures found in this document.")

    # ── ByteRange ─────────────────────────────────────────────────────────
    with st.expander("📐  ByteRange Coverage"):
        if result.crypto and result.crypto.total_sigs > 0:
            for r in result.crypto.results:
                st.markdown(f"**{r.field_name}** — Covers entire file: `{r.revision_covers_all}`")
                val = 100 if r.byte_range_valid else 0
                st.progress(val / 100,
                            text=f"ByteRange structural validity: {'Valid' if r.byte_range_valid else 'Invalid'}")
        else:
            st.info("No signature ByteRange data available.")

    # ── Revision ──────────────────────────────────────────────────────────
    with st.expander("📋  PDF Revision Analysis"):
        if result.revision:
            rv = result.revision
            section_header("Revision Timeline")
            for rev in rv.revisions:
                badge = "🔏 signed" if rev.is_signed else ""
                st.markdown(f"- **Rev {rev.index}**: bytes `{rev.start_offset}` – `{rev.end_offset}` {badge}")

            if rv.signed_rev_image and rv.current_image:
                i1,i2 = st.columns(2)
                with i1: show_image(rv.signed_rev_image, "Signed revision render")
                with i2: show_image(rv.current_image,    "Current revision render")
            if rv.diff_image:
                d1,d2 = st.columns(2)
                with d1: show_image(rv.diff_image, "Pixel difference")
                with d2:
                    if rv.diff_mask: show_image(rv.diff_mask, "Thresholded mask")
            st.markdown(f"Changed: **{rv.changed_area_pct:.2f}%** | Shadow suspect: **{rv.shadow_suspect}**")
        else:
            st.info("Revision analysis not performed.")

    # ── Localisation pipeline ─────────────────────────────────────────────
    with st.expander("✍️  Signature Localisation Pipeline"):
        if result.localization:
            loc = result.localization
            st.markdown("**6-stage processing pipeline:**")
            c1,c2,c3 = st.columns(3)
            with c1: show_image(loc.original,     "1. Original page")
            with c2: show_image(loc.gray,         "2. Greyscale")
            with c3: show_image(loc.text_masked,  "3. Text masked")
            c4,c5,c6 = st.columns(3)
            with c4: show_image(loc.thresholded,  "4. Thresholded (Otsu)")
            with c5: show_image(loc.components_vis,"5. Connected components")
            with c6: show_image(loc.annotated,    "6. Candidates (blue boxes)")
            if loc.candidates:
                st.markdown("**Extracted crops:**")
                cr_cols = st.columns(min(len(loc.candidates), 4))
                for i, cand in enumerate(loc.candidates[:4]):
                    with cr_cols[i]:
                        show_image(cand.crop, f"Crop {i+1} (conf={cand.confidence:.2f})")
        else:
            st.info("Localisation not performed.")

    # ── ELA ───────────────────────────────────────────────────────────────
    with st.expander("🖼️  Error Level Analysis — Multi-Quality"):
        if result.ela and result.ela.error is None:
            el = result.ela
            import plotly.graph_objects as go

            # Multi-quality comparison
            if el.multi_quality:
                q_vals = sorted(el.multi_quality.keys())
                means  = [el.multi_quality[q].mean_residual for q in q_vals]
                fig2 = go.Figure()
                fig2.add_trace(go.Bar(
                    x=[f"Q{q}" for q in q_vals], y=means,
                    marker_color=["#B91C1C" if m > 25 else "#2563EB" for m in means],
                    text=[f"{m:.1f}" for m in means], textposition="outside",
                ))
                fig2.add_hline(y=25, line_dash="dot", line_color="#B45309",
                               annotation_text="Alert threshold")
                fig2.update_layout(
                    title="Mean Residual by JPEG Quality Setting",
                    yaxis_title="Mean residual",
                    height=250, margin=dict(l=20,r=20,t=40,b=10),
                    plot_bgcolor="#F8FAFC", paper_bgcolor="#FFFFFF",
                )
                st.plotly_chart(fig2)
                st.caption(el.sweep_summary)

            # Residual histogram for active quality
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=list(range(0, 256, 4)),
                y=[sum(el.histogram[i:i+4]) for i in range(0, 256, 4)],
                marker_color="#2563EB", name="Residual",
            ))
            fig.update_layout(
                title=f"ELA Residual Histogram — Q{el.quality_used} (measurement, not amplified)",
                xaxis_title="Pixel intensity", yaxis_title="Frequency",
                height=260, margin=dict(l=20,r=20,t=40,b=20),
                plot_bgcolor="#F8FAFC", paper_bgcolor="#FFFFFF",
                font=dict(family="Inter, sans-serif"),
            )
            st.plotly_chart(fig)

            ec1,ec2,ec3,ec4 = st.columns(4)
            with ec1: show_image(el.original,     "Original")
            with ec2: show_image(el.recompressed, "Recompressed")
            with ec3: show_image(el.raw_diff,     "Raw diff (measurement)")
            with ec4: show_image(el.amplified,    f"Amplified ×{el.amp_used} (visualization only)")
            st.caption(el.finding)
            st.warning(
                "Amplification changes visualization brightness only — it does NOT "
                "affect residual measurements or verdict logic. Elevated ELA residuals "
                "can be caused by high-contrast edges, printed text, or gradients — "
                "not only by manipulation. ELA is a supporting forensic indicator."
            )
        else:
            msg = result.ela.error if result.ela else "ELA not performed."
            st.info(msg)

    # ── ORB ───────────────────────────────────────────────────────────────
    with st.expander("🎯  ORB Feature Matching"):
        if result.orb and result.orb.error is None:
            orb = result.orb
            st.markdown(
                f"Keypoints A: **{orb.n_kp_a}** | Keypoints B: **{orb.n_kp_b}** | "
                f"Raw matches: **{orb.n_raw_matches}** | Filtered: **{orb.n_filtered}**"
            )
            o1,o2 = st.columns(2)
            with o1: show_image(orb.kp_a_vis, "Keypoints — image A")
            with o2: show_image(orb.kp_b_vis, "Keypoints — image B")
            show_image(orb.raw_matches_vis,      "Raw matches")
            show_image(orb.filtered_matches_vis, "Filtered matches (ratio + mutual)")
        else:
            msg = result.orb.error if result.orb else "ORB not performed (need ≥ 2 candidates)."
            st.info(msg)

    # ── RANSAC ────────────────────────────────────────────────────────────
    with st.expander("📐  RANSAC Geometric Verification"):
        if result.ransac:
            rs = result.ransac
            r1,r2,r3,r4 = st.columns(4)
            r1.metric("Matches",    rs.matches_before)
            r2.metric("Inliers",    rs.inlier_count)
            r3.metric("Outliers",   rs.outlier_count)
            r4.metric("Inlier %",   f"{rs.inlier_ratio:.0%}")
            show_image(rs.inlier_vis, "Green = inliers | Red = outliers")
            st.caption(rs.summary)
        else:
            st.info("RANSAC not performed.")

    # ── Evidence fusion ────────────────────────────────────────────────────
    with st.expander("⚖️  Evidence Fusion"):
        if result.fusion:
            fu = result.fusion
            import plotly.graph_objects as go

            # Integrity verdict
            st.markdown(f"**Integrity status:** `{fu.integrity_verdict.value}`")
            st.markdown(f"**Overall verdict:** `{fu.verdict.value}` (confidence: {fu.confidence_label})")

            modules  = list(fu.module_scores.keys())
            statuses = list(fu.module_scores.values())
            colors = []
            for s in statuses:
                sl = s.lower()
                if "fail" in sl or "tamper" in sl:      colors.append("#B91C1C")
                elif "suspect" in sl or "review" in sl: colors.append("#B45309")
                elif "pass" in sl or "no tamper" in sl: colors.append("#15803D")
                else:                                   colors.append("#64748B")

            fig = go.Figure(go.Bar(
                x=modules, y=[1]*len(modules),
                text=statuses, textposition="inside",
                marker_color=colors,
            ))
            fig.update_layout(
                title="Module Status Summary", height=250,
                showlegend=False, yaxis_visible=False,
                plot_bgcolor="#F8FAFC", paper_bgcolor="#FFFFFF",
                font=dict(family="Inter, sans-serif"),
            )
            st.plotly_chart(fig)

            if fu.findings:
                for f in fu.findings:
                    st.markdown(f"- **[{f.severity.value}]** `{f.code}` — {f.title}")
                    if f.limitation:
                        st.caption(f"  ⚠ {f.limitation}")
            if fu.limitations:
                with st.expander("Analysis limitations"):
                    for lim in fu.limitations:
                        st.caption(f"⚠ {lim}")
