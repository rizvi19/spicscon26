# SPICSCON 2026 paper build notes

## Branch

`paper/spicscon26-ieee-draft`

## Text-only PR workflow

This Codex pull request intentionally contains only text-based paper source files and shell scripts. Binary PDF and PNG files are not committed because binary files are not supported in this review UI.

The original paper-ready figures remain tracked under `../results/figures/`. The local preparation script copies the required figures into `paper/figures/` immediately before compilation. Generated copies under `paper/figures/` and the generated PDF under `paper/build/` must remain untracked.

## Build the final PDF locally

From the repository root, run:

```bash
cd paper
bash build_paper.sh
```

The script runs `prepare_assets.sh`, creates `paper/build/` if needed, and invokes:

```bash
latexmk -pdf -interaction=nonstopmode -outdir=build main.tex
```

The final generated PDF will be at:

```text
paper/build/main.pdf
```

## Source and TeX engine

The submission source is `paper/main.tex`, using `\documentclass[conference]{IEEEtran}` and BibTeX file `paper/references.bib`. The intended TeX engine flow is `latexmk` with PDFLaTeX and BibTeX as required by the bibliography.

Equivalent manual commands, after running `bash prepare_assets.sh`, are:

```bash
mkdir -p build
pdflatex -interaction=nonstopmode -output-directory=build main.tex
bibtex build/main
pdflatex -interaction=nonstopmode -output-directory=build main.tex
pdflatex -interaction=nonstopmode -output-directory=build main.tex
```

## Container build status

A final IEEEtran compilation could **not** be executed inside the Codex container because no TeX engine (`latexmk`, `pdflatex`, `bibtex`, Tectonic, XeLaTeX, or LuaLaTeX) is installed. Attempts to install TeX Live with `apt-get` and to download Tectonic were blocked by the environment HTTP proxy with `403 Forbidden` responses.

No generated PDF is committed to this branch. After building locally, confirm the final IEEEtran page count, PDF size, bibliography output, font embedding, and layout warnings before submission.

## Remaining checks after local rebuild

1. Confirm that the compiled paper remains within the conference page limit.
2. Confirm that the compiled PDF remains below the locally recorded approximately 2 MB limit.
3. Inspect `paper/build/main.log` for overfull boxes and unresolved references.
4. Verify font embedding and PDF compatibility using the conference-provided IEEE PDF validation flow if and when official final-submission instructions are published or made accessible.
