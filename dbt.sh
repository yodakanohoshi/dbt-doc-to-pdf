#!/usr/bin/env bash
# NixOS workaround: duckdb needs libstdc++ from gcc store path
LIBSTDCXX=$(find /nix/store -maxdepth 3 -name "libstdc++.so.6" 2>/dev/null | grep "gcc-14" | head -1 | xargs dirname)
export LD_LIBRARY_PATH="$LIBSTDCXX${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

cd "$(dirname "$0")/sample_project"
exec uv run dbt "$@" --profiles-dir .
