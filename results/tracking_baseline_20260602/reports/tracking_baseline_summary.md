# Tracking Baseline Summary

- Experiment: fixed-parameter constant-velocity Kalman tracking baseline
- Branch: codex/tracking-baseline-evidence
- Generated UTC: 2026-06-02T17:56:44.240137+00:00
- Command used: python -m src.tracking_baseline_experiments --config configs/expanded_seeds.yaml --mode final
- Config path: configs/expanded_seeds.yaml
- Seed list: [101, 102, 103, 104, 105, 106, 107, 108, 109, 110]
- Number of seeds: 10
- Scenarios: ['s1_clean', 's2_wifi_degraded', 's3_vlp_blocked', 's4_mixed_dynamic']
- Methods evaluated: ['kalman_wifi_only', 'kalman_vlp_only', 'kalman_static_fusion', 'kalman_static_fusion_median']
- 
- IMPLEMENTATION SUMMARY
- State vector: [x, y, vx, vy]
- Transition: x_t=x_(t-1)+vx; y_t=y_(t-1)+vy; dt=1

## Scenario comparisons

- **s1_clean**: Best tracking beats adaptive fusion on mean error. Best tracking `kalman_vlp_only` = 0.375040 m; adaptive fusion = 0.467598 m.
- **s2_wifi_degraded**: Best tracking beats adaptive fusion on mean error. Best tracking `kalman_vlp_only` = 0.368192 m; adaptive fusion = 0.470734 m.
- **s3_vlp_blocked**: Adaptive fusion retains lower mean error than best tracking. Best tracking `kalman_static_fusion` = 0.813788 m; adaptive fusion = 0.805788 m.
- **s4_mixed_dynamic**: Adaptive fusion retains lower mean error than best tracking. Best tracking `kalman_static_fusion` = 0.651270 m; adaptive fusion = 0.644397 m.
