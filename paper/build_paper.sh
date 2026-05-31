#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
bash prepare_assets.sh
mkdir -p build
latexmk -pdf -interaction=nonstopmode -outdir=build main.tex
