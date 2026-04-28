# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

dbt docs generate で生成されるメタ情報を活用して、ブラウザで閲覧できる単一 HTML ファイルのテーブルカタログを生成する。
pandas は利用せず pip で導入可能なツールのみを使用。

## セットアップ & 実行

```bash
uv sync                        # 依存関係インストール
uv run dbt-doc-to-html \
  --target-dir sample_project/target \
  --output catalog.html \
  --project sample_project

# モデルをパスプレフィックスで絞り込む例
uv run dbt-doc-to-html \
  --target-dir sample_project/target \
  --dir staging \
  --output staging.html
```

## Docker での使い方

```bash
# イメージをビルド
docker build -t dbt-doc-to-html .

# 実行 (dbt target ディレクトリと出力先をマウント)
docker run --rm \
  -v /path/to/your/dbt/target:/target:ro \
  -v $(pwd):/out \
  dbt-doc-to-html \
  --target-dir /target \
  --output /out/catalog.html \
  --project my_project

# --dir で絞り込む場合
docker run --rm \
  -v /path/to/your/dbt/target:/target:ro \
  -v $(pwd):/out \
  dbt-doc-to-html \
  --target-dir /target \
  --dir staging \
  --output /out/staging.html
```

## テスト

```bash
uv run pytest tests/ -v               # 全テスト
uv run pytest tests/test_extractor.py -v      # 抽出ロジック単体テスト
uv run pytest tests/test_html_content.py -v  # HTML 内容整合テスト
```

## アーキテクチャ

```
src/dbt_doc_to_pdf/
  loader.py      manifest.json / catalog.json の読み込み
  models.py      ModelInfo / ColumnInfo データクラス
  extractor.py   manifest + catalog -> ModelInfo リスト変換
                 (テスト情報も各カラムに付与)
  html_gen.py    単一 HTML + インライン SVG ER 図を生成
  __main__.py    CLI エントリーポイント (--dir フィルタ対応)
tests/
  conftest.py         セッションスコープ fixtures (manifest/catalog/HTML)
  test_extractor.py   抽出ロジック単体テスト
  test_html_content.py HTML テキスト整合性テスト
```
