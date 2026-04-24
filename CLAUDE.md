# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

This repository is intended to convert dbt documentation into PDF format. The project is currently empty — no source files, dependencies, or tooling have been added yet.

## セットアップ & 実行

```bash
uv sync                        # 依存関係インストール
uv run dbt-doc-to-pdf \
  --target-dir sample_project/target \
  --output catalog.pdf \
  --project sample_project
```

## テスト

```bash
uv run pytest tests/ -v        # 全テスト
uv run pytest tests/test_extractor.py -v   # 抽出ロジック単体テスト
uv run pytest tests/test_pdf_content.py -v # PDF 内容整合テスト
```

## アーキテクチャ

```
src/dbt_doc_to_pdf/
  loader.py      manifest.json / catalog.json の読み込み
  models.py      ModelInfo / ColumnInfo データクラス
  extractor.py   manifest + catalog -> ModelInfo リスト変換
                 (テスト情報も各カラムに付与)
  pdf_gen.py     reportlab Platypus で PDF 生成
                 (HeiseiKakuGo-W5 CID フォントで日本語対応)
  er_diagram.py  reportlab Drawing でリネージ図描画
  __main__.py    CLI エントリーポイント
tests/
  conftest.py    セッションスコープ fixtures (manifest/catalog/PDF)
  test_extractor.py  抽出ロジック単体テスト
  test_pdf_content.py PDF テキスト整合性テスト
```

## ゴール
dbt docs generateで生成されるメタ情報を活用してある程度きれいなpdf形式のテーブルカタログを作成すること
pandasは利用せずpipで導入可能なツールのみを活用して
