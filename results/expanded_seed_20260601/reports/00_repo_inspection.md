# Expanded-Seed Evaluation: Initial Repository Inspection

## Scope and preservation rule

This inspection was completed before running the expanded evaluation. The existing five-seed outputs under `results/raw/`, `results/processed/`, `results/tables/`, `results/figures/`, and `results/logs/` are treated as the original evidence and must not be overwritten or deleted. The expanded workflow therefore runs the unchanged stage modules in an isolated workspace and publishes new evidence only under `results/expanded_seed_20260601/` and `paper/tables/expanded_seed_20260601/`.

## Existing seed list

`configs/default.yaml` defines training seeds `[1, 2, 3, 4, 5]` and held-out test seeds `[101, 102, 103, 104, 105]` under `project.seed_train` and `project.seed_test`.

## Existing main experiment runner

`src/final_experiments.py` is the existing repeated-seed runner. For each requested seed it invokes, in order:

1. `src.environment`
2. `src.signal_models`
3. `src.baselines`
4. `src.dsp_filters`
5. `src.dsp_evaluation`
6. `src.gsp_evaluation --estimate-method expected`
7. `src.adaptive_fusion --estimate-method argmax`

The stage modules use relative `results/...` paths. The new wrapper must preserve that pipeline while changing the current working directory to an isolated workspace so that the original five-seed artifacts are not overwritten.

## Existing output files

The existing pipeline already contains five-seed per-seed artifacts and aggregate evidence, including:

- `results/tables/table_final_method_comparison_long.csv`
- `results/tables/table_ablation.csv`
- `results/tables/table_baseline_comparison.csv`
- `results/tables/table_runtime.csv`
- per-seed baseline, DSP, GSP, and adaptive metric tables for seeds 101--105
- scenario masks and signal files under `results/raw/`
- prediction files under `results/processed/`
- paper-oriented tables and figures under `results/tables/` and `results/figures/`

The expanded runner reads `results/tables/table_final_method_comparison_long.csv` only as the preserved old five-seed comparison source. It writes no expanded output into those legacy directories.

## Existing method names

The existing final long table combines these families and labels:

- Baselines: `wifi_only`, `vlp_only`, `static_fusion`
- DSP static variants: `static_fusion_moving_average`, `static_fusion_median`, `static_fusion_ema`
- GSP expected-position methods: `static_raw`, `graph_diffusion_1`, `graph_diffusion_3`, `laplacian`
- Adaptive method: `adaptive_fusion`

The main expanded ablation focuses on `wifi_only`, `vlp_only`, `static_fusion`, `static_fusion_median`, `graph_diffusion_3`, and `adaptive_fusion`.

## Risks identified before execution

1. `src/final_experiments.get_test_seeds()` checks `seeds.test` and `random_seeds.test`, but does not read the existing `project.seed_test`. The expanded wrapper must explicitly read `project.seed_test` for compatibility with the repository config.
2. Stage modules write to relative legacy-style `results/...` paths. Running them from the repository root would overwrite old artifacts for seeds 101--105. The expanded wrapper must use an isolated working directory.
3. Some shared figure and summary names are overwritten within a single isolated run as seeds advance. These are diagnostic stage artifacts; the required expanded numeric evidence must be aggregated from per-seed metric CSV files.
4. Existing five-seed values are retained as a comparison baseline. The expanded aggregation must use freshly generated final-workspace artifacts for all seeds 101--110, not a mixture of old and new files.
5. Confidence intervals require a Student-t critical value. The wrapper should use `scipy.stats.t` and fail clearly if SciPy is unavailable rather than silently changing the statistical method.
6. `paper/main.tex` already contains five-seed narrative values. It must remain unchanged until the expanded evidence is reviewed.
