# Expanded 10-Seed Evidence Audit

## Scope

This audit checks the saved expanded-seed artifacts without rerunning or recomputing the experiment. It uses the existing numeric summary and sanity report, with file-existence verification for the required generated artifacts.

## Audit checklist

1. **PASS — Does `expanded_seed_numeric_summary.txt` exist?**
   - `results/expanded_seed_20260601/reports/expanded_seed_numeric_summary.txt`
2. **PASS — Does `02_sanity_check_report.md` exist?**
   - `results/expanded_seed_20260601/reports/02_sanity_check_report.md`
3. **PASS — Do all required CSV result files exist?**
   - `results/expanded_seed_20260601/raw/errors_by_seed_scenario_method_expanded.csv`: PASS
   - `results/expanded_seed_20260601/tables/table_main_expanded_seed_results.csv`: PASS
   - `results/expanded_seed_20260601/tables/table_ablation_expanded_seed_results.csv`: PASS
   - `results/expanded_seed_20260601/tables/table_seed_stability_comparison.csv`: PASS
   - `results/expanded_seed_20260601/tables/table_best_method_by_scenario.csv`: PASS
4. **PASS — Do all required LaTeX table files exist?**
   - `paper/tables/expanded_seed_20260601/compact_main_results_expanded.tex`: PASS
   - `paper/tables/expanded_seed_20260601/compact_ablation_expanded.tex`: PASS
   - `paper/tables/expanded_seed_20260601/compact_seed_stability.tex`: PASS
5. **PASS — Does the seed list contain 101–110?**
   - Saved seed list: `[101, 102, 103, 104, 105, 106, 107, 108, 109, 110]`
6. **PASS — Are all four scenarios present?**
   - Saved scenarios: `['s1_clean', 's2_wifi_degraded', 's3_vlp_blocked', 's4_mixed_dynamic']`
7. **PASS — Are key methods present?**
   - Required key methods: `['static_fusion', 'static_fusion_median', 'graph_diffusion_3', 'adaptive_fusion']`
8. **PASS — Is the old 5-seed conclusion stable?**
   - Existing numeric summary reports: `Old 5-seed conclusion remained stable: yes`.
9. **PASS — Does adaptive fusion improve over static fusion in `s3_vlp_blocked`?**
   - Existing numeric summary reports a `25.242%` mean-error improvement (`1.077862 m` to `0.805788 m`).
10. **PASS — Does adaptive fusion improve over static fusion in `s4_mixed_dynamic`?**
    - Existing numeric summary reports a `20.496%` mean-error improvement (`0.810519 m` to `0.644397 m`).
11. **PASS — Are paper claims still conditional, not universal-best?**
    - The existing sanity report says ranking varies by scenario and no universal-best claim is made. The numeric summary recommendation is `preserved`.
12. **PASS — Are there any red flags before paper update?**
    - No red flags were found in the required artifact, seed, scenario, method, stability, or conditional-claim checks. The saved sanity report also records no non-finite metrics, bounded failure rates, nonnegative localization errors, sensible confidence intervals, no command failures, and fresh final-run metrics.

## Conclusion

The expanded 10-seed evidence is internally consistent with the saved sanity report and is suitable for a later, separate paper update after review. Adaptive fusion should continue to be described conditionally as useful in the difficult VLP-blocked and mixed-dynamic scenarios, not as universally optimal.
