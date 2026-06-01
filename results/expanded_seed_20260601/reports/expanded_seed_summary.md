# Expanded 10-Seed Evaluation Summary

Command: `python -m src.expanded_seed_experiments --config configs/expanded_seeds.yaml --mode final`

## Numeric Summary

```text
Expanded-seed numeric summary
Seed list: [101, 102, 103, 104, 105, 106, 107, 108, 109, 110]
Number of seeds: 10
Scenarios: ['s1_clean', 's2_wifi_degraded', 's3_vlp_blocked', 's4_mixed_dynamic']
Methods: ['adaptive_fusion', 'graph_diffusion_1', 'graph_diffusion_3', 'laplacian', 'static_fusion', 'static_fusion_ema', 'static_fusion_median', 'static_fusion_moving_average', 'static_fusion_raw', 'static_raw', 'vlp_only', 'wifi_only']
Best method per scenario:
- s1_clean: static_fusion (mean error 0.467132 m)
- s2_wifi_degraded: vlp_only (mean error 0.470537 m)
- s3_vlp_blocked: adaptive_fusion (mean error 0.805788 m)
- s4_mixed_dynamic: adaptive_fusion (mean error 0.644397 m)
s3_vlp_blocked: static_fusion vs adaptive_fusion
- mean error: 1.077862 m vs 0.805788 m; improvement 25.242%
- P90 error: 2.908838 m vs 1.704751 m; improvement 41.394%
- failure rate: 0.184000 vs 0.083000; adaptive-static change -0.101000
- smoothness: 1.329031 vs 0.679043 m/step; adaptive-static change -0.649988
s4_mixed_dynamic: static_fusion vs adaptive_fusion
- mean error: 0.810519 m vs 0.644397 m; improvement 20.496%
- P90 error: 1.956960 m vs 1.253606 m; improvement 35.941%
- failure rate: 0.103000 vs 0.040000; adaptive-static change -0.063000
- smoothness: 0.980000 vs 0.570835 m/step; adaptive-static change -0.409165
Old 5-seed conclusion remained stable: yes
Paper claim recommendation: preserved
```

## Sanity Check

The complete sanity-check report is saved at `results/expanded_seed_20260601/reports/02_sanity_check_report.md`.

# Expanded-Seed Sanity Check Report

The final 10-seed evidence was checked after generation. `PASS` means the stated safety condition is satisfied.

1. **PASS — Did every expected CSV exist?**
   - results/expanded_seed_20260601/raw/errors_by_seed_scenario_method_expanded.csv, results/expanded_seed_20260601/tables/table_main_expanded_seed_results.csv, results/expanded_seed_20260601/tables/table_ablation_expanded_seed_results.csv, results/expanded_seed_20260601/tables/table_seed_stability_comparison.csv, results/expanded_seed_20260601/tables/table_best_method_by_scenario.csv
2. **PASS — Did every expected LaTeX table exist?**
   - paper/tables/expanded_seed_20260601/compact_main_results_expanded.tex, paper/tables/expanded_seed_20260601/compact_ablation_expanded.tex, paper/tables/expanded_seed_20260601/compact_seed_stability.tex
3. **PASS — Are all seeds 101--110 present?**
   - [101, 102, 103, 104, 105, 106, 107, 108, 109, 110]
4. **PASS — Are all four scenarios present?**
   - ['s1_clean', 's2_wifi_degraded', 's3_vlp_blocked', 's4_mixed_dynamic']
5. **PASS — Are all key methods present?**
   - ['static_fusion', 'static_fusion_median', 'graph_diffusion_3', 'adaptive_fusion']
6. **PASS — Are there NaN or infinite metric values?**
   - No non-finite metric values detected
7. **PASS — Are failure rates between 0 and 1?**
   - All failure rates are bounded
8. **PASS — Are localization errors nonnegative?**
   - All localization errors are nonnegative
9. **PASS — Are confidence intervals sensible?**
   - Each reported mean lies within its Student-t 95% interval
10. **PASS — Does the method ranking make scientific sense?**
   - Ranking varies by scenario; no universal-best claim is made
11. **PASS — Did adaptive fusion still help in VLP-blocked and mixed-dynamic scenarios?**
   - Adaptive fusion has lower mean error than static fusion in both difficult scenarios
12. **PASS — Are there any claims that should be weakened?**
   - Preserve the conditional claim; do not strengthen to a universal-best claim
13. **PASS — Is the result strong enough for paper update?**
   - Expanded evidence is suitable for a later paper update after review
14. **PASS — Did any command fail?**
   - Smoke and final pipelines completed without command failures
15. **PASS — Was any output regenerated from old stale data by mistake?**
   - Fresh metrics came from .expanded_seed_work/final; old table is used only for explicit five-seed comparison

## Statistical method

Across-seed 95% confidence intervals use `scipy.stats.t.ppf(0.975, n_seeds - 1)` and `mean ± t_critical * std / sqrt(n_seeds)`.

## Scientific interpretation

The ranking remains scenario-dependent. Adaptive fusion should be described conditionally as useful under VLP blockage and mixed dynamic degradation, not as universally optimal.
