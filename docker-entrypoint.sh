#!/usr/bin/env bash
set -e

OUTPUT="${OUTPUT:-/output/catalog.pdf}"
PROJECT="${PROJECT:-sample_project}"

echo "==> PDF を生成中..."
uv run --directory /app dbt-doc-to-pdf \
  --target-dir /target \
  --output "${OUTPUT}" \
  --project "${PROJECT}"

echo "==> 完了: ${OUTPUT}"
