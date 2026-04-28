import datetime
import html
from pathlib import Path

from .models import ModelInfo

_LAYER_COLORS: dict[str, str] = {
    "staging": "#2980B9",
    "intermediate": "#8E44AD",
    "marts": "#27AE60",
    "other": "#7F8C8D",
}
_LAYER_ORDER = ["staging", "intermediate", "marts"]

_BOX_W = 200
_HEADER_H = 28
_ROW_H = 18
_PAD_V = 8
_COL_GAP = 80
_V_GAP = 20


def _c(layer: str) -> str:
    return _LAYER_COLORS.get(layer, _LAYER_COLORS["other"])


def _h(text: object) -> str:
    return html.escape(str(text))


def _box_h(model: ModelInfo) -> int:
    return _HEADER_H + len(model.columns) * _ROW_H + _PAD_V


def _build_er_svg(models: list[ModelInfo]) -> str:
    if not models:
        return ""

    by_name = {m.name: m for m in models}

    # Determine layer column order
    seen_layers: list[str] = []
    for m in models:
        if m.layer not in seen_layers:
            seen_layers.append(m.layer)
    ordered_layers = [l for l in _LAYER_ORDER if l in seen_layers]
    for l in seen_layers:
        if l not in ordered_layers:
            ordered_layers.append(l)

    col_x: dict[str, float] = {}
    x = 20.0
    for layer in ordered_layers:
        col_x[layer] = x
        x += _BOX_W + _COL_GAP

    # Assign y positions per column (y-down SVG coords)
    positions: dict[str, tuple[float, float]] = {}  # name -> (x, y_top)
    col_cursor: dict[str, float] = {l: 60.0 for l in ordered_layers}

    # First pass: layers in order
    for layer in ordered_layers:
        layer_models = [m for m in models if m.layer == layer]
        lx = col_x[layer]
        y = col_cursor[layer]
        for m in layer_models:
            positions[m.name] = (lx, y)
            y += _box_h(m) + _V_GAP
        col_cursor[layer] = y

    # Nudge downstream model y to align with its dependencies' midpoints
    for layer in ordered_layers[1:]:
        layer_models = [m for m in models if m.layer == layer]
        sorted_models = sorted(layer_models, key=lambda m: positions[m.name][1])
        for m in sorted_models:
            dep_mids = []
            for dep in m.depends_on:
                if dep in positions and dep in by_name:
                    dy = positions[dep][1]
                    dep_mids.append(dy + _box_h(by_name[dep]) / 2)
            if dep_mids:
                target_mid = sum(dep_mids) / len(dep_mids)
                positions[m.name] = (positions[m.name][0], target_mid - _box_h(m) / 2)

        # Fix overlaps (top-down)
        sorted_models = sorted(layer_models, key=lambda m: positions[m.name][1])
        for i in range(1, len(sorted_models)):
            prev = sorted_models[i - 1]
            curr = sorted_models[i]
            min_y = positions[prev.name][1] + _box_h(prev) + _V_GAP
            if positions[curr.name][1] < min_y:
                positions[curr.name] = (positions[curr.name][0], min_y)

    if not positions:
        return ""

    total_w = x
    total_h = max(py + _box_h(by_name[n]) for n, (_, py) in positions.items()) + 40

    parts: list[str] = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{total_w:.0f}" height="{total_h:.0f}" '
        f'style="font-family:sans-serif;background:#fafafa;">'
    )

    # Layer labels
    for layer in ordered_layers:
        lx = col_x[layer]
        parts.append(
            f'<text x="{lx + _BOX_W / 2:.0f}" y="40" text-anchor="middle" '
            f'font-size="13" font-weight="bold" fill="{_c(layer)}">{_h(layer)}</text>'
        )

    # Arrows (draw behind boxes)
    for m in models:
        mx, my = positions[m.name]
        m_mid_y = my + _box_h(m) / 2
        for dep in m.depends_on:
            if dep not in positions or dep not in by_name:
                continue
            dx, dy = positions[dep]
            dep_mid_y = dy + _box_h(by_name[dep]) / 2
            x1 = dx + _BOX_W
            y1 = dep_mid_y
            x2 = mx
            y2 = m_mid_y
            # Arrow line
            parts.append(
                f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                f'stroke="#888" stroke-width="1.5" marker-end="url(#arrow)"/>'
            )

    # Arrowhead marker
    parts.insert(1,
        '<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">'
        '<path d="M0,0 L0,6 L8,3 z" fill="#888"/>'
        '</marker></defs>'
    )

    # Boxes
    for m in models:
        mx, my = positions[m.name]
        bh = _box_h(m)
        color = _c(m.layer)
        # Shadow
        parts.append(
            f'<rect x="{mx + 3:.0f}" y="{my + 3:.0f}" width="{_BOX_W}" height="{bh}" '
            f'rx="4" fill="#ccc" opacity="0.4"/>'
        )
        # Box background
        parts.append(
            f'<rect x="{mx:.0f}" y="{my:.0f}" width="{_BOX_W}" height="{bh}" '
            f'rx="4" fill="#f4f6f7" stroke="#bdc3c7" stroke-width="0.8"/>'
        )
        # Header
        parts.append(
            f'<rect x="{mx:.0f}" y="{my:.0f}" width="{_BOX_W}" height="{_HEADER_H}" '
            f'rx="4" fill="{color}"/>'
            f'<rect x="{mx:.0f}" y="{my + _HEADER_H - 4:.0f}" width="{_BOX_W}" height="4" fill="{color}"/>'
        )
        # Model name
        name_y = my + _HEADER_H / 2 + 5
        parts.append(
            f'<text x="{mx + _BOX_W / 2:.0f}" y="{name_y:.0f}" text-anchor="middle" '
            f'font-size="11" font-weight="bold" fill="white">{_h(m.name)}</text>'
        )
        # Columns
        for i, col in enumerate(m.columns):
            row_y = my + _HEADER_H + i * _ROW_H
            if i % 2 == 0:
                parts.append(
                    f'<rect x="{mx:.0f}" y="{row_y:.0f}" width="{_BOX_W}" height="{_ROW_H}" fill="#eaf0fb" opacity="0.6"/>'
                )
            type_txt = f"{col.name}" + (f" : {col.data_type}" if col.data_type else "")
            text_y = row_y + _ROW_H - 5
            parts.append(
                f'<text x="{mx + 8:.0f}" y="{text_y:.0f}" font-size="9" fill="#2c3e50">{_h(type_txt)}</text>'
            )

    parts.append("</svg>")
    return "\n".join(parts)


def generate_html(
    models: list[ModelInfo],
    output_path: Path,
    project_name: str = "dbt project",
) -> None:
    today = datetime.date.today().strftime("%Y年%m月%d日")

    # Group by layer
    layers: dict[str, list[ModelInfo]] = {}
    for m in models:
        layers.setdefault(m.layer, []).append(m)

    layer_order = [l for l in _LAYER_ORDER if l in layers]
    for l in layers:
        if l not in layer_order:
            layer_order.append(l)

    sidebar_items: list[str] = []
    for layer in layer_order:
        sidebar_items.append(
            f'<div class="layer-label" style="color:{_c(layer)}">{_h(layer)}</div>'
        )
        for m in layers[layer]:
            sidebar_items.append(
                f'<a class="nav-item" href="#model-{_h(m.name)}" '
                f'data-search="{_h(m.name.lower())}">{_h(m.name)}</a>'
            )

    model_sections: list[str] = []
    for layer in layer_order:
        model_sections.append(
            f'<div class="layer-section-header" style="border-left:4px solid {_c(layer)};padding-left:12px">'
            f'<h2 style="color:{_c(layer)};margin:0">{_h(layer)}</h2></div>'
        )
        for m in layers[layer]:
            depends_html = (
                '<div class="depends">依存: ' +
                ", ".join(f'<a href="#model-{_h(d)}">{_h(d)}</a>' for d in m.depends_on) +
                "</div>"
                if m.depends_on else ""
            )
            col_rows = ""
            for i, col in enumerate(m.columns):
                tests_html = (
                    " ".join(f'<span class="badge">{_h(t)}</span>' for t in col.tests)
                    if col.tests else '<span class="muted">-</span>'
                )
                row_class = "alt" if i % 2 == 0 else ""
                col_rows += (
                    f'<tr class="{row_class}">'
                    f'<td class="num">{i + 1}</td>'
                    f'<td class="colname">{_h(col.name)}</td>'
                    f'<td class="type">{_h(col.data_type or "-")}</td>'
                    f'<td>{_h(col.description or "-")}</td>'
                    f'<td>{tests_html}</td>'
                    f'</tr>'
                )
            col_table = (
                '<table class="col-table"><thead><tr>'
                '<th>#</th><th>カラム名</th><th>データ型</th><th>説明</th><th>テスト</th>'
                f'</tr></thead><tbody>{col_rows}</tbody></table>'
                if m.columns else '<p class="muted">カラム定義なし</p>'
            )
            model_sections.append(f"""
<div class="model-card" id="model-{_h(m.name)}">
  <div class="model-header" style="background:{_c(m.layer)}">
    <span class="model-title">{_h(m.name)}</span>
    <span class="model-badge">{_h(m.materialized or "model")}</span>
  </div>
  <div class="model-body">
    <div class="meta-grid">
      <span class="meta-label">スキーマ</span><span>{_h(m.schema or "-")}</span>
      <span class="meta-label">データベース</span><span>{_h(m.database or "-")}</span>
      <span class="meta-label">パス</span><span>{_h(m.path or "-")}</span>
    </div>
    {('<p class="desc">' + _h(m.description) + '</p>') if m.description else ''}
    {depends_html}
    {col_table}
  </div>
</div>""")

    er_svg = _build_er_svg(models)
    er_section = f"""
<section id="er-diagram">
  <h2>ER図 / データリネージ</h2>
  <div class="er-container">
    {er_svg}
  </div>
</section>""" if er_svg else ""

    html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>dbt データカタログ — {_h(project_name)}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;font-size:14px;color:#2c3e50;background:#f0f2f5;display:flex;min-height:100vh}}
a{{color:inherit;text-decoration:none}}
/* Sidebar */
#sidebar{{width:240px;min-width:240px;background:#2c3e50;color:#ecf0f1;display:flex;flex-direction:column;position:fixed;top:0;left:0;height:100vh;overflow-y:auto;z-index:10}}
.sidebar-header{{padding:20px 16px 12px;border-bottom:1px solid #3d5166}}
.sidebar-header h1{{font-size:15px;font-weight:700;color:#fff}}
.sidebar-header .sub{{font-size:11px;color:#95a5a6;margin-top:4px}}
#search{{margin:10px 12px;padding:7px 10px;border-radius:6px;border:1px solid #3d5166;background:#1e2d3d;color:#ecf0f1;font-size:13px;width:calc(100% - 24px);outline:none}}
#search::placeholder{{color:#7f8c8d}}
.layer-label{{padding:10px 16px 4px;font-size:11px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;opacity:.9}}
.nav-item{{display:block;padding:5px 16px 5px 24px;font-size:13px;color:#bdc3c7;border-left:3px solid transparent;transition:all .15s}}
.nav-item:hover,.nav-item.active{{background:#1e2d3d;color:#fff;border-left-color:#3498db}}
/* Main */
#main{{margin-left:240px;flex:1;display:flex;flex-direction:column;min-height:100vh}}
#topbar{{background:#fff;border-bottom:1px solid #dde1e7;padding:12px 28px;display:flex;align-items:center;gap:12px;position:sticky;top:0;z-index:5}}
#topbar h2{{font-size:16px;font-weight:600;color:#2c3e50}}
.topbar-sub{{font-size:12px;color:#7f8c8d}}
#content{{padding:28px;display:flex;flex-direction:column;gap:32px}}
/* Layer header */
.layer-section-header{{margin-bottom:4px}}
/* Model card */
.model-card{{background:#fff;border-radius:8px;box-shadow:0 1px 4px rgba(0,0,0,.08);overflow:hidden}}
.model-header{{padding:12px 18px;display:flex;align-items:center;justify-content:space-between}}
.model-title{{font-size:15px;font-weight:700;color:#fff}}
.model-badge{{font-size:11px;background:rgba(255,255,255,.2);color:#fff;padding:2px 8px;border-radius:10px}}
.model-body{{padding:16px 18px}}
.meta-grid{{display:grid;grid-template-columns:max-content 1fr;gap:4px 16px;font-size:12px;margin-bottom:12px;color:#555}}
.meta-label{{color:#95a5a6;font-weight:600}}
.desc{{font-size:13px;color:#555;margin-bottom:10px;line-height:1.5}}
.depends{{font-size:12px;color:#7f8c8d;margin-bottom:10px}}
.depends a{{color:#3498db;text-decoration:underline}}
/* Column table */
.col-table{{width:100%;border-collapse:collapse;font-size:13px}}
.col-table th{{background:#2c3e50;color:#fff;padding:6px 10px;text-align:left;font-weight:600;font-size:12px}}
.col-table td{{padding:5px 10px;border-bottom:1px solid #eee;vertical-align:top}}
.col-table tr.alt td{{background:#f7f9fc}}
td.num{{color:#95a5a6;width:32px;text-align:right}}
td.colname{{font-family:monospace;font-size:12px;font-weight:600}}
td.type{{font-family:monospace;font-size:12px;color:#7f8c8d}}
.badge{{display:inline-block;font-size:10px;background:#eaf4fd;color:#2980b9;border:1px solid #aed6f1;border-radius:4px;padding:1px 5px;margin:1px 2px}}
.muted{{color:#bdc3c7}}
/* ER section */
#er-diagram{{background:#fff;border-radius:8px;box-shadow:0 1px 4px rgba(0,0,0,.08);padding:20px 18px}}
#er-diagram h2{{font-size:15px;font-weight:600;color:#2c3e50;margin-bottom:14px}}
.er-container{{overflow-x:auto}}
</style>
</head>
<body>
<nav id="sidebar">
  <div class="sidebar-header">
    <h1>dbt データカタログ</h1>
    <div class="sub">{_h(project_name)} · {_h(today)}</div>
  </div>
  <input id="search" type="search" placeholder="モデルを検索…" oninput="filterNav(this.value)">
  <div id="nav-list">
    {"".join(sidebar_items)}
    <a class="nav-item" href="#er-diagram">ER図 / リネージ</a>
  </div>
</nav>
<div id="main">
  <div id="topbar">
    <h2>データカタログ</h2>
    <span class="topbar-sub">{len(models)} モデル · 生成: {_h(today)}</span>
  </div>
  <div id="content">
    {"".join(model_sections)}
    {er_section}
  </div>
</div>
<script>
function filterNav(q) {{
  q = q.toLowerCase();
  document.querySelectorAll('#nav-list .nav-item').forEach(function(a) {{
    var s = a.dataset.search || '';
    a.style.display = (!q || s.includes(q)) ? '' : 'none';
  }});
}}
// Highlight active section on scroll
var cards = document.querySelectorAll('.model-card, #er-diagram');
var navLinks = document.querySelectorAll('.nav-item');
function onScroll() {{
  var scrollY = window.scrollY + 80;
  var active = null;
  cards.forEach(function(el) {{
    if (el.offsetTop <= scrollY) active = el.id;
  }});
  navLinks.forEach(function(a) {{
    var href = a.getAttribute('href');
    a.classList.toggle('active', href === '#' + active);
  }});
}}
window.addEventListener('scroll', onScroll, {{passive: true}});
</script>
</body>
</html>"""

    output_path.write_text(html_content, encoding="utf-8")
