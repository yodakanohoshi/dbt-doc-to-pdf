#!/usr/bin/env bash
set -e

OUTPUT="${OUTPUT:-/output/catalog.pdf}"
PROJECT="${PROJECT:-sample_project}"

echo "==> dbt docs generate を実行中..."
cd /app/sample_project
uv run --directory /app dbt docs generate --profiles-dir .

echo "==> PDF を生成中..."
cd /app
uv run dbt-doc-to-pdf \
  --target-dir sample_project/target \
  --output "${OUTPUT}" \
  --project "${PROJECT}"

echo "==> 完了: ${OUTPUT}"
