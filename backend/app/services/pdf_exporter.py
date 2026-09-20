"""
app/services/pdf_exporter.py
----------------------------
High-fidelity, professional PDF generator using ReportLab.
Produces server-side PDFs with PreHab AI styling, structured tables,
metric callouts, disclaimer banners, and dynamic page numbering.
"""
from __future__ import annotations

import io
from datetime import datetime
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
    HRFlowable,
)

from app.schemas.reports import FullReportPayload, ReportTypeEnum


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute and print 'Page X of Y' in the footer.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            super().showPage()
        super().save()

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        
        # Footer text
        footer_text = "PreHab AI Automated Assessment System • Confidential • For Screening Purposes Only"
        self.drawString(40, 30, footer_text)
        
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(letter[0] - 40, 30, page_str)
        
        # Bottom divider
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(40, 42, letter[0] - 40, 42)
        
        self.restoreState()


def generate_pdf_report(payload: FullReportPayload) -> bytes:
    """
    Generates a professionally formatted PDF document from a FullReportPayload.
    Returns the binary PDF bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=55,
    )

    styles = getSampleStyleSheet()
    
    # Custom Typography
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=3,
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#475569"),
        spaceAfter=12,
    )
    section_title = ParagraphStyle(
        "SectionTitle",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#1E3A8A"),
        spaceBefore=10,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#334155"),
    )
    bold_body = ParagraphStyle(
        "BoldBody",
        parent=body_style,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#0F172A"),
    )
    disclaimer_style = ParagraphStyle(
        "Disclaimer",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#475569"),
    )

    story = []

    # ── BRAND HEADER ────────────────────────────────────────────────────────
    brand_table = Table(
        [
            [
                Paragraph("<b>PREHAB AI</b>", ParagraphStyle("BrandLogo", fontName="Helvetica-Bold", fontSize=14, leading=16, textColor=colors.HexColor("#2563EB"))),
                Paragraph(f"<b>Generated:</b> {payload.generated_at.strftime('%Y-%m-%d %H:%M UTC')}<br/><b>By:</b> {payload.generated_by_name} ({payload.generated_by_role})", ParagraphStyle("MetaR", parent=body_style, alignment=2)),
            ]
        ],
        colWidths=[200, 330],
    )
    brand_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(brand_table)
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2563EB"), spaceAfter=10))

    # ── REPORT TITLE ────────────────────────────────────────────────────────
    story.append(Paragraph(payload.report_title.upper(), title_style))
    story.append(Paragraph(f"{payload.report_type_label} • PreHab AI Biomechanical Evaluation", subtitle_style))

    # ── ATHLETE & ASSESSMENT METADATA BOX ───────────────────────────────────
    ath = payload.athlete
    ass = payload.assessment

    col_w = [110, 155, 110, 155]
    meta_data = [
        [
            Paragraph("Athlete Name:", bold_body), Paragraph(str(ath.name), body_style),
            Paragraph("Sport / Position:", bold_body), Paragraph(f"{ath.sport} / {ath.position}", body_style),
        ],
        [
            Paragraph("Age / Height / Weight:", bold_body), Paragraph(f"{ath.age} yrs / {ath.height} cm / {ath.weight} kg", body_style),
            Paragraph("Dominant Leg:", bold_body), Paragraph(str(ath.dominant_leg), body_style),
        ],
        [
            Paragraph("Injury Status:", bold_body), Paragraph(str(ath.injury_status), body_style),
            Paragraph("Assigned Coach:", bold_body), Paragraph(str(ath.coach_name), body_style),
        ],
    ]

    if ass:
        meta_data.append([
            Paragraph("Assessment Video:", bold_body), Paragraph(str(ass.title or ass.original_filename or "N/A"), body_style),
            Paragraph("Assessment Date:", bold_body), Paragraph(ass.assessment_date.strftime('%Y-%m-%d %H:%M') if ass.assessment_date else "N/A", body_style),
        ])
        meta_data.append([
            Paragraph("FPS / Duration:", bold_body), Paragraph(f"{ass.fps} fps / {ass.duration_seconds}s", body_style),
            Paragraph("Frames Analyzed:", bold_body), Paragraph(str(ass.frames_processed), body_style),
        ])

    meta_table = Table(meta_data, colWidths=col_w)
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#CBD5E1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 12))

    # ── REPORT-SPECIFIC CONTENT ─────────────────────────────────────────────
    data_dict = payload.data.model_dump() if hasattr(payload.data, "model_dump") else payload.data

    if payload.report_type == ReportTypeEnum.INJURY_RISK:
        # 1. Injury Risk Summary
        story.append(Paragraph("1. Overall Risk Screening Classification", section_title))
        risk_score = data_dict.get("overall_risk_score", "Data unavailable")
        risk_level = str(data_dict.get("risk_level", "Data unavailable")).upper()

        risk_color = "#10B981" if risk_level == "LOW" else ("#F59E0B" if risk_level in ("MODERATE", "MEDIUM") else "#EF4444")

        score_table = Table(
            [
                [
                    Paragraph(f"<b>RISK SCORE: {risk_score} / 100</b>", ParagraphStyle("R1", fontName="Helvetica-Bold", fontSize=13, textColor=colors.HexColor(risk_color))),
                    Paragraph(f"<b>RISK LEVEL: {risk_level}</b>", ParagraphStyle("R2", fontName="Helvetica-Bold", fontSize=13, textColor=colors.HexColor(risk_color), alignment=2)),
                ]
            ],
            colWidths=[265, 265],
        )
        score_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F1F5F9")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor(risk_color)),
            ("PADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(score_table)
        story.append(Spacer(1, 8))

        # Risk Factors Table
        factors = data_dict.get("risk_factors", [])
        if factors:
            story.append(Paragraph("2. Contributing Risk Factors (5-Factor Model)", section_title))
            fac_data = [["Factor Name", "Score", "Status", "Description"]]
            for f in factors:
                fac_data.append([
                    Paragraph(f.get("factor_name", ""), bold_body),
                    str(f.get("contribution_score", "")),
                    f.get("status", ""),
                    Paragraph(f.get("description", ""), body_style),
                ])
            fac_table = Table(fac_data, colWidths=[150, 50, 60, 270])
            fac_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("PADDING", (0, 0), (-1, -1), 5),
            ]))
            story.append(fac_table)
            story.append(Spacer(1, 10))

        # Recommendations
        recs = data_dict.get("recommendations")
        if recs:
            story.append(Paragraph("3. Recommended Corrective Action Plan", section_title))
            rec_items = recs.get("exercise_recommendations", []) + recs.get("mobility_recommendations", []) + recs.get("strengthening_recommendations", [])
            if rec_items:
                r_rows = [["Priority", "Title & Category", "Guidance & Exercises"]]
                for r in rec_items[:6]:
                    r_rows.append([
                        r.get("priority", "").upper(),
                        Paragraph(f"<b>{r.get('title', '')}</b><br/><i>{r.get('category', '')}</i>", body_style),
                        Paragraph(f"{r.get('description', '')}<br/><b>Action:</b> {', '.join(r.get('exercises', []))}", body_style),
                    ])
                r_table = Table(r_rows, colWidths=[55, 145, 330])
                r_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ("PADDING", (0, 0), (-1, -1), 4),
                ]))
                story.append(r_table)

    elif payload.report_type == ReportTypeEnum.BIOMECHANICAL:
        story.append(Paragraph("1. Core Biomechanical Scores & Metrics", section_title))
        bio_rows = [
            ["Metric Name", "Value", "Status / Notes"],
            ["Symmetry Score", str(data_dict.get("symmetry_score", "Data unavailable")), "Bilateral kinematics symmetry"],
            ["Fatigue Score", str(data_dict.get("fatigue_score", "Data unavailable")), "Kinematic degradation score"],
            ["Movement Quality", str(data_dict.get("movement_quality", "Data unavailable")), "Pose stability score"],
            ["Joint Alignment", str(data_dict.get("joint_alignment", "Data unavailable")), "Lower extremity axis alignment"],
            ["Trunk Lean", str(data_dict.get("trunk_lean", "Data unavailable")), "Sagittal/coronal trunk deviation"],
            ["Knee Valgus Index", str(data_dict.get("knee_valgus", "Data unavailable")), "Medial knee collapse indicator"],
            ["Hip Stability", str(data_dict.get("hip_stability", "Data unavailable")), "Pelvic and hip drop stability"],
            ["Stride Length", str(data_dict.get("stride_length", "Data unavailable")), "Kinematic step stride length"],
            ["LESS Score", f"{data_dict.get('less_score', 'Data unavailable')} / {data_dict.get('less_max', 'Data unavailable')}", f"Classification: {data_dict.get('less_classification', 'Data unavailable')}"],
        ]
        bio_table = Table(bio_rows, colWidths=[150, 100, 280])
        bio_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("PADDING", (0, 0), (-1, -1), 4.5),
        ]))
        story.append(bio_table)
        story.append(Spacer(1, 10))

        # Asymmetries
        asyms = data_dict.get("asymmetries", [])
        if asyms:
            story.append(Paragraph("2. Bilateral Asymmetry Findings", section_title))
            asym_rows = [["Body Region / Joint", "Left", "Right", "Difference", "Status"]]
            for a in asyms:
                asym_rows.append([
                    a.get("body_region", ""),
                    str(a.get("left_value", "")),
                    str(a.get("right_value", "")),
                    f"{a.get('asymmetry_percentage', '')}°",
                    a.get("status", ""),
                ])
            asym_table = Table(asym_rows, colWidths=[160, 80, 80, 80, 130])
            asym_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("PADDING", (0, 0), (-1, -1), 4.5),
            ]))
            story.append(asym_table)

    elif payload.report_type == ReportTypeEnum.MOVEMENT:
        story.append(Paragraph("1. Landing Error Scoring System (LESS) Findings", section_title))
        less_score = data_dict.get("less_total_score", "Data unavailable")
        less_max = data_dict.get("less_max_score", "Data unavailable")
        less_class = data_dict.get("less_classification", "Data unavailable")

        story.append(Paragraph(f"<b>LESS Overall Score:</b> {less_score} / {less_max} &nbsp;&nbsp;|&nbsp;&nbsp; <b>Classification:</b> {less_class}", bold_body))
        story.append(Spacer(1, 6))

        items = data_dict.get("less_items", [])
        if items:
            item_rows = [["#", "Item Name", "Status", "Score", "Measured", "Details / Reason"]]
            for it in items:
                status_val = it.get("status", "")
                st_color = "#10B981" if status_val == "PASS" else ("#EF4444" if status_val == "ERROR" else "#64748B")
                item_rows.append([
                    str(it.get("item_number", "")),
                    Paragraph(it.get("item_name", ""), body_style),
                    Paragraph(f"<b>{status_val}</b>", ParagraphStyle("ST", parent=body_style, textColor=colors.HexColor(st_color))),
                    str(it.get("score") if it.get("score") is not None else "-"),
                    str(it.get("measured_value", "N/A")),
                    Paragraph(str(it.get("reason") or "Standard criteria met"), body_style),
                ])
            item_table = Table(item_rows, colWidths=[20, 140, 50, 35, 65, 220])
            item_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("PADDING", (0, 0), (-1, -1), 3.5),
            ]))
            story.append(item_table)

    elif payload.report_type == ReportTypeEnum.ATHLETE_PERFORMANCE:
        story.append(Paragraph("1. Training Workload & Fatigue Profile", section_title))
        workload_rows = [
            ["Weekly Sessions", "Avg Duration", "Avg RPE (1-10)", "Weekly Load (AU)", "Current Fatigue"],
            [
                str(data_dict.get("training_sessions_per_week", "Data unavailable")),
                f"{data_dict.get('average_session_duration', 'Data unavailable')} min",
                str(data_dict.get("average_session_rpe", "Data unavailable")),
                f"{data_dict.get('weekly_training_load', 'Data unavailable')} AU",
                f"{data_dict.get('current_fatigue_level', 'Data unavailable')} / 10",
            ],
        ]
        workload_table = Table(workload_rows, colWidths=[105, 105, 105, 105, 110])
        workload_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("PADDING", (0, 0), (-1, -1), 5),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]))
        story.append(workload_table)
        story.append(Spacer(1, 10))

        # Assessment History Table
        history = data_dict.get("assessment_history", [])
        if history:
            story.append(Paragraph("2. Longitudinal Assessment History", section_title))
            hist_rows = [["Date", "Assessment Title", "Risk Score", "Risk Level", "LESS Score", "Symmetry"]]
            for h in history:
                dt_str = datetime.fromisoformat(h.get("date")).strftime("%Y-%m-%d") if h.get("date") else "N/A"
                hist_rows.append([
                    dt_str,
                    Paragraph(h.get("title", "Assessment"), body_style),
                    str(h.get("risk_score", "N/A")),
                    str(h.get("risk_level", "N/A")),
                    str(h.get("less_score", "N/A")),
                    str(h.get("symmetry_score", "N/A")),
                ])
            hist_table = Table(hist_rows, colWidths=[70, 160, 75, 75, 75, 75])
            hist_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("PADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(hist_table)

    elif payload.report_type == ReportTypeEnum.REHABILITATION:
        story.append(Paragraph("1. Recovery & Reassessment Status", section_title))
        status_rows = [
            ["Injury Status", "Needs Reassessment", "Days Since Last Assessment", "Guidance"],
            [
                str(data_dict.get("current_injury_status", "Data unavailable")),
                "YES" if data_dict.get("needs_reassessment") else "NO",
                str(data_dict.get("days_since_last_assessment", "Data unavailable")),
                Paragraph(data_dict.get("reassessment_recommendation", ""), body_style),
            ],
        ]
        status_table = Table(status_rows, colWidths=[100, 110, 120, 200])
        status_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("PADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(status_table)
        story.append(Spacer(1, 10))

        # Injury History
        injuries = data_dict.get("injury_records", [])
        if injuries:
            story.append(Paragraph("2. Documented Injury History", section_title))
            inj_rows = [["Injury Type", "Body Part", "Severity", "Date", "Recovery", "Status", "Remarks"]]
            for inj in injuries:
                inj_rows.append([
                    str(inj.get("injury_type", "N/A")),
                    str(inj.get("body_part", "N/A")),
                    str(inj.get("severity", "N/A")),
                    str(inj.get("injury_date", "N/A")),
                    str(inj.get("recovery_date", "N/A")),
                    str(inj.get("status", "N/A")),
                    Paragraph(str(inj.get("remarks", "") or "No remarks"), body_style),
                ])
            inj_table = Table(inj_rows, colWidths=[80, 70, 55, 60, 60, 65, 140])
            inj_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("PADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(inj_table)
            story.append(Spacer(1, 10))

        # Notes
        notes = data_dict.get("rehabilitation_notes")
        if notes and notes != "Data unavailable":
            story.append(Paragraph("3. Clinical / Coaching Notes", section_title))
            story.append(Paragraph(str(notes), body_style))

    # ── AI RISK DISCLAIMER CALLOUT ──────────────────────────────────────────
    story.append(Spacer(1, 14))
    disclaimer_box = Table(
        [
            [
                Paragraph(
                    f"<b>AI SCREENING DISCLAIMER:</b> {payload.disclaimer}",
                    disclaimer_style,
                )
            ]
        ],
        colWidths=[530],
    )
    disclaimer_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FEF3C7")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#F59E0B")),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(KeepTogether([disclaimer_box]))

    # Build PDF
    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    return buffer.getvalue()
