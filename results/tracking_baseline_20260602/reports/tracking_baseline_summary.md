# Tracking Baseline Summary

## Local execution status

Numeric evidence is **unavailable** because the local container lacks the repository's scientific Python dependencies and package installation is blocked by a proxy `403 Forbidden` response. No numeric claims are made from an experiment that did not execute.

## Implemented evaluator

The evaluator applies a fixed-parameter constant-velocity Kalman filter to WiFi-only, VLP-only, static-fusion, and median-filtered static-fusion per-step estimates. It initializes from the first observed localization estimate with zero velocity, never uses held-out ground truth for filtering, and does not tune Q/R on seeds 101--110.

## Required action

Please run the `tracking-baseline-evidence` workflow from GitHub Actions. A successful workflow run will replace this blocked handoff summary with complete ten-seed numeric evidence and an honest comparison against adaptive fusion.
