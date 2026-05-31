# SPICSCON 2026 paper quality checklist

## 1. Page count

- [ ] **Final IEEEtran page count:** confirm after a local build with `cd paper && bash build_paper.sh`.
- [ ] Confirm that the locally generated PDF remains within the official conference page limit after that limit is independently verified.

## 2. PDF size

- [ ] Build `paper/build/main.pdf` locally and record its size.
- [ ] Keep the locally generated PDF below the recorded approximately **2 MB** target if that requirement is confirmed by the conference.

## 3. Build status

- [ ] **Submission PDF build:** run locally with `cd paper && bash build_paper.sh`.
- [x] **Text-only PR:** copied PNG figures and generated PDFs are intentionally excluded because binary files are not supported in the Codex review UI.
- [x] **Local asset workflow:** `paper/prepare_assets.sh` copies required figures from `results/figures/` into `paper/figures/` before compilation.
- [ ] Inspect the locally generated LaTeX log for unresolved references, bibliography errors, and layout warnings.

## 4. Figures included by the LaTeX source

Run `bash paper/prepare_assets.sh` from the repository root, or `bash prepare_assets.sh` from `paper/`, before compiling. The script copies:

1. `fig1_layout_trajectory.png` — indoor layout and sample trajectory.
2. `fig3_noisy_vs_filtered_signals.png` — noisy versus filtered signal traces.
3. `fig4_raw_vs_graph_smoothed_heatmap.png` — raw versus graph-smoothed heatmaps.
4. `fig5_scenario_wise_error_paper.png` — scenario-wise localization error.
5. `fig7_failure_smoothness_paper.png` — failure-rate and smoothness robustness.
6. `fig8_physical_sanity_wifi_light.png` — optional smartphone-based physical sanity trends.

The architecture diagram is written directly in TikZ inside `main.tex`: WiFi RSSI-like and VLP intensity-like signals → DSP filtering → probability maps → graph smoothing → reliability-aware adaptive fusion → final position estimate.

## 5. Tables included

The LaTeX source includes:

1. Table I — manually written simulation and scenario parameters.
2. Table II — compact main repeated-seed result comparison from `tables/compact_main_results.tex`.
3. Table III — compact difficult-scenario ablation from `tables/compact_ablation.tex`.

Traceability copies retained in `paper/tables/`:

- `table_main_results_paper.tex`
- `table_ablation_paper.tex`
- `table_best_method_summary_paper.tex`

## 6. References count

- [x] **14** bibliography entries are present.
- [x] Every in-text citation key has a BibTeX entry.
- [x] Every BibTeX entry is cited.
- [x] Entries were selected from `Literature_Review/spicscon2026_literature_gap_matrix.xlsx` rows marked verified; no DOI was invented.

## 7. Unresolved TODOs

- [ ] Confirm Dr. Md. Nazrul Islam Mondal’s full affiliation from an authoritative source and replace the visible TODO placeholder.
- [ ] Add verified email addresses for all three authors and replace the visible TODO placeholder.
- [ ] Compile locally with TeX Live and inspect layout warnings.
- [ ] Reconfirm official conference rules immediately before submission.
- [ ] Decide whether any conference-specific AI-use disclosure is required under the applicable IEEE and SPICSCON 2026 instructions.

## 8. Unverified citations, if any

- [x] No unverified citation is used in the final bibliography.
- [x] Candidate citations with incomplete author lists or only partial local verification were excluded.

## 9. Official SPICSCON instruction verification status

### Verified online

- [x] The public Microsoft CMT landing page at `https://cmt3.research.microsoft.com/SPICSCON2026` exists and identifies **IEEE International Conference on Signal Processing, Information, Communication and Systems 2026**.
- [x] Submission is therefore associated with the SPICSCON 2026 Microsoft CMT portal.

### Recorded in local project resources, but not independently confirmed from an accessible official SPICSCON 2026 author-guidelines page

- [ ] IEEE conference two-column style.
- [ ] Paper length of 4–6 pages including figures, tables, and references.
- [ ] PDF file-size target of approximately 2 MB.
- [ ] Use of a conference/IEEE template.
- [ ] PDF submission format.
- [ ] IEEE numbered reference style.

### Unverified conference instructions

The following items could not be confirmed from an accessible official SPICSCON 2026 author-guidelines page and must be checked before submission:

- [ ] Whether the initial submission must include author names or be anonymized.
- [ ] Exact final PDF file-size limit.
- [ ] Exact page-limit wording and whether any overlength pages are permitted.
- [ ] Exact paper-size requirement (A4 or US Letter).
- [ ] Whether PDF eXpress or another IEEE PDF validation flow is required for initial or final submission.
- [ ] Any conference-specific plagiarism/similarity threshold or formatting-screening rule.
- [ ] Whether an AI-use disclosure statement is required and where it must appear.

No unverified item is stated in the paper as an official conference rule.

## 10. Claim boundary check

- [x] No real deployment claim.
- [x] No state-of-the-art claim.
- [x] No new WiFi propagation-model claim.
- [x] No new VLP optical-model claim.
- [x] No new RL-algorithm claim.
- [x] Physical sanity check is explicitly limited to motivation and is not described as real localization validation.
- [x] Adaptive fusion is described as reliability-aware, lightweight, transparent, and based on predefined fusion modes.
- [x] Results explicitly state that adaptive fusion is not universally best.
- [x] Clean scenario identifies static fusion as best.
- [x] WiFi-degraded scenario identifies VLP-only estimation as best.
- [x] VLP-blocked and mixed-dynamic scenarios identify adaptive fusion as best.
- [x] Key numerical results are traceable to existing repeated-seed result files under `results/tables/` and `results/logs/`.
