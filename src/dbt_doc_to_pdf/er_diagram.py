from reportlab.graphics.shapes import (
    Drawing,
    Group,
    Line,
    Polygon,
    Rect,
    String,
)
from reportlab.lib import colors
from reportlab.lib.units import mm

from .models import ModelInfo

_LAYER_COLORS = {
    "staging": colors.HexColor("#2980B9"),
    "ecommerce": colors.HexColor("#27AE60"),
    "other": colors.HexColor("#7F8C8D"),
}
_BOX_BG = colors.HexColor("#ECF0F1")
_BOX_BORDER = colors.HexColor("#BDC3C7")
_ARROW_COLOR = colors.HexColor("#555555")

_BOX_W = 200
_HEADER_H = 22
_ROW_H = 14
_PAD = 8
_COL_GAP = 60
_FONT = "HeiseiKakuGo-W5"
_FONT_SZ_HEADER = 9
_FONT_SZ_COL = 7


def _box_height(model: ModelInfo) -> float:
    return _HEADER_H + len(model.columns) * _ROW_H + _PAD


def _draw_box(model: ModelInfo, x: float, y_bottom: float) -> Group:
    """Draw a model box. y_bottom is the bottom edge in Drawing coords (y-up)."""
    h = _box_height(model)
    header_color = _LAYER_COLORS.get(model.layer, _LAYER_COLORS["other"])

    g = Group()
    # Shadow
    g.add(Rect(x + 2, y_bottom - 2, _BOX_W, h, fillColor=colors.HexColor("#CCCCCC"), strokeColor=None))
    # Main box
    g.add(Rect(x, y_bottom, _BOX_W, h, fillColor=_BOX_BG, strokeColor=_BOX_BORDER, strokeWidth=0.5))
    # Header background
    g.add(Rect(x, y_bottom + h - _HEADER_H, _BOX_W, _HEADER_H, fillColor=header_color, strokeColor=None))

    # Model name in header
    g.add(String(
        x + _BOX_W / 2,
        y_bottom + h - _HEADER_H + 6,
        model.name,
        fontName=_FONT,
        fontSize=_FONT_SZ_HEADER,
        fillColor=colors.white,
        textAnchor="middle",
    ))

    # Column rows
    for i, col in enumerate(model.columns):
        row_y = y_bottom + h - _HEADER_H - (i + 1) * _ROW_H
        # Alternating row background
        if i % 2 == 0:
            g.add(Rect(x, row_y, _BOX_W, _ROW_H, fillColor=colors.HexColor("#F8F9FA"), strokeColor=None))

        type_str = f"  {col.name}" + (f" : {col.data_type}" if col.data_type else "")
        g.add(String(
            x + 6,
            row_y + 3,
            type_str,
            fontName=_FONT,
            fontSize=_FONT_SZ_COL,
            fillColor=colors.HexColor("#2C3E50"),
        ))

    # Border re-draw on top
    g.add(Rect(x, y_bottom, _BOX_W, h, fillColor=None, strokeColor=_BOX_BORDER, strokeWidth=0.5))

    return g


def _arrow(x1: float, y1: float, x2: float, y2: float) -> Group:
    g = Group()
    g.add(Line(x1, y1, x2, y2, strokeColor=_ARROW_COLOR, strokeWidth=1.2))
    # Arrowhead at (x2, y2)
    import math
    angle = math.atan2(y2 - y1, x2 - x1)
    size = 6
    pts = [
        x2, y2,
        x2 - size * math.cos(angle - 0.4), y2 - size * math.sin(angle - 0.4),
        x2 - size * math.cos(angle + 0.4), y2 - size * math.sin(angle + 0.4),
    ]
    g.add(Polygon(pts, fillColor=_ARROW_COLOR, strokeColor=None))
    return g


def build_er_diagram(models: list[ModelInfo], page_width: float) -> Drawing:
    staging = [m for m in models if m.layer == "staging"]
    ecommerce = [m for m in models if m.layer not in ("staging",)]

    by_name = {m.name: m for m in models}

    # Layout parameters
    left_x = 20.0
    right_x = left_x + _BOX_W + _COL_GAP
    v_gap = 16.0
    title_h = 30.0

    # Compute staging box positions (top-down, y-up)
    staging_positions: dict[str, float] = {}  # name -> y_bottom
    y = 0.0
    for m in reversed(staging):
        staging_positions[m.name] = y
        y += _box_height(m) + v_gap

    staging_total_h = y - v_gap

    # Compute ecommerce box positions based on dependency midpoints
    ecommerce_positions: dict[str, float] = {}
    for m in ecommerce:
        dep_centers = []
        for dep_name in m.depends_on:
            if dep_name in staging_positions:
                dep_m = by_name.get(dep_name)
                if dep_m:
                    dep_centers.append(staging_positions[dep_name] + _box_height(dep_m) / 2)
        if dep_centers:
            mid = sum(dep_centers) / len(dep_centers)
            ecommerce_positions[m.name] = mid - _box_height(m) / 2
        else:
            ecommerce_positions[m.name] = 0.0

    # Fix overlaps in ecommerce column
    sorted_eco = sorted(ecommerce, key=lambda m: ecommerce_positions[m.name])
    for i in range(1, len(sorted_eco)):
        prev = sorted_eco[i - 1]
        curr = sorted_eco[i]
        min_y = ecommerce_positions[prev.name] + _box_height(prev) + v_gap
        if ecommerce_positions[curr.name] < min_y:
            ecommerce_positions[curr.name] = min_y

    eco_total_h = max(
        (ecommerce_positions[m.name] + _box_height(m) for m in ecommerce),
        default=0.0,
    )

    drawing_h = max(staging_total_h, eco_total_h) + title_h + 20
    drawing_w = right_x + _BOX_W + 20

    d = Drawing(drawing_w, drawing_h)

    # Title
    d.add(String(
        drawing_w / 2,
        drawing_h - 20,
        "データリネージ図",
        fontName=_FONT,
        fontSize=12,
        fillColor=colors.HexColor("#2C3E50"),
        textAnchor="middle",
    ))

    # Layer labels
    d.add(String(left_x + _BOX_W / 2, drawing_h - title_h + 2, "Staging",
                 fontName=_FONT, fontSize=8, fillColor=_LAYER_COLORS["staging"], textAnchor="middle"))
    d.add(String(right_x + _BOX_W / 2, drawing_h - title_h + 2, "Ecommerce",
                 fontName=_FONT, fontSize=8, fillColor=_LAYER_COLORS["ecommerce"], textAnchor="middle"))

    content_base = 10.0

    # Draw arrows first (behind boxes)
    for m in ecommerce:
        eco_y_bot = ecommerce_positions[m.name] + content_base
        eco_center_y = eco_y_bot + _box_height(m) / 2
        for dep_name in m.depends_on:
            if dep_name in staging_positions:
                dep_m = by_name.get(dep_name)
                if dep_m:
                    stg_y_bot = staging_positions[dep_name] + content_base
                    stg_center_y = stg_y_bot + _box_height(dep_m) / 2
                    d.add(_arrow(
                        left_x + _BOX_W, stg_center_y,
                        right_x, eco_center_y,
                    ))

    # Draw boxes
    for m in staging:
        y_bot = staging_positions[m.name] + content_base
        d.add(_draw_box(m, left_x, y_bot))

    for m in ecommerce:
        y_bot = ecommerce_positions[m.name] + content_base
        d.add(_draw_box(m, right_x, y_bot))

    return d
