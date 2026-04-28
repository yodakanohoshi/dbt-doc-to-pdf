import argparse
import sys
from pathlib import Path

from .extractor import extract_models
from .html_gen import generate_html
from .loader import load_catalog, load_manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="dbt メタデータから HTML データカタログを生成")
    parser.add_argument(
        "--target-dir",
        type=Path,
        default=Path("target"),
        help="dbt target ディレクトリのパス (default: ./target)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("catalog.html"),
        help="出力 HTML ファイルパス (default: ./catalog.html)",
    )
    parser.add_argument(
        "--project",
        default="dbt project",
        help="プロジェクト名 (default: dbt project)",
    )
    parser.add_argument(
        "--dir",
        dest="model_dir",
        default=None,
        help="対象モデルのパスプレフィックス (例: staging, models/marts)",
    )
    args = parser.parse_args()

    target_dir: Path = args.target_dir
    if not target_dir.exists():
        print(f"ERROR: target ディレクトリが見つかりません: {target_dir}", file=sys.stderr)
        sys.exit(1)

    manifest = load_manifest(target_dir)
    catalog = load_catalog(target_dir)
    models = extract_models(manifest, catalog)

    if args.model_dir:
        # Strip leading "models/" to match manifest path format
        prefix = args.model_dir.removeprefix("models/").rstrip("/") + "/"
        models = [m for m in models if m.path.startswith(prefix)]
        if not models:
            print(f"WARNING: --dir '{args.model_dir}' にマッチするモデルがありません", file=sys.stderr)

    print(f"モデル数: {len(models)}")
    for m in models:
        print(f"  [{m.layer:12s}] {m.name} ({len(m.columns)} columns)  {m.path}")

    generate_html(
        models,
        args.output,
        project_name=args.project,
        base_dir=target_dir.parent,
        manifest_docs=manifest.get("docs", {}),
    )
    print(f"\nHTML を生成しました: {args.output}")


if __name__ == "__main__":
    main()
