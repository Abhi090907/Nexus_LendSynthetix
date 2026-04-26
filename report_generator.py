import hashlib
import io
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import qrcode
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from report_signing import build_verification_payload, generate_report_hash

COLOR_BG_DARK = colors.HexColor("#0f1117")
COLOR_CARD = colors.HexColor("#1a1f2e")
COLOR_GREEN = colors.HexColor("#22c55e")
COLOR_RED = colors.HexColor("#ef4444")
COLOR_AMBER = colors.HexColor("#f59e0b")
COLOR_BLUE = colors.HexColor("#3b82f6")
COLOR_PURPLE = colors.HexColor("#8b5cf6")
COLOR_TEXT_LIGHT = colors.HexColor("#e2e8f0")
COLOR_TEXT_DIM = colors.HexColor("#94a3b8")
COLOR_BORDER = colors.HexColor("#2d3748")
COLOR_WHITE = colors.white


def _build_qr_flowable(verification: dict, final_rec: str) -> Image:
    qr_data = (
        "LENDSYNTHETIX INTEGRITY CHECK\n"
        f"Document ID: {verification['document_id']}\n"
        f"SHA-256: {verification['sha256_hash']}\n"
        f"Generated: {verification['generated_at']}\n"
        f"Signature: {verification['server_signature'][:32]}...\n"
        f"Recommendation: {final_rec}"
    )
    qr = qrcode.QRCode(
        version=2, box_size=3, border=2, error_correction=qrcode.constants.ERROR_CORRECT_H
    )
    qr.add_data(qr_data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)
    return Image(qr_buffer, width=32 * mm, height=32 * mm)


def generate_signed_pdf(report_data: dict, collection_name: str) -> bytes:
    """
    Generates a complete signed PDF credit appraisal report.
    Returns raw PDF bytes (ready for HTTP response body).
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        title=f"LendSynthetix Credit Appraisal — {collection_name}",
        author="LendSynthetix AI Credit War Room",
        subject="Credit Appraisal Note",
        creator="LendSynthetix v1.0",
    )
    verification = build_verification_payload(report_data, collection_name)
    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "Title",
        fontSize=22,
        textColor=COLOR_TEXT_LIGHT,
        fontName="Helvetica-Bold",
        alignment=TA_CENTER,
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "Subtitle",
        fontSize=11,
        textColor=COLOR_TEXT_DIM,
        fontName="Helvetica",
        alignment=TA_CENTER,
        spaceAfter=16,
    )
    section_header = ParagraphStyle(
        "SectionHeader",
        fontSize=13,
        textColor=COLOR_BLUE,
        fontName="Helvetica-Bold",
        spaceBefore=14,
        spaceAfter=6,
        borderPad=4,
    )
    body_style = ParagraphStyle(
        "Body",
        fontSize=9,
        textColor=COLOR_TEXT_LIGHT,
        fontName="Helvetica",
        leading=14,
        spaceAfter=4,
    )

    story.append(Paragraph("LendSynthetix", title_style))
    story.append(Paragraph("AI Credit War Room — Official Appraisal Report", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=COLOR_BORDER, spaceAfter=12))

    final_rec = (report_data.get("final_decision") or {}).get("final_recommendation", "UNKNOWN")
    meta_data = [
        ["Document ID", verification["document_id"]],
        ["Collection", collection_name],
        ["Generated", verification["generated_at"]],
        ["Report Type", "Credit Appraisal Note (AI-Assisted)"],
        ["Classification", "CONFIDENTIAL — For Authorised Review Only"],
    ]
    meta_table = Table(meta_data, colWidths=[45 * mm, 125 * mm])
    meta_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TEXTCOLOR", (0, 0), (0, -1), COLOR_TEXT_DIM),
                ("TEXTCOLOR", (1, 0), (1, -1), COLOR_TEXT_LIGHT),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [COLOR_CARD, colors.HexColor("#1e2535")]),
                ("GRID", (0, 0), (-1, -1), 0.25, COLOR_BORDER),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(meta_table)
    story.append(Spacer(1, 12))

    verdict_color = {"APPROVE": COLOR_GREEN, "REJECT": COLOR_RED}.get(final_rec.upper(), COLOR_AMBER)
    verdict_icon = {"APPROVE": "APPROVED", "REJECT": "REJECTED"}.get(final_rec.upper(), "CONDITIONAL APPROVAL")
    verdict_style = ParagraphStyle(
        "Verdict",
        fontSize=20,
        textColor=verdict_color,
        fontName="Helvetica-Bold",
        alignment=TA_CENTER,
        borderWidth=1.5,
        borderColor=verdict_color,
        borderPad=12,
        backColor=colors.HexColor("#0f1117"),
    )
    story.append(Paragraph(verdict_icon, verdict_style))
    story.append(Spacer(1, 16))

    qr_flowable = _build_qr_flowable(verification, final_rec)
    integrity_lines = [
        "<b>SHA-256 Hash</b>",
        f"<font name='Courier' size='7'>{verification['sha256_hash']}</font>",
        "",
        "<b>HMAC-SHA256 Signature</b>",
        f"<font name='Courier' size='7'>{verification['server_signature']}</font>",
        "",
        f"<b>Algorithm:</b> {verification['algorithm']}",
        f"<b>Canonical Length:</b> {verification['canonical_length']} bytes",
        "",
        f"<font size='7' color='#94a3b8'>{verification['verification_note']}</font>",
    ]
    integrity_para = Paragraph(
        "<br/>".join(integrity_lines),
        ParagraphStyle("Integrity", fontSize=8, textColor=COLOR_TEXT_LIGHT, fontName="Helvetica", leading=13),
    )
    integrity_table = Table([[integrity_para, qr_flowable]], colWidths=[130 * mm, 38 * mm])
    integrity_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), COLOR_CARD),
                ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(integrity_table)
    story.append(PageBreak())

    story.append(Paragraph("Financial Analysis", section_header))
    fa = report_data.get("financial_analysis") or {}
    metrics = fa.get("metrics") or fa
    metric_rows = []
    for field, label, note in [
        ("dscr", "DSCR", ">= 1.25 required"),
        ("ebitda_margin", "EBITDA Margin", "Higher = stronger ops"),
        ("revenue_growth", "Revenue Growth", "YoY %"),
        ("debt_trend", "Debt Trend", "DECREASING preferred"),
    ]:
        metric_rows.append([label, str(metrics.get(field, fa.get(field, "N/A"))), note])
    altman = fa.get("altman_z") or report_data.get("altman_z") or {}
    if altman:
        metric_rows.append(
            [
                "Altman Z-Score",
                f"{altman.get('z_score', 'N/A')} ({altman.get('z_zone', 'N/A')})",
                str(altman.get("z_interpretation", ""))[:60],
            ]
        )
    m_table = Table([["Metric", "Value", "Benchmark"]] + metric_rows, colWidths=[55 * mm, 45 * mm, 68 * mm])
    m_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), COLOR_BLUE),
                ("TEXTCOLOR", (0, 0), (-1, 0), COLOR_WHITE),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [COLOR_CARD, colors.HexColor("#1e2535")]),
                ("TEXTCOLOR", (0, 1), (-1, -1), COLOR_TEXT_LIGHT),
                ("GRID", (0, 0), (-1, -1), 0.25, COLOR_BORDER),
            ]
        )
    )
    story.append(m_table)

    for key, title, color in [
        ("sales_memo", "Sales Agent Memo", COLOR_GREEN),
        ("risk_memo", "Risk Agent Memo", COLOR_RED),
        ("sales_rebuttal", "Sales Rebuttal", COLOR_AMBER),
        ("compliance_memo", "Compliance Agent Memo", COLOR_PURPLE),
        ("sentiment_memo", "Sentiment Analysis", COLOR_BLUE),
    ]:
        memo = report_data.get(key) or {}
        if not memo:
            continue
        story.append(
            Paragraph(
                title,
                ParagraphStyle(f"Memo_{key}", fontSize=11, textColor=color, fontName="Helvetica-Bold", spaceBefore=12, spaceAfter=4),
            )
        )
        for field, value in list(memo.items())[:6]:
            if isinstance(value, list):
                value = " • ".join(str(v) for v in value[:3])
            story.append(Paragraph(f"<b>{field.replace('_', ' ').title()}:</b> {str(value)[:200]}", body_style))

    story.append(PageBreak())
    story.append(Paragraph("Risk Assessment", section_header))
    rs = report_data.get("risk_score") or {}
    score_val = rs.get("risk_score", "N/A")
    score_level = rs.get("risk_level", "N/A")
    story.append(
        Paragraph(
            f"XGBoost Risk Score: {score_val}/100 — {score_level}",
            ParagraphStyle("ScoreHeader", fontSize=14, textColor=COLOR_TEXT_LIGHT, fontName="Helvetica-Bold", spaceAfter=8),
        )
    )
    shap = rs.get("shap_explanation") or []
    if shap:
        shap_rows = [["Feature", "Impact (pts)", "Direction"]]
        for item in shap:
            shap_rows.append([item.get("feature", ""), str(item.get("impact", "")), item.get("direction", "")])
        shap_table = Table(shap_rows, colWidths=[80 * mm, 40 * mm, 48 * mm])
        shap_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), COLOR_PURPLE),
                    ("TEXTCOLOR", (0, 0), (-1, 0), COLOR_WHITE),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [COLOR_CARD, colors.HexColor("#1e2535")]),
                    ("TEXTCOLOR", (0, 1), (-1, -1), COLOR_TEXT_LIGHT),
                    ("GRID", (0, 0), (-1, -1), 0.25, COLOR_BORDER),
                ]
            )
        )
        story.append(shap_table)
    stress = report_data.get("stress_test_results") or {}
    if stress:
        story.append(Spacer(1, 14))
        stress_rows = [["Scenario", "Risk Score", "Risk Level", "Grade", "Delta vs Base"]]
        for scenario, data in stress.items():
            stress_rows.append(
                [
                    scenario.replace("_", " ").title(),
                    str(data.get("risk_score", "N/A")),
                    data.get("risk_level", "N/A"),
                    data.get("predicted_grade", "N/A"),
                    str(data.get("delta_vs_base", "N/A")),
                ]
            )
        st_table = Table(stress_rows, colWidths=[55 * mm, 30 * mm, 35 * mm, 22 * mm, 26 * mm])
        st_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), COLOR_RED),
                    ("TEXTCOLOR", (0, 0), (-1, 0), COLOR_WHITE),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [COLOR_CARD, colors.HexColor("#1e2535")]),
                    ("TEXTCOLOR", (0, 1), (-1, -1), COLOR_TEXT_LIGHT),
                    ("GRID", (0, 0), (-1, -1), 0.25, COLOR_BORDER),
                ]
            )
        )
        story.append(st_table)

    story.append(PageBreak())
    story.append(Paragraph("Final Decision — Moderator Synthesis", section_header))
    final = report_data.get("final_decision") or {}
    story.append(Paragraph(final.get("reasoning", "No reasoning provided."), body_style))
    conditions = final.get("conditions") or []
    if conditions:
        story.append(Spacer(1, 8))
        story.append(Paragraph("Conditions for Approval:", ParagraphStyle("CondHeader", fontSize=10, textColor=COLOR_AMBER, fontName="Helvetica-Bold", spaceAfter=4)))
        for condition in conditions:
            story.append(Paragraph(f"• {condition}", body_style))

    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=0.5, color=COLOR_BORDER, spaceAfter=12))
    sig_data = [
        ["Field", "Value"],
        ["Document ID", verification["document_id"]],
        ["SHA-256", verification["sha256_hash"]],
        ["HMAC Signature", verification["server_signature"]],
        ["Generated At", verification["generated_at"]],
        ["Algorithm", verification["algorithm"]],
        ["Canonical Size", f"{verification['canonical_length']} bytes"],
    ]
    sig_table = Table(sig_data, colWidths=[45 * mm, 123 * mm])
    sig_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), COLOR_CARD),
                ("TEXTCOLOR", (0, 0), (-1, 0), COLOR_TEXT_DIM),
                ("FONTNAME", (0, 0), (-1, -1), "Courier"),
                ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                ("TEXTCOLOR", (0, 1), (0, -1), COLOR_TEXT_DIM),
                ("TEXTCOLOR", (1, 1), (1, -1), COLOR_TEXT_LIGHT),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [COLOR_CARD, colors.HexColor("#1e2535")]),
                ("GRID", (0, 0), (-1, -1), 0.25, COLOR_BORDER),
            ]
        )
    )
    story.append(sig_table)
    story.append(Spacer(1, 16))

    disclaimer = (
        "LEGAL DISCLAIMER: This document was generated by the LendSynthetix "
        "AI Credit War Room system. It is AI-assisted appraisal output and "
        "requires authorised human approval under applicable policy and regulation. "
        "Any modification after generation invalidates integrity proofs."
    )
    story.append(
        Paragraph(
            disclaimer,
            ParagraphStyle(
                "Disclaimer",
                fontSize=7.5,
                textColor=COLOR_TEXT_DIM,
                fontName="Helvetica",
                leading=11,
                borderWidth=0.5,
                borderColor=COLOR_BORDER,
                borderPad=8,
                backColor=COLOR_CARD,
            ),
        )
    )
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def generate_report_pdf(war_room_output: dict, output_dir: Path = Path("outputs")) -> dict:
    """
    Backward-compatible report generator used by war_room_graph report_node.
    Writes JSON + signed PDF artifacts and returns metadata.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    case_id = war_room_output.get("case_id") or str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()
    war_room_output["case_id"] = case_id
    war_room_output["generated_at_utc"] = timestamp
    war_room_output["pipeline_version"] = "2.0.0"

    collection_name = war_room_output.get("collection_name", "loan_documents")
    hash_info = generate_report_hash(war_room_output)
    json_hash = hash_info["sha256"]

    json_path = output_dir / f"{case_id}.json"
    with open(json_path, "w", encoding="utf-8") as file_obj:
        json.dump(war_room_output, file_obj, indent=2, sort_keys=True, default=str)

    pdf_bytes = generate_signed_pdf(war_room_output, collection_name)
    pdf_path = output_dir / f"{case_id}_signed_report.pdf"
    with open(pdf_path, "wb") as file_obj:
        file_obj.write(pdf_bytes)
    pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()

    final_decision = war_room_output.get("final_decision") or {}
    return {
        "case_id": case_id,
        "pdf_path": str(pdf_path),
        "json_path": str(json_path),
        "json_hash": json_hash,
        "pdf_hash": pdf_hash,
        "timestamp_utc": timestamp,
        "verdict": final_decision.get("final_recommendation", "UNKNOWN"),
    }
