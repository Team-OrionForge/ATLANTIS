"""Generates Project Atlantis Physical Measurements & Detection Specification PDF document."""

import os
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


def generate_pdf():
    workspace_dir = Path("c:/Users/VISHAL/OneDrive/Desktop/Atlantis")
    output_pdf_path = workspace_dir / "Project_Atlantis_Physical_Measurements_Specification.pdf"
    artifact_dir = Path(r"C:\Users\VISHAL\.gemini\antigravity-ide\brain\8fcaa57f-4f48-4ef7-9798-36d940f3657f")
    artifact_pdf_path = artifact_dir / "Project_Atlantis_Physical_Measurements_Specification.pdf"

    doc = SimpleDocTemplate(
        str(output_pdf_path),
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()

    # Custom Palette
    NAVY = colors.HexColor("#0B1325")
    DARK_BLUE = colors.HexColor("#121E36")
    CYAN = colors.HexColor("#007799")
    LIGHT_BG = colors.HexColor("#F4F7FA")
    ACCENT_LINE = colors.HexColor("#00A8CC")
    TEXT_DARK = colors.HexColor("#1E293B")

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=NAVY,
        alignment=TA_LEFT,
        spaceAfter=4,
    )

    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=CYAN,
        alignment=TA_LEFT,
        spaceAfter=15,
    )

    section_heading = ParagraphStyle(
        "SecHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=NAVY,
        spaceBefore=12,
        spaceAfter=6,
    )

    body_style = ParagraphStyle(
        "BodyTextCustom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13.5,
        textColor=TEXT_DARK,
        spaceAfter=6,
    )

    code_box_style = ParagraphStyle(
        "CodeBox",
        parent=styles["Normal"],
        fontName="Courier-Bold",
        fontSize=9,
        leading=12,
        textColor=NAVY,
        backColor=LIGHT_BG,
        borderColor=ACCENT_LINE,
        borderWidth=0.5,
        borderPadding=6,
        spaceAfter=8,
    )

    table_header_style = ParagraphStyle(
        "TableHeader",
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=11,
        textColor=colors.white,
        alignment=TA_LEFT,
    )

    table_cell_style = ParagraphStyle(
        "TableCell",
        fontName="Helvetica",
        fontSize=8.5,
        leading=11.5,
        textColor=TEXT_DARK,
        alignment=TA_LEFT,
    )

    table_cell_bold = ParagraphStyle(
        "TableCellBold",
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11.5,
        textColor=NAVY,
        alignment=TA_LEFT,
    )

    story = []

    # Title & Header Banner
    story.append(Paragraph("PROJECT ATLANTIS", title_style))
    story.append(
        Paragraph(
            "Physical Measurements, Pixel-Level Metrics & Mathematical Target Classification Specification",
            subtitle_style,
        )
    )
    story.append(HRFlowable(width="100%", thickness=1.5, color=ACCENT_LINE, spaceAfter=15))

    # 1. Executive Summary
    story.append(Paragraph("1. System Architecture Overview", section_heading))
    story.append(
        Paragraph(
            "Project Atlantis employs a physics-informed dual-engine pipeline combining Side-Scan Sonar (SSS) acoustic ray trigonometry, 8-bit backscatter intensity statistics, boundary micro-roughness analysis, WGS84 geodetic navigation, and fine-tuned YOLOv8 deep learning segmentation. Below is the complete mathematical and physical specification.",
            body_style,
        )
    )

    # 2. Pixel-Level Intensity & Texture Metrics Table
    story.append(Paragraph("2. Pixel-Level Acoustic Intensity Statistics (8-Bit Space)", section_heading))
    story.append(
        Paragraph(
            "In 8-bit acoustic waterfall images, pixel intensity values range from 0 (total sound absorption/shadow) to 255 (maximum specular acoustic reflection).",
            body_style,
        )
    )

    data_intensity = [
        [
            Paragraph("Physical Metric", table_header_style),
            Paragraph("Mathematical Formula / Variable", table_header_style),
            Paragraph("Threshold", table_header_style),
            Paragraph("Physical / Acoustic Meaning", table_header_style),
        ],
        [
            Paragraph("Trailing Acoustic Shadow Intensity", table_cell_bold),
            Paragraph("I_shadow = (1/N) ∑_{k=5}^{30} I(far_pt + k · r)", table_cell_style),
            Paragraph("I_shadow < 35.0", table_cell_style),
            Paragraph("Blocked sound wave behind protruding seabed target.", table_cell_style),
        ],
        [
            Paragraph("Specular Return Intensity", table_cell_bold),
            Paragraph("I_mean = (1/A_px) ∑_{(x,y) ∈ C} I(x,y)", table_cell_style),
            Paragraph("I_mean ≥ 190.0", table_cell_style),
            Paragraph("High acoustic impedance return (metal debris, hull).", table_cell_style),
        ],
        [
            Paragraph("Micro-Roughness Texture Energy", table_cell_bold),
            Paragraph("E_texture = Var(∇² I_target)", table_cell_style),
            Paragraph("E_texture > 15.0", table_cell_style),
            Paragraph("Laplacian variance confirming planar/benthic debris (plastic/nets).", table_cell_style),
        ],
        [
            Paragraph("Internal Target Uniformity", table_cell_bold),
            Paragraph("σ_I = √[ (1/A_px) ∑ (I - I_mean)² ]", table_cell_style),
            Paragraph("σ_I < 35.0", table_cell_style),
            Paragraph("Uniform return characteristic of manufactured containers.", table_cell_style),
        ],
        [
            Paragraph("Channel Monochromicity", table_cell_bold),
            Paragraph("Δ_RGB = ( |R-G| + |G-B| ) / 2", table_cell_style),
            Paragraph("Δ_RGB < 25.0", table_cell_style),
            Paragraph("Monochromatic sonar colormap validation; rejects RGB photos.", table_cell_style),
        ],
    ]

    t_intensity = Table(data_intensity, colWidths=[110, 150, 80, 190])
    t_intensity.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), DARK_BLUE),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ])
    )
    story.append(t_intensity)
    story.append(Spacer(1, 10))

    # 3. Acoustic Ray Geometry & Elevation
    story.append(Paragraph("3. Acoustic Ray Geometry & Target Elevation (h)", section_heading))
    story.append(
        Paragraph(
            "Using similar triangles in acoustic propagation geometry, physical target height <i>h</i> above seabed is derived from towfish altitude <i>H</i>, acoustic shadow length <i>L<sub>s</sub></i>, and slant range <i>R<sub>s</sub></i>:",
            body_style,
        )
    )
    story.append(Paragraph("<b>Formula:</b> &nbsp;&nbsp; <b>h = ( H · L<sub>s</sub> ) / R<sub>s</sub></b>", code_box_style))
    story.append(
        Paragraph(
            "where <i>L<sub>s</sub> = shadow_length_px · resolution</i> &nbsp;and&nbsp; <i>R<sub>s</sub> = slant_range_px · resolution</i>.",
            body_style,
        )
    )

    # 4. Slant-to-Ground Range Correction
    story.append(Paragraph("4. Pythagorean Slant-to-Ground Range Correction (R_g)", section_heading))
    story.append(
        Paragraph(
            "Side-Scan Sonar measures 3D slant range (R<sub>s</sub>). To obtain true horizontal ground range (R<sub>g</sub>) along the seabed:",
            body_style,
        )
    )
    story.append(Paragraph("<b>Formula:</b> &nbsp;&nbsp; <b>R<sub>g</sub> = √( R<sub>s</sub>² - H² )</b>", code_box_style))

    # 5. Geometric Classification Rules
    story.append(Paragraph("5. Geometric Ratio & Feature Decision Rules", section_heading))

    data_geom = [
        [
            Paragraph("Target Taxonomy Class", table_header_style),
            Paragraph("Geometric & Feature Decision Rule", table_header_style),
            Paragraph("Physical Signature", table_header_style),
        ],
        [
            Paragraph("Pipeline", table_cell_bold),
            Paragraph("Aspect Ratio ≥ 8.0 &nbsp;(max(W,H) / min(W,H))", table_cell_style),
            Paragraph("Long continuous acoustic corridor.", table_cell_style),
        ],
        [
            Paragraph("Shipwreck", table_cell_bold),
            Paragraph("Area m² ≥ 200.0 m² &nbsp;(A_px · res²)", table_cell_style),
            Paragraph("Macro-scale hull structure & long shadow.", table_cell_style),
        ],
        [
            Paragraph("Metal Debris", table_cell_bold),
            Paragraph("I_mean ≥ 190.0 & Irregularity (P²/A) ≤ 25.0", table_cell_style),
            Paragraph("High acoustic return, compact perimeter.", table_cell_style),
        ],
        [
            Paragraph("Chemical Container", table_cell_bold),
            Paragraph("Aspect Ratio ∈ [1.0, 2.5] & σ_I < 35.0", table_cell_style),
            Paragraph("Rectangular box with uniform internal return.", table_cell_style),
        ],
        [
            Paragraph("Ghost Net", table_cell_bold),
            Paragraph("Boundary Irregularity (P²/A) ≥ 25.0", table_cell_style),
            Paragraph("Twisted non-rigid irregular polyline mesh.", table_cell_style),
        ],
        [
            Paragraph("Marine Plastic", table_cell_bold),
            Paragraph("BENTHIC_DRAPED verdict & I_mean < 140.0", table_cell_style),
            Paragraph("Flat planar sheet, minimal acoustic shadow.", table_cell_style),
        ],
    ]

    t_geom = Table(data_geom, colWidths=[120, 210, 200])
    t_geom.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), DARK_BLUE),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ])
    )
    story.append(t_geom)
    story.append(Spacer(1, 10))

    # 6. WGS84 Geodetic Navigation
    story.append(Paragraph("6. WGS84 Geodetic Navigation Projection", section_heading))
    story.append(
        Paragraph(
            "Converts pixel offset (x_px, y_px) and ground range (R_g) into precise WGS84 latitude (φ₂) and longitude (λ₂) using spherical haversine projection:",
            body_style,
        )
    )
    story.append(
        Paragraph(
            "<b>Distance:</b> d = √( (y_px · res)² + R_g² ) &nbsp;&nbsp;|&nbsp;&nbsp; <b>Bearing:</b> θ = θ_heading + atan2(R_g, y_px · res)<br/>"
            "<b>φ₂ = asin( sin φ₁ cos(d/R_e) + cos φ₁ sin(d/R_e) cos θ )</b><br/>"
            "<b>λ₂ = λ₁ + atan2( sin θ sin(d/R_e) cos φ₁, cos(d/R_e) - sin φ₁ sin φ₂ )</b> &nbsp;&nbsp; (where R_e = 6,371,000 m)",
            code_box_style,
        )
    )

    # 7. Hazard Priority Index (HPI)
    story.append(Paragraph("7. Hazard Priority Index (HPI) Threat Model", section_heading))
    story.append(
        Paragraph(
            "Multi-factor environmental risk score combining target taxonomy, physical footprint, height, and ecological severity:",
            body_style,
        )
    )
    story.append(
        Paragraph(
            "<b>HPI = 0.35 · S_class + 0.25 · S_span + 0.20 · S_depth + 0.20 · S_eco</b><br/>"
            "where &nbsp; <i>S_span = min(1.0, span_m / 20.0)</i> &nbsp;and&nbsp; <i>S_depth = min(1.0, h / 10.0)</i>",
            code_box_style,
        )
    )

    data_hpi = [
        [Paragraph("HPI Score Band", table_header_style), Paragraph("Risk Tier", table_header_style), Paragraph("Operational Protocol", table_header_style)],
        [Paragraph("HPI ≥ 0.75", table_cell_bold), Paragraph("CRITICAL", table_cell_bold), Paragraph("Immediate ROV dispatch & hazardous intervention.", table_cell_style)],
        [Paragraph("0.50 ≤ HPI < 0.75", table_cell_bold), Paragraph("HIGH", table_cell_bold), Paragraph("Priority survey logging & ecological warning flag.", table_cell_style)],
        [Paragraph("0.25 ≤ HPI < 0.50", table_cell_bold), Paragraph("MODERATE", table_cell_bold), Paragraph("Standard oceanographic mapping catalog entry.", table_cell_style)],
        [Paragraph("HPI < 0.25", table_cell_bold), Paragraph("LOW", table_cell_bold), Paragraph("Background seabed object record.", table_cell_style)],
    ]

    t_hpi = Table(data_hpi, colWidths=[120, 110, 300])
    t_hpi.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), DARK_BLUE),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ])
    )
    story.append(t_hpi)

    doc.build(story)

    # Copy to artifact dir as well
    if artifact_dir.exists():
        import shutil
        shutil.copy(output_pdf_path, artifact_pdf_path)

    print(f"[OK] Generated PDF report at: {output_pdf_path}")


if __name__ == "__main__":
    generate_pdf()
