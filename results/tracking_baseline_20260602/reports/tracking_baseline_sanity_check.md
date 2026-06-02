# Tracking Baseline Sanity Check

## Local status: BLOCKED / workflow execution required

The local container cannot install or import the repository's scientific Python dependencies. No scientific result claims are made from a run that did not execute.

- **BLOCKED**: all expected numeric CSV files exist — they will be generated only after a successful final workflow run.
- **PASS**: all expected local handoff TXT/MD/JSON reports exist.
- **BLOCKED**: all seeds 101--110 are present in generated metrics — final run required.
- **BLOCKED**: all four scenarios are present in generated metrics — final run required.
- **BLOCKED**: tracking method names are present in generated metrics — final run required.
- **BLOCKED**: no NaN or infinite metric values — final run required.
- **BLOCKED**: failure rates are between 0 and 1 — final run required.
- **BLOCKED**: errors are nonnegative — final run required.
- **BLOCKED**: confidence intervals are sensible — final run required.
- **PASS**: no existing expanded-seed result file was overwritten locally.
- **PASS**: `paper/main.tex` was not modified locally.
- **BLOCKED**: results are scientifically plausible — final run required.
- **PASS**: evaluator is implemented to report honestly if tracking beats adaptive fusion.
- **PASS**: evaluator is implemented to report honestly if tracking fails to help.

## Required action

Please run the tracking-baseline-evidence workflow from GitHub Actions. A successful workflow final run replaces this blocked handoff report with the complete numeric sanity check.
