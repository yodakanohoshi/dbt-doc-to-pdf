import base64
import datetime
import html
import mimetypes
import re
from pathlib import Path
from typing import Any

import markdown as _md_lib

from .models import ModelInfo

_LAYER_COLORS: dict[str, str] = {
    "staging": "#2980B9",
    "intermediate": "#8E44AD",
    "marts": "#27AE60",
    "other": "#7F8C8D",
}
_LAYER_ORDER = ["staging", "intermediate", "marts"]


def _c(layer: str) -> str:
    return _LAYER_COLORS.get(layer, _LAYER_COLORS["other"])


def _h(text: object) -> str:
    return html.escape(str(text))


def _embed_images(html_str: str, base_dir: Path | None) -> str:
    """Replace local <img src="..."> paths with base64 data URIs."""
    if not base_dir:
        return html_str

    def replace_src(m: re.Match) -> str:
        src = m.group(1)
        if src.startswith(("http://", "https://", "data:", "//")):
            return m.group(0)
        candidates = [base_dir / src, base_dir / "models" / src]
        img_path = next((p for p in candidates if p.exists()), None)
        if img_path is None:
            return m.group(0)
        mime_type, _ = mimetypes.guess_type(str(img_path))
        if not mime_type or not mime_type.startswith("image/"):
            return m.group(0)
        data = base64.b64encode(img_path.read_bytes()).decode("ascii")
        return f'src="data:{mime_type};base64,{data}"'

    return re.sub(r'src="([^"]*)"', replace_src, html_str)


def _md(text: str | None, base_dir: Path | None = None) -> str:
    """Convert Markdown (including math) to HTML.

    Math blocks ($...$ and $$...$$) are extracted before Markdown processing
    and restored afterwards so MathJax can render them in the browser.
    Local images are embedded as base64 data URIs if base_dir is provided.
    """
    if not text:
        return ""
    saved: list[str] = []

    def _save(m: re.Match) -> str:
        saved.append(m.group(0))
        return f"MATHPLACEHOLDER{len(saved) - 1}X"

    # Protect display math before inline math to avoid double-matching.
    text = re.sub(r"\$\$[\s\S]*?\$\$", _save, text)
    text = re.sub(r"\$[^$\n]+?\$", _save, text)

    result = _md_lib.markdown(text, extensions=["tables", "fenced_code"])

    for i, block in enumerate(saved):
        result = result.replace(f"MATHPLACEHOLDER{i}X", block)

    result = _embed_images(result, base_dir)
    return result


def _dir_of(path: str) -> str:
    parts = path.rsplit("/", 1)
    return parts[0] if len(parts) > 1 else path.split(".")[0]


def _sorted_dirs(dirs: list[str]) -> list[str]:
    def sort_key(d: str) -> tuple[int, str]:
        top = d.split("/")[0]
        try:
            return (_LAYER_ORDER.index(top), d)
        except ValueError:
            return (len(_LAYER_ORDER), d)
    return sorted(dirs, key=sort_key)


def generate_html(
    models: list[ModelInfo],
    output_path: Path,
    project_name: str = "dbt project",
    base_dir: Path | None = None,
    manifest_docs: dict[str, Any] | None = None,
) -> None:
    # Build content -> doc-file directory map for precise image path resolution.
    # When a description originates from a doc block ({{ doc("name") }}), images
    # referenced in that block must be resolved relative to the .md file, not base_dir.
    content_to_doc_dir: dict[str, Path] = {}
    if base_dir and manifest_docs:
        for doc in manifest_docs.values():
            fp: str = doc.get("original_file_path", "")
            contents: str = doc.get("block_contents", "")
            if fp and contents:
                content_to_doc_dir[contents] = (base_dir / fp).parent

    def _resolve_dir(text: str | None) -> Path | None:
        if text and text in content_to_doc_dir:
            return content_to_doc_dir[text]
        return base_dir

    today = datetime.date.today().strftime("%Y年%m月%d日")

    # Group by full directory path (e.g. "staging", "staging/orders")
    dir_groups: dict[str, list[ModelInfo]] = {}
    for m in models:
        d = _dir_of(m.path)
        dir_groups.setdefault(d, []).append(m)

    dir_order = _sorted_dirs(list(dir_groups.keys()))

    sidebar_items: list[str] = []
    prev_top: str = ""
    for d in dir_order:
        top = d.split("/")[0]
        if top != prev_top:
            sidebar_items.append(
                f'<div class="layer-label" style="color:{_c(top)}">{_h(top)}</div>'
            )
            prev_top = top
        if "/" in d:
            sub = d.split("/", 1)[1]
            sidebar_items.append(
                f'<div class="subdir-label">{_h(sub)}</div>'
            )
        for m in dir_groups[d]:
            sidebar_items.append(
                f'<a class="nav-item" href="#model-{_h(m.name)}" '
                f'data-search="{_h(m.name.lower())}">{_h(m.name)}</a>'
            )

    model_sections: list[str] = []
    prev_top = ""
    for d in dir_order:
        top = d.split("/")[0]
        color = _c(top)
        if top != prev_top:
            model_sections.append(
                f'<div class="layer-section-header" style="border-left:4px solid {color};padding-left:12px">'
                f'<h2 style="color:{color};margin:0">{_h(top)}</h2></div>'
            )
            prev_top = top
        if "/" in d:
            sub = d.split("/", 1)[1]
            model_sections.append(
                f'<div class="subdir-section-header" style="border-left:3px solid {color};padding-left:10px;margin-left:8px">'
                f'<h3 style="color:{color};margin:0;font-size:13px;opacity:.85">{_h(sub)}</h3></div>'
            )
        for m in dir_groups[d]:
            col_rows = ""
            for i, col in enumerate(m.columns):
                tests_html = (
                    " ".join(f'<span class="badge">{_h(t)}</span>' for t in col.tests)
                    if col.tests else '<span class="muted">-</span>'
                )
                row_class = "alt" if i % 2 == 0 else ""
                col_desc = _md(col.description, _resolve_dir(col.description)) if col.description else '<span class="muted">-</span>'
                col_rows += (
                    f'<tr class="{row_class}">'
                    f'<td class="num">{i + 1}</td>'
                    f'<td class="colname">{_h(col.name)}</td>'
                    f'<td class="type">{_h(col.data_type or "-")}</td>'
                    f'<td class="md-content">{col_desc}</td>'
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
    {('<div class="desc md-content">' + _md(m.description, _resolve_dir(m.description)) + '</div>') if m.description else ''}
    {col_table}
  </div>
</div>""")

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
.subdir-label{{padding:6px 16px 2px 28px;font-size:10px;font-weight:600;color:#7f8c8d;letter-spacing:.03em}}
.nav-item{{display:block;padding:5px 16px 5px 24px;font-size:13px;color:#bdc3c7;border-left:3px solid transparent;transition:all .15s}}
.nav-item:hover,.nav-item.active{{background:#1e2d3d;color:#fff;border-left-color:#3498db}}
/* Main */
#main{{margin-left:240px;flex:1;display:flex;flex-direction:column;min-height:100vh}}
#topbar{{background:#fff;border-bottom:1px solid #dde1e7;padding:12px 28px;display:flex;align-items:center;gap:12px;position:sticky;top:0;z-index:5}}
#topbar h2{{font-size:16px;font-weight:600;color:#2c3e50}}
.topbar-sub{{font-size:12px;color:#7f8c8d}}
#content{{padding:28px;display:flex;flex-direction:column;gap:32px}}
/* Layer / subdir headers */
.layer-section-header{{margin-bottom:4px}}
.subdir-section-header{{margin-bottom:4px;margin-top:8px}}
/* Model card */
.model-card{{background:#fff;border-radius:8px;box-shadow:0 1px 4px rgba(0,0,0,.08);overflow:hidden}}
.model-header{{padding:12px 18px;display:flex;align-items:center;justify-content:space-between}}
.model-title{{font-size:15px;font-weight:700;color:#fff}}
.model-badge{{font-size:11px;background:rgba(255,255,255,.2);color:#fff;padding:2px 8px;border-radius:10px}}
.model-body{{padding:16px 18px}}
.meta-grid{{display:grid;grid-template-columns:max-content 1fr;gap:4px 16px;font-size:12px;margin-bottom:12px;color:#555}}
.meta-label{{color:#95a5a6;font-weight:600}}
.desc{{font-size:13px;color:#555;margin-bottom:10px;line-height:1.5}}
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
/* Markdown-rendered descriptions */
.md-content p{{margin:0 0 6px}}
.md-content p:last-child{{margin-bottom:0}}
.md-content strong{{font-weight:700}}
.md-content em{{font-style:italic}}
.md-content code{{font-family:monospace;font-size:12px;background:#f0f2f5;padding:1px 4px;border-radius:3px}}
.md-content pre{{background:#f0f2f5;padding:8px;border-radius:4px;overflow-x:auto;margin:4px 0}}
.md-content pre code{{background:none;padding:0}}
.md-content ul,.md-content ol{{padding-left:18px;margin:4px 0}}
.md-content table{{border-collapse:collapse;font-size:12px;margin:4px 0}}
.md-content table th,.md-content table td{{border:1px solid #dde1e7;padding:3px 8px}}
.md-content table th{{background:#f7f9fc;font-weight:600}}
.md-content img{{max-width:100%;height:auto;display:block;margin:6px 0;border-radius:4px}}
</style>
<script>
MathJax = {{tex: {{inlineMath: [['$','$']], displayMath: [['$$','$$']]}}, options: {{skipHtmlTags: ['script','noscript','style','textarea']}}}};
</script>
<script async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js"></script>
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
  </div>
</nav>
<div id="main">
  <div id="topbar">
    <h2>データカタログ</h2>
    <span class="topbar-sub">{len(models)} モデル · 生成: {_h(today)}</span>
  </div>
  <div id="content">
    {"".join(model_sections)}
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
var cards = document.querySelectorAll('.model-card');
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
