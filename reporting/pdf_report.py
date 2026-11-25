"""Module 11b — PDF forensic report generator (ReportLab)."""
from __future__ import annotations
import io, time
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Image as RLImage, PageBreak,
)
from core.pipeline import PipelineResult
from core.evidence_fusion import Verdict, IntegrityVerdict

W, H = A4
NAVY   = colors.HexColor("#1E293B")
GREEN  = colors.HexColor("#15803D")
RED    = colors.HexColor("#B91C1C")
AMBER  = colors.HexColor("#B45309")
LIGHT  = colors.HexColor("#F8FAFC")
BORDER = colors.HexColor("#E2E8F0")
MUTED  = colors.HexColor("#64748B")


def _verdict_color(v):
    if v in (Verdict.TAMPERING_DETECTED, "TAMPERING DETECTED"):
        return RED
    if v in (Verdict.REVIEW_REQUIRED, "REVIEW REQUIRED"):
        return AMBER
    return MUTED


def _two_col_table(rows):
    t = Table(rows, colWidths=["38%", "62%"])
    t.setStyle(TableStyle([
        ("FONTNAME",    (0,0),(0,-1), "Helvetica-Bold"),
        ("FONTSIZE",    (0,0),(-1,-1), 8),
        ("TEXTCOLOR",   (0,0),(0,-1), MUTED),
        ("ROWBACKGROUNDS",(0,0),(-1,-1), [colors.white, LIGHT]),
        ("GRID",        (0,0),(-1,-1), 0.5, BORDER),
        ("LEFTPADDING", (0,0),(-1,-1), 6),
        ("TOPPADDING",  (0,0),(-1,-1), 3),
        ("BOTTOMPADDING",(0,0),(-1,-1), 3),
    ]))
    return t


def build_pdf_report(result: PipelineResult) -> bytes:
    buf    = io.BytesIO()
    styles = getSampleStyleSheet()

    h1 = ParagraphStyle("h1", parent=styles["Heading1"],
                         textColor=NAVY, fontSize=16, spaceAfter=6)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"],
                         textColor=NAVY, fontSize=12, spaceAfter=4)
    body = ParagraphStyle("body", parent=styles["Normal"],
                          fontSize=9, leading=14, spaceAfter=4)
    label = ParagraphStyle("label", parent=styles["Normal"],
                           fontSize=8, textColor=MUTED)
    sev_crit = ParagraphStyle("sv1", parent=body, textColor=RED,
                              fontName="Helvetica-Bold")
    sev_high = ParagraphStyle("sv2", parent=body, textColor=AMBER,
                              fontName="Helvetica-Bold")

    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2.5*cm, bottomMargin=2*cm)
    story = []

    from xml.sax.saxutils import escape
    if result.coverage:
        story.append(Paragraph("Analysis Coverage", h2))
        story.append(Paragraph(escape(str(result.coverage)), body))
    if result.processing_error:
        story.append(Paragraph(escape(result.processing_error), sev_crit))
    if result.audit_error:
        story.append(Paragraph(escape("Audit record NOT saved: " + result.audit_error), sev_high))

    # Header
    story.append(Paragraph("SignGuard Forensic Report", h1))
    story.append(Paragraph(
        f"Generated: {time.strftime('%Y-%m-%d %H:%M UTC')} | "
        f"Schema 2.0 | Analysis: {result.analysis_ts or 'N/A'}",
        label))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER, spaceAfter=10))
    story.append(Paragraph(
        "This report is NOT an authenticity certificate. It is a forensic "
        "analysis report for educational and research use. Expert review is "
        "required for any legal, compliance, or operational decision.",
        label))
    story.append(Spacer(1, 0.4*cm))

    # Verdict
    if result.fusion:
        fu = result.fusion
        vc = _verdict_color(fu.verdict.value)
        banner = Table([[
            Paragraph(f"<b>VERDICT: {fu.verdict.value}</b>",
                      ParagraphStyle("v", parent=body, textColor=vc,
                                     fontSize=13, fontName="Helvetica-Bold")),
            Paragraph(f"Integrity: {fu.integrity_verdict.value}",
                      ParagraphStyle("iv", parent=body, fontSize=8, textColor=MUTED)),
        ]], colWidths=["65%", "35%"])
        banner.setStyle(TableStyle([
            ("BOX",         (0,0),(-1,-1), 1.5, vc),
            ("BACKGROUND",  (0,0),(-1,-1), LIGHT),
            ("TOPPADDING",  (0,0),(-1,-1), 8),
            ("BOTTOMPADDING",(0,0),(-1,-1), 8),
            ("LEFTPADDING", (0,0),(-1,-1), 10),
        ]))
        story.append(banner)
        story.append(Spacer(1, 0.3*cm))
        story.append(Paragraph(escape(fu.explanation), body))
        story.append(Paragraph(f"Confidence: {fu.confidence_label} | {fu.completeness}", label))
        story.append(Spacer(1, 0.4*cm))

    # Document info
    if result.parsed:
        p = result.parsed
        story.append(Paragraph("Document Information", h2))
        story.append(_two_col_table([
            ["Filename",   p.file_name],
            ["SHA-256",    p.sha256],
            ["Size",       f"{p.file_size:,} bytes"],
            ["Pages",      str(p.page_count)],
            ["Encrypted",  str(p.is_encrypted)],
            ["Author",     p.metadata.get("author","—")],
            ["Creator",    p.metadata.get("creator","—")],
        ]))
        story.append(Spacer(1, 0.4*cm))

    # Classification
    if result.classification:
        c = result.classification
        story.append(Paragraph("Signature Classification", h2))
        story.append(Paragraph(f"<b>Class:</b> {c.doc_class.value}", body))
        story.append(Paragraph(escape(c.explanation), body))
        story.append(Spacer(1, 0.3*cm))

    # Cryptographic
    if result.crypto and result.crypto.total_sigs > 0:
        story.append(Paragraph("Cryptographic Verification", h2))
        for sig in result.crypto.results:
            rows = [
                ["Field",           sig.field_name],
                ["Integrity",       sig.integrity_status],
                ["Math valid",      str(sig.math_valid)],
                ["Trust",           sig.trust_status],
                ["Mod-policy",      sig.modpolicy_status],
                ["Identity",        sig.identity_status],
                ["Digest alg",      sig.digest_alg],
                ["Sig alg",         sig.sig_alg],
                ["Signing time",    sig.signing_time or "—"],
                ["Completeness",    sig.completeness],
                ["Revocation", sig.revocation_status],
                ["Trusted timestamp", sig.timestamp_status],
                ["Modification level", sig.modification_level],
            ]
            if sig.byte_range:
                rows.append(["ByteRange valid", str(sig.byte_range.structurally_valid)])
                rows.append(["Covers full file", str(sig.byte_range.covers_full_file)])
                rows.append(["Covers parsed signed revision", str(sig.byte_range.covers_signed_rev)])
                rows.append(["pyHanko coverage", sig.coverage_level])
            if sig.cert_info:
                rows += [
                    ["Cert subject",    sig.cert_info.subject[:60]],
                    ["Cert issuer",     sig.cert_info.issuer[:60]],
                    ["Self-signed",     str(sig.cert_info.is_self_signed)],
                    ["Test certificate", str(sig.cert_info.is_test_cert)],
                ]
            if sig.error:
                rows.append(["Error", sig.error[:100]])
            story.append(_two_col_table(rows))
            story.append(Spacer(1, 0.2*cm))
        story.append(Spacer(1, 0.2*cm))

    # Revision
    if result.revision:
        rv = result.revision
        story.append(Paragraph("Revision Analysis", h2))
        story.append(_two_col_table([
            ["Revisions",           str(len(rv.revisions))],
            ["Discovery method",    rv.discovery_method],
            ["Incremental updates", str(rv.has_incremental_updates)],
            ["Shadow suspect",      str(rv.shadow_suspect)],
            ["Changed area",        f"{rv.changed_area_pct:.2f}%"],
            ["Text diff",           rv.text_diff_summary or "None detected"],
            ["Metadata changed",    str(rv.metadata_changed)],
        ]))
        story.append(Paragraph(rv.summary, body))
        story.append(Spacer(1, 0.4*cm))

    # Findings
    if result.fusion and result.fusion.findings:
        story.append(Paragraph("Findings", h2))
        for f in result.fusion.findings:
            style = sev_crit if f.severity.value in ("CRITICAL",) else (
                    sev_high if f.severity.value == "HIGH" else body)
            story.append(Paragraph(
                f"[{f.severity.value}] {f.code} — {f.title}", style))
            story.append(Paragraph(escape(f.description), body))
            if f.measurements:
                story.append(Paragraph(f"<i>Measurements: {escape(f.measurements)}</i>", label))
            if f.limitation:
                story.append(Paragraph(f"<i>Limitation: {escape(f.limitation)}</i>", label))
            story.append(Spacer(1, 0.2*cm))
        story.append(Spacer(1, 0.2*cm))

    # ELA
    if result.ela and result.ela.error is None:
        el = result.ela
        story.append(Paragraph("Error Level Analysis (Multi-Quality)", h2))
        story.append(_two_col_table([
            ["Active quality", str(el.quality_used)],
            ["Mean residual",  f"{el.mean_residual:.2f}"],
            ["Max residual",   f"{el.max_residual:.2f}"],
            ["Std residual",   f"{el.std_residual:.2f}"],
            ["High-energy %",  f"{el.high_pct:.2f}%"],
        ]))
        if el.sweep_summary:
            story.append(Paragraph(el.sweep_summary, label))
        story.append(Paragraph(el.finding, body))
        story.append(Spacer(1, 0.4*cm))

    # ORB / RANSAC
    if result.ransac:
        rs = result.ransac
        story.append(Paragraph("ORB / RANSAC Analysis", h2))
        story.append(_two_col_table([
            ["Matches (pre-RANSAC)", str(rs.matches_before)],
            ["Inliers",              str(rs.inlier_count)],
            ["Outliers",             str(rs.outlier_count)],
            ["Inlier ratio",         f"{rs.inlier_ratio:.0%}"],
            ["Geometric match",      str(rs.geometric_ok)],
            ["Spatial coverage",     f"{rs.spatial_coverage:.0%}"],
        ]))
        story.append(Paragraph(rs.summary, body))
        story.append(Spacer(1, 0.4*cm))

    # Limitations
    if result.fusion and result.fusion.limitations:
        story.append(Paragraph("Analysis Limitations", h2))
        for lim in result.fusion.limitations:
            story.append(Paragraph(f"• {escape(lim)}", body))
        story.append(Spacer(1, 0.3*cm))

    if result.active_content:
        story.append(Paragraph("Static PDF Content", h2))
        story.append(Paragraph(escape(result.active_content.get('note','')), body))
        for entry in result.active_content.get('entries',[])[:30]:
            story.append(Paragraph(escape(f"Object {entry['object']}: {entry['category']} - {entry['description']}"), body))
        if len(result.active_content.get('entries',[]))>30:
            story.append(Paragraph("Additional inventory entries are retained in the JSON evidence.", label))
    if result.timeline:
        story.append(Paragraph("Consecutive Revision Timeline", h2))
        story.append(Paragraph(escape(f"Complete: {result.timeline.get('complete')}; page comparisons: {result.timeline.get('pages_compared',0)}"), body))
        for transition in result.timeline.get('transitions',[]):
            changed=[str(p['page']+1)+': '+p['change'] for p in transition['pages'] if p['change']!='unchanged']
            story.append(Paragraph(escape(f"Revision {transition['from_revision']+1} to {transition['to_revision']+1}: "+(', '.join(changed) or 'no page content change detected')), body))
    if result.renderer_comparison:
        story.append(Paragraph("Independent Rendering", h2))
        story.append(Paragraph(escape(str(result.renderer_comparison)), body))
    if result.provenance:
        story.append(Paragraph("Reproducibility", h2))
        story.append(Paragraph(escape(f"Application {result.provenance.get('application_version')}; Python {result.provenance.get('python')}; commit {result.provenance.get('git_commit')}"), body))
        story.append(Paragraph(escape("Engine source SHA-256: "+result.provenance.get('engine_source_sha256','')), body))
        story.append(Paragraph(escape("Settings: "+str(result.provenance.get('settings',{}))), body))
        story.append(Paragraph("Full dependency versions, decision thresholds and evidence hashes are in the JSON report and evidence package.", label))

    # Footer
    story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceBefore=10))
    story.append(Paragraph(
        "Generated by SignGuard v3.0 for educational and research purposes. "
        "Not an authenticity certificate. Results require qualified expert review.",
        label))

    doc.build(story)
    return buf.getvalue()
