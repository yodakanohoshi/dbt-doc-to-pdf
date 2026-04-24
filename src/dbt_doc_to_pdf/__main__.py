import argparse
import sys
from pathlib import Path

from .extractor import extract_models
from .loader import load_catalog, load_manifest
from .pdf_gen import generate_pdf


def main() -> None:
    parser = argparse.ArgumentParser(description="dbt メタデータから PDF データカタログを生成")
    parser.add_argument(
        "--target-dir",
        type=Path,
        default=Path("target"),
        help="dbt target ディレクトリのパス (default: ./target)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("catalog.pdf"),
        help="出力 PDF ファイルパス (default: ./catalog.pdf)",
    )
    parser.add_argument(
        "--project",
        default="sample_project",
        help="プロジェクト名 (default: sample_project)",
    )
    args = parser.parse_args()

    target_dir: Path = args.target_dir
    if not target_dir.exists():
        print(f"ERROR: target ディレクトリが見つかりません: {target_dir}", file=sys.stderr)
        sys.exit(1)

    manifest = load_manifest(target_dir)
    catalog = load_catalog(target_dir)
    models = extract_models(manifest, catalog)

    print(f"モデル数: {len(models)}")
    for m in models:
        print(f"  [{m.layer:12s}] {m.name} ({len(m.columns)} columns)")

    generate_pdf(models, args.output, project_name=args.project)
    print(f"\nPDF を生成しました: {args.output}")


if __name__ == "__main__":
    main()
