"""Page 2 — Document Analysis (v2 — uses new crypto/fusion APIs)."""
from __future__ import annotations
import hashlib
import streamlit as st
from dashboard.components import (
    page_header, section_header, verdict_badge,
    status_pill, finding_card, show_image, empty_state, download_button
)
from core.pipeline import run as run_pipeline


def render() -> None:
    page_header("Document Analysis", "Upload a PDF and run the full forensic pipeline.")

    # ── Upload ────────────────────────────────────────────────────────────
    st.markdown("""
<div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:12px;
  padding:1.2rem 1.5rem;margin-bottom:1rem;">
  <div style="font-weight:700;color:#1E293B;font-size:0.95rem;margin-bottom:0.5rem;">
    📂 Upload PDF Document
  </div>
  <div style="font-size:0.8rem;color:#64748B;">
    PDF only · Max 50 MB · Max 200 pages · Processed locally on this machine
  </div>
</div>""", unsafe_allow_html=True)

    uploaded = st.file_uploader("Upload PDF", type=["pdf"],
                                label_visibility="collapsed")

    if uploaded is None:
        empty_state("Drop a PDF file above to begin forensic analysis.", "🔐")
        return

    raw = uploaded.read()

    # ── State invalidation keyed on SHA-256, not filename ─────────────────
    doc_hash = hashlib.sha256(raw).hexdigest()
    if st.session_state.get("last_doc_hash") != doc_hash:
        st.session_state.pop("pipeline_result", None)
        st.session_state.pop("analysis_config",  None)
        st.session_state["last_doc_hash"] = doc_hash
        st.session_state["last_filename"] = uploaded.name

    # ── Validate ─────────────────────────────────────────────────────────
    from core.pdf_parser import parse_pdf, validate_pdf, render_page
    val = validate_pdf(raw, uploaded.name)
    if not val.valid:
        st.error(f"⛔ Validation failed: {val.reason}")
        return

    parsed_preview = parse_pdf(raw, uploaded.name)
    if parsed_preview.error:
        st.error(f"⛔ Parse error: {parsed_preview.error}")
        return

    # ── Document identity banner ──────────────────────────────────────────
    st.markdown(f"""
<div style="background:#F0FDF4;border:1px solid #86EFAC;border-radius:8px;
  padding:0.6rem 1rem;margin-bottom:0.8rem;display:flex;gap:12px;align-items:center;">
  <span style="font-size:1.1rem;">📄</span>
  <div style="font-size:0.82rem;color:#334155;">
    <strong>{uploaded.name}</strong> &nbsp;·&nbsp;
    SHA-256: <code>{doc_hash[:20]}…</code> &nbsp;·&nbsp;
    {parsed_preview.page_count} page(s) &nbsp;·&nbsp;
    {parsed_preview.file_size:,} bytes
  </div>
</div>""", unsafe_allow_html=True)

    # ── Preview ────────────────────────────────────────────────────────────
    section_header("Document Preview", "📄")
    page_idx = 0
    if parsed_preview.page_count > 1:
        page_idx = st.slider("Page", 0, parsed_preview.page_count - 1, 0,
                             format="Page %d")

    col_prev, col_meta = st.columns([3, 2], gap="large")
    with col_prev:
        try:
            show_image(render_page(raw, page_idx),
                       f"Page {page_idx+1} of {parsed_preview.page_count}")
        except Exception as e:
            st.warning(f"Preview error: {e}")

    with col_meta:
        m = parsed_preview.metadata
        rows = [
            ("File",    uploaded.name),
            ("SHA-256", doc_hash[:20] + "…"),
            ("Size",    f"{parsed_preview.file_size:,} bytes"),
            ("Pages",   str(parsed_preview.page_count)),
            ("Sig fields", str(parsed_preview.sig_field_count)),
            ("Author",  m.get("author") or "—"),
            ("Creator", m.get("creator") or "—"),
            ("Created", (m.get("creation_date") or "—")[:30]),
            ("Modified",(m.get("mod_date") or "—")[:30]),
        ]
        html = '<div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:12px;overflow:hidden;">'
        html += '<div style="background:#F8FAFC;padding:0.6rem 1rem;border-bottom:1px solid #E2E8F0;font-weight:700;color:#1E293B;font-size:0.88rem;">Document Metadata</div>'
        for k, v in rows:
            html += (
                f'<div style="display:flex;justify-content:space-between;'
                f'padding:5px 1rem;border-bottom:1px solid #F8FAFC;">'
                f'<span style="color:#64748B;font-size:0.79rem;font-weight:500;">{k}</span>'
                f'<span style="font-size:0.79rem;color:#1E293B;font-weight:600;'
                f'max-width:55%;text-align:right;overflow:hidden;text-overflow:ellipsis;'
                f'white-space:nowrap;">{v}</span></div>'
            )
        html += '</div>'
        st.markdown(html, unsafe_allow_html=True)

        st.markdown("<div style='margin-top:0.6rem;'></div>", unsafe_allow_html=True)
        # Quick classification
        from core.document_classifier import classify, DocClass
        cls = classify(parsed_preview)
        cls_colors = {
            DocClass.CRYPTOGRAPHICALLY_SIGNED: ("#F0FDF4","#15803D","#86EFAC","🔏"),
            DocClass.VISUAL_CANDIDATE:         ("#FFFBEB","#92400E","#FCD34D","✍️"),
            DocClass.UNSIGNED:                 ("#F8FAFC","#475569","#CBD5E1","📄"),
            DocClass.UNSUPPORTED:              ("#FEF2F2","#B91C1C","#FCA5A5","⛔"),
        }
        bg,fg,border,icon = cls_colors.get(cls.doc_class,("#F8FAFC","#475569","#CBD5E1","❓"))
        st.markdown(f"""
<div style="background:{bg};border:1px solid {border};border-radius:10px;padding:0.8rem 1rem;">
  <div style="font-size:0.7rem;color:{fg};font-weight:700;text-transform:uppercase;
    letter-spacing:0.06em;margin-bottom:4px;">Document Classification</div>
  <div style="font-size:1rem;font-weight:800;color:{fg};">{icon} {cls.doc_class.value}</div>
  <div style="font-size:0.76rem;color:#64748B;margin-top:4px;line-height:1.5;">
    {cls.explanation[:120]}{'…' if len(cls.explanation)>120 else ''}
  </div>
</div>""", unsafe_allow_html=True)

    st.markdown("---")

    # ── Analysis settings (sidebar) ────────────────────────────────────────
    with st.sidebar:
        st.markdown("""
<div style="margin-top:0.8rem;padding:0.7rem;background:rgba(37,99,235,0.1);
  border:1px solid rgba(37,99,235,0.2);border-radius:8px;margin-bottom:0.5rem;">
  <div style="font-size:0.7rem;font-weight:700;color:#60A5FA;
    text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.4rem;">
    Analysis Settings
  </div>
</div>""", unsafe_allow_html=True)
        ela_q   = st.slider("ELA Quality", 50, 95, 75,
                            help="JPEG recompression quality for ELA")
        ela_amp = st.slider("ELA Amplification", 5, 30, 15,
                            help="Visual amplification (does not affect measurements)")

    # Invalidate if config changed
    cur_config = (ela_q, ela_amp)
    if st.session_state.get("analysis_config") != cur_config:
        if "pipeline_result" in st.session_state:
            st.session_state.pop("pipeline_result")
            st.info("Analysis settings changed — previous results cleared.")
        st.session_state["analysis_config"] = cur_config

    if st.button("🔬  Run Full Forensic Analysis"):
        with st.spinner("Running forensic pipeline — please wait…"):
            result = run_pipeline(raw, uploaded.name,
                                  ela_quality=ela_q, ela_amp=ela_amp)
        st.session_state["pipeline_result"] = result
        st.success(
            f"Analysis complete in {result.elapsed_sec:.2f}s  |  "
            f"Document: {uploaded.name}  |  Timestamp: {result.analysis_ts}"
        )

    result = st.session_state.get("pipeline_result")
    if result is None:
        st.markdown("""
<div style="background:#EFF6FF;border:1px solid #BFDBFE;border-radius:10px;
  padding:1rem 1.2rem;margin-top:0.5rem;display:flex;align-items:center;gap:10px;">
  <span style="font-size:1.3rem;">💡</span>
  <span style="color:#1D4ED8;font-size:0.88rem;font-weight:500;">
    Click <strong>Run Full Forensic Analysis</strong> above to start processing.
  </span>
</div>""", unsafe_allow_html=True)
        return

    # ── Verify result belongs to current document ──────────────────────────
    if result.parsed and result.parsed.sha256 != doc_hash:
        st.warning("Result is from a different document. Re-run analysis.")
        st.session_state.pop("pipeline_result", None)
        return

    # ══════════════════════════════════════════════════════════════════════
    # RESULTS
    # ══════════════════════════════════════════════════════════════════════

    # ── Verdict + integrity ────────────────────────────────────────────────
    if result.fusion:
        fu = result.fusion
        section_header("Final Verdict", "⚖️")

        v_col, i_col = st.columns([2,1])
        with v_col:
            verdict_badge(fu.verdict.value)
        with i_col:
            integ_colors = {
                "NO TAMPERING DETECTED":   ("#F0FDF4","#15803D","#86EFAC"),
                "INTEGRITY FAILURE":       ("#FEF2F2","#B91C1C","#FCA5A5"),
                "INTEGRITY NOT ESTABLISHED":("#FFFBEB","#92400E","#FCD34D"),
                "NOT APPLICABLE":          ("#F8FAFC","#475569","#CBD5E1"),
            }
            iv = fu.integrity_verdict.value
            bg_i,fg_i,bd_i = integ_colors.get(iv,("#F8FAFC","#475569","#CBD5E1"))
            st.markdown(f"""
<div style="background:{bg_i};border:1px solid {bd_i};border-radius:8px;
  padding:0.6rem 0.8rem;margin-top:0.3rem;">
  <div style="font-size:0.68rem;color:{fg_i};font-weight:700;
    text-transform:uppercase;letter-spacing:0.06em;">Integrity Status</div>
  <div style="font-size:0.85rem;font-weight:700;color:{fg_i};margin-top:3px;">{iv}</div>
</div>""", unsafe_allow_html=True)

        st.markdown(f"""
<div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:10px;
  padding:0.9rem 1.2rem;margin:0.5rem 0 0.3rem;">
  <div style="font-size:0.88rem;color:#334155;line-height:1.65;">{fu.explanation}</div>
  <div style="margin-top:0.5rem;font-size:0.76rem;color:#94A3B8;">{fu.completeness}</div>
  <div style="font-size:0.72rem;color:#94A3B8;margin-top:2px;">
    Analysis timestamp: {result.analysis_ts or "—"}
  </div>
</div>""", unsafe_allow_html=True)

        if fu.findings:
            section_header("Findings", "🚩")
            for f in fu.findings:
                finding_card(f.code, f.severity.value, f.title, f.description)
                if f.limitation:
                    st.caption(f"⚠ Limitation: {f.limitation}")

    # ── Cryptographic ──────────────────────────────────────────────────────
    if result.crypto and result.crypto.total_sigs > 0:
        section_header("Cryptographic Verification", "🔐")
        st.caption(f"pyHanko used: {result.crypto.pyhanko_used}")
        for r in result.crypto.results:
            with st.expander(f"Signature field: **{r.field_name}**", expanded=True):
                ca, cb, cc = st.columns(3)
                with ca:
                    st.markdown("**Signed-byte integrity**")
                    status_pill("Byte integrity",  r.integrity_ok)
                    st.markdown("")
                    status_pill("Math valid",       r.math_valid)
                    st.markdown("")
                    status_pill("Cert trusted",     r.cert_trusted)
                with cb:
                    st.markdown("**Signature details**")
                    st.caption(f"Digest: `{r.digest_alg}`")
                    st.caption(f"Sig alg: `{r.sig_alg}`")
                    st.caption(f"Signed: `{r.signing_time or '—'}`")
                    st.caption(f"Trust: `{r.trust_status}`")
                    st.caption(f"Mod-policy: `{r.modpolicy_status}`")
                    st.caption(f"Identity: `{r.identity_status}`")
                with cc:
                    if r.byte_range:
                        br = r.byte_range
                        st.markdown("**ByteRange**")
                        st.caption(f"Structurally valid: `{br.structurally_valid}`")
                        st.caption(f"Covers full file: `{br.covers_full_file}`")
                        st.caption(f"Covers signed rev: `{br.covers_signed_rev}`")
                        for note in br.validation_notes:
                            st.caption(f"• {note}")
                if r.cert_info:
                    ci = r.cert_info
                    st.code(
                        f"Subject:     {ci.subject}\n"
                        f"Issuer:      {ci.issuer}\n"
                        f"Serial:      {ci.serial}\n"
                        f"Self-signed: {ci.is_self_signed}  |  "
                        f"Test cert: {ci.is_test_cert}\n"
                        f"Key alg:     {ci.key_algorithm}"
                    )
                    if ci.is_test_cert:
                        st.warning(
                            "⚠️ TEST / self-signed certificate — signer identity "
                            "CANNOT be established from this certificate alone."
                        )
                for detail in r.details:
                    st.caption(detail)
                if r.error:
                    st.warning(f"Verification note: {r.error}")
    elif result.crypto is not None:
        st.info("No cryptographic signatures found in this document.")

    # ── Revision ──────────────────────────────────────────────────────────
    if result.revision:
        section_header("Revision Analysis", "📋")
        rv = result.revision
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Revisions",         len(rv.revisions))
        c2.metric("Incremental",        "Yes" if rv.has_incremental_updates else "No")
        c3.metric("Shadow suspect",     "⚠️ Yes" if rv.shadow_suspect else "No")
        c4.metric("Changed area",       f"{rv.changed_area_pct:.2f}%")
        st.caption(f"Discovery method: {rv.discovery_method}")
        st.caption(rv.summary)

        if rv.shadow_suspect:
            st.markdown("""
<div style="background:#FFFBEB;border:1.5px solid #FCD34D;border-radius:10px;
  padding:0.8rem 1rem;margin:0.4rem 0;display:flex;gap:10px;">
  <span style="font-size:1.3rem;">⚠️</span>
  <div style="color:#78350F;font-size:0.87rem;font-weight:600;">
    Possible shadow attack — visible content changed between signed revision and current.
    Manual expert review required.
  </div>
</div>""", unsafe_allow_html=True)

        if rv.text_diff_summary:
            st.info(f"Text diff: {rv.text_diff_summary}")
        if rv.metadata_changed:
            st.info("Metadata differs between signed revision and current document.")

        if rv.signed_rev_image and rv.current_image:
            ic1, ic2 = st.columns(2)
            with ic1: show_image(rv.signed_rev_image, "Signed revision")
            with ic2: show_image(rv.current_image,    "Current revision (changes annotated)")
            if rv.diff_image:
                with st.expander("Pixel difference"):
                    d1, d2 = st.columns(2)
                    with d1: show_image(rv.diff_image, "Raw pixel diff")
                    with d2:
                        if rv.diff_mask: show_image(rv.diff_mask, "Thresholded mask")

        with st.expander("Revision timeline"):
            for rev in rv.revisions:
                badge = " 🔏" if rev.is_signed else ""
                st.markdown(
                    f"- **Rev {rev.index}**: bytes {rev.start_offset}–{rev.end_offset}"
                    f" | pages={rev.page_count}{badge}"
                )

        if rv.limitations:
            with st.expander("Analysis limitations"):
                for lim in rv.limitations:
                    st.caption(f"⚠ {lim}")

    # ── Localisation ──────────────────────────────────────────────────────
    if result.localization:
        section_header("Signature Localisation", "✍️")
        loc = result.localization
        st.markdown(f"""
<div style="background:#EFF6FF;border:1px solid #BFDBFE;border-radius:8px;
  padding:0.55rem 0.9rem;margin-bottom:0.7rem;font-size:0.84rem;color:#1D4ED8;">
  Found <strong>{len(loc.candidates)}</strong> visual candidate(s) — 
  heuristic scores, not calibrated probabilities. Blue bounding boxes mark 
  unverified regions. Localisation does not confirm signer identity.
</div>""", unsafe_allow_html=True)
        with st.expander("Show localisation pipeline stages"):
            c1,c2,c3 = st.columns(3)
            with c1: show_image(loc.gray,        "Greyscale")
            with c2: show_image(loc.text_masked, "Text masked")
            with c3: show_image(loc.thresholded, "Thresholded (Otsu)")
            c4,c5 = st.columns(2)
            with c4: show_image(loc.components_vis, "Connected components")
            with c5: show_image(loc.annotated,       "Candidates (blue boxes)")
        if loc.candidates:
            st.markdown("**Extracted candidate crops:**")
            cr_cols = st.columns(min(len(loc.candidates), 4))
            for i, cand in enumerate(loc.candidates[:4]):
                with cr_cols[i]:
                    show_image(cand.crop, f"Candidate {i+1} (score={cand.confidence:.2f})")

    # ── ELA ───────────────────────────────────────────────────────────────
    if result.ela and result.ela.error is None:
        section_header("Error Level Analysis — Multi-Quality", "🖼️")
        el = result.ela
        m1,m2,m3,m4 = st.columns(4)
        m1.metric("Mean Residual",  f"{el.mean_residual:.2f}")
        m2.metric("Max Residual",   f"{el.max_residual:.2f}")
        m3.metric("Std Dev",        f"{el.std_residual:.2f}")
        m4.metric("High-energy px", f"{el.high_pct:.1f}%")

        if el.sweep_summary:
            st.caption(el.sweep_summary)

        # Multi-quality tabs
        if el.multi_quality:
            q_tabs = st.tabs([f"Q{q}" for q in sorted(el.multi_quality.keys())])
            for tab, q in zip(q_tabs, sorted(el.multi_quality.keys())):
                with tab:
                    mq = el.multi_quality[q]
                    st.caption(
                        f"Mean={mq.mean_residual:.2f} | Max={mq.max_residual:.2f} | "
                        f"Std={mq.std_residual:.2f} | High%={mq.high_pct:.1f}"
                    )
                    qc1,qc2 = st.columns(2)
                    with qc1: show_image(mq.raw_diff,  "Raw diff")
                    with qc2: show_image(mq.amplified, "Amplified (visualization only)")

        with st.expander("ELA interpretation & limitations"):
            st.caption(el.finding)
            st.warning(
                "Amplification changes visualization brightness only — it does NOT "
                "affect residual measurements or verdict logic. ELA is a supporting "
                "forensic indicator. High residuals can be caused by high-contrast edges, "
                "printed text, or gradients — not only manipulation."
            )

    # ── ORB / RANSAC ──────────────────────────────────────────────────────
    if result.ransac:
        section_header("ORB / RANSAC Analysis", "🎯")
        rs = result.ransac
        r1,r2,r3,r4 = st.columns(4)
        r1.metric("Filtered Matches", rs.matches_before)
        r2.metric("RANSAC Inliers",   rs.inlier_count)
        r3.metric("Outliers",         rs.outlier_count)
        r4.metric("Inlier Ratio",     f"{rs.inlier_ratio:.0%}")
        with st.expander("RANSAC visualisation"):
            show_image(rs.inlier_vis, "Green = geometric inliers | Red = rejected outliers")
            st.caption(rs.summary)
            st.caption("Visual similarity does not establish signer identity or prove unauthorised reuse.")

    # ── Downloads ─────────────────────────────────────────────────────────
    section_header("Download Reports", "📥")
    st.caption("Reports correspond to the analysis above. They are NOT authenticity certificates.")
    from reporting.json_report import to_json
    from reporting.pdf_report  import build_pdf_report
    dl1, dl2 = st.columns(2)
    with dl1:
        download_button("⬇  JSON Report",
                        to_json(result).encode(),
                        "signguard_report.json", "application/json")
    with dl2:
        download_button("⬇  PDF Report",
                        build_pdf_report(result),
                        "signguard_report.pdf", "application/pdf")
