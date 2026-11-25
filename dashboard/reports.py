"""Page 6 — Reports and Audit."""

from __future__ import annotations
import streamlit as st
import pandas as pd
from dashboard.components import inject_css, page_header, section_header, empty_state, download_button
from core.audit_logger import verify_chain, get_records


def render() -> None:
    inject_css()
    page_header("Reports & Audit", "Download forensic reports and inspect the audit chain.")

    result = st.session_state.get("pipeline_result")

    # ── Report downloads ───────────────────────────────────────────────────
    section_header("Forensic Reports")
    if result is None:
        empty_state("Run an analysis on the Document Analysis page to generate a report.")
    else:
        from reporting.json_report import to_json
        from reporting.pdf_report  import build_pdf_report
        col1, col2 = st.columns(2)
        with col1:
            json_bytes = to_json(result).encode()
            st.download_button(
                "⬇ Download JSON Report",
                data=json_bytes,
                file_name="signguard_report.json",
                mime="application/json",
            )
        with col2:
            pdf_bytes = build_pdf_report(result)
            st.download_button(
                "⬇ Download PDF Report",
                data=pdf_bytes,
                file_name="signguard_report.pdf",
                mime="application/pdf",
            )

        with st.expander("Preview JSON report"):
            st.json(to_json(result))

    st.markdown("---")

    # ── Audit chain ────────────────────────────────────────────────────────
    section_header("Tamper-Evident Audit Chain")

    chain_ok, chain_msg = verify_chain()
    if chain_ok:
        st.success(f"✓ {chain_msg}")
    else:
        st.error(f"✗ {chain_msg}")

    st.info(
        "The audit chain uses SHA-256 hash linking: each record includes the hash of the "
        "previous record. This provides tamper evidence for the log file itself. "
        "Independent custody of the chain head is required for stronger assurance."
    )

    records = get_records()
    if records:
        df = pd.DataFrame(records)
        display_cols = ["event_id","timestamp","doc_hash","verdict","prev_hash","record_hash"]
        display_cols = [c for c in display_cols if c in df.columns]

        # Truncate hashes for readability
        for col in ["prev_hash","record_hash","doc_hash"]:
            if col in df.columns:
                df[col] = df[col].str[:16] + "…"

        st.dataframe(df[display_cols])
        st.caption(f"{len(records)} audit record(s) on file.")
    else:
        empty_state("No audit records yet. Run an analysis to create the first entry.")
