#!/usr/bin/env bash
set -euo pipefail                     # any non-zero exit fails the build

# The tools run from the directory of this script, wherever it is called from.
cd "$(dirname "$0")"

echo '--------------------[ sync ]--------------------'
uv sync --locked                      # fails if uv.lock doesn't match pyproject.toml

echo '--------------------[ format check ]--------------------'
uv run --no-sync ruff format --check  # formatting

echo '--------------------[ lint check ]--------------------'
uv run --no-sync ruff check           # lint

echo '--------------------[ type check ]--------------------'
uv run --no-sync pyrefly check        # type check

echo '--------------------[ tests ]--------------------'
uv run --no-sync pytest               # tests

echo '========================================[ ALL GOOD ]========================================'
