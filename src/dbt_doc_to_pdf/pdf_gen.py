import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .er_diagram import build_er_diagram
from .models import ModelInfo

_FONT = "HeiseiKakuGo-W5"
_FONT_BOLD = "HeiseiKakuGo-W5"

_C_PRIMARY = colors.HexColor("#2C3E50")
_C_STAGING = colors.HexColor("#2980B9")
_C_ECO = colors.HexColor("#27AE60")
_C_OTHER = colors.HexColor("#7F8C8D")
_C_HEADER_BG = colors.HexColor("#F4F6F7")
_C_BORDER = colors.HexColor("#BDC3C7")
_C_ROW_ALT = colors.HexColor("#FDFEFE")

_LAYER_LABELS = {
    "staging": "Staging",
    "ecommerce": "Ecommerce",
}
_LAYER_COLORS = {
    "staging": _C_STAGING,
    "ecommerce": _C_ECO,
    "other": _C_OTHER,
}


def _register_fonts() -> None:
    pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    def s(name: str, **kw) -> ParagraphStyle:
        return ParagraphStyle(name, fontName=_FONT, **kw)

    return {
        "cover_title": s("cover_title", fontSize=28, textColor=_C_PRIMARY,
                         alignment=TA_CENTER, spaceAfter=6),
        "cover_sub": s("cover_sub", fontSize=14, textColor=colors.HexColor("#7F8C8D"),
                       alignment=TA_CENTER, spaceAfter=4),
        "cover_meta": s("cover_meta", fontSize=11, textColor=colors.HexColor("#95A5A6"),
                        alignment=TA_CENTER),
        "section": s("section", fontSize=16, textColor=_C_PRIMARY,
                     spaceBefore=12, spaceAfter=4),
        "model_name": s("model_name", fontSize=13, textColor=colors.white,
                        alignment=TA_LEFT),
        "desc": s("desc", fontSize=9, textColor=_C_PRIMARY, spaceAfter=6),
        "normal": s("normal", fontSize=9, textColor=_C_PRIMARY),
        "toc_entry": s("toc_entry", fontSize=10, textColor=_C_PRIMARY, spaceAfter=2),
        "er_title": s("er_title", fontSize=14, textColor=_C_PRIMARY,
                      spaceBefore=10, spaceAfter=6, alignment=TA_CENTER),
    }


def _layer_color(layer: str) -> colors.Color:
    return _LAYER_COLORS.get(layer, _C_OTHER)


def _cover_page(project_name: str, st: dict) -> list:
    page_w, page_h = A4
    return [
        Spacer(1, 80 * mm),
        Paragraph("dbt データカタログ", st["cover_title"]),
        HRFlowable(width="60%", thickness=2, color=_C_PRIMARY, hAlign="CENTER"),
        Spacer(1, 6 * mm),
        Paragraph(f"プロジェクト: {project_name}", st["cover_sub"]),
        Spacer(1, 4 * mm),
        Paragraph(
            f"生成日: {datetime.date.today().strftime('%Y年%m月%d日')}",
            st["cover_meta"],
        ),
        PageBreak(),
    ]


def _toc_page(models: list[ModelInfo], st: dict) -> list:
    items: list = [
        Paragraph("目次", st["section"]),
        HRFlowable(width="100%", thickness=1, color=_C_BORDER),
        Spacer(1, 4 * mm),
    ]
    current_layer = None
    for m in models:
        if m.layer != current_layer:
            current_layer = m.layer
            label = _LAYER_LABELS.get(m.layer, m.layer)
            items.append(Paragraph(f"■ {label}", ParagraphStyle(
                f"toc_layer_{m.layer}", fontName=_FONT, fontSize=10,
                textColor=_layer_color(m.layer), spaceBefore=6, spaceAfter=2,
            )))
        items.append(Paragraph(f"　　{m.name}", st["toc_entry"]))
    items.append(Paragraph("　　ER 図", st["toc_entry"]))
    items.append(PageBreak())
    return items


def _model_section(model: ModelInfo, st: dict) -> list:
    layer_color = _layer_color(model.layer)
    layer_label = _LAYER_LABELS.get(model.layer, model.layer)

    items: list = []

    # Model name header bar
    header_table = Table(
        [[Paragraph(f"  {model.name}", ParagraphStyle(
            "mh", fontName=_FONT, fontSize=13, textColor=colors.white,
        ))]],
        colWidths=["100%"],
    )
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), layer_color),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
    ]))
    items.append(header_table)

    # Meta info table
    meta_data = [
        ["レイヤー", layer_label, "マテリアライズ", model.materialized or "-"],
        ["スキーマ", model.schema or "-", "データベース", model.database or "-"],
    ]
    meta_table = Table(meta_data, colWidths=[35 * mm, 60 * mm, 35 * mm, 60 * mm])
    meta_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), _FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#7F8C8D")),
        ("TEXTCOLOR", (2, 0), (2, -1), colors.HexColor("#7F8C8D")),
        ("TEXTCOLOR", (1, 0), (1, -1), _C_PRIMARY),
        ("TEXTCOLOR", (3, 0), (3, -1), _C_PRIMARY),
        ("GRID", (0, 0), (-1, -1), 0.3, _C_BORDER),
        ("BACKGROUND", (0, 0), (-1, -1), _C_HEADER_BG),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    items.append(meta_table)

    # Description
    if model.description:
        items.append(Spacer(1, 2 * mm))
        items.append(Paragraph(model.description, st["desc"]))

    # Upstream dependencies
    if model.depends_on:
        items.append(Paragraph(
            "依存モデル: " + "、".join(model.depends_on),
            ParagraphStyle("deps", fontName=_FONT, fontSize=8,
                           textColor=colors.HexColor("#7F8C8D"), spaceAfter=4),
        ))

    # Columns table
    if model.columns:
        _cell_st = ParagraphStyle("cell", fontName=_FONT, fontSize=8, textColor=_C_PRIMARY)
        _hdr_st = ParagraphStyle("hcell", fontName=_FONT, fontSize=8, textColor=colors.white)

        def _cell(text: str) -> Paragraph:
            return Paragraph(text or "-", _cell_st)

        col_header = [[
            Paragraph(h, _hdr_st) for h in ["#", "カラム名", "データ型", "説明", "テスト"]
        ]]
        col_rows = [
            [
                _cell(str(i + 1)),
                _cell(col.name),
                _cell(col.data_type or "-"),
                _cell(col.description or "-"),
                _cell(", ".join(col.tests) if col.tests else "-"),
            ]
            for i, col in enumerate(model.columns)
        ]
        col_table = Table(
            col_header + col_rows,
            colWidths=[8 * mm, 38 * mm, 38 * mm, 72 * mm, 29 * mm],
        )
        style = [
            ("FONTNAME", (0, 0), (-1, -1), _FONT),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("BACKGROUND", (0, 0), (-1, 0), _C_PRIMARY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.3, _C_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]
        for i in range(1, len(col_rows) + 1):
            if i % 2 == 0:
                style.append(("BACKGROUND", (0, i), (-1, i), _C_HEADER_BG))
        col_table.setStyle(TableStyle(style))
        items.append(col_table)

    items.append(Spacer(1, 8 * mm))
    return items


def generate_pdf(
    models: list[ModelInfo],
    output_path: Path,
    project_name: str = "sample_project",
) -> None:
    _register_fonts()
    st = _styles()
    page_w, page_h = A4

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title=f"dbt データカタログ - {project_name}",
        author="dbt-doc-to-pdf",
    )

    story: list = []
    story.extend(_cover_page(project_name, st))
    story.extend(_toc_page(models, st))

    # One section per layer
    current_layer = None
    for model in models:
        if model.layer != current_layer:
            current_layer = model.layer
            label = _LAYER_LABELS.get(model.layer, model.layer)
            story.append(Paragraph(f"{label} レイヤー", st["section"]))
            story.append(HRFlowable(width="100%", thickness=1.5, color=_layer_color(model.layer)))
            story.append(Spacer(1, 3 * mm))
        story.extend(_model_section(model, st))

    # ER diagram
    story.append(PageBreak())
    story.append(Paragraph("ER 図 / データリネージ", st["er_title"]))
    story.append(HRFlowable(width="100%", thickness=1, color=_C_BORDER))
    story.append(Spacer(1, 4 * mm))

    content_w = page_w - 30 * mm
    er = build_er_diagram(models, content_w)
    story.append(er)

    doc.build(story)
