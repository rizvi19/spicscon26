# GitHub Actions Instructions for Expanded-Seed Evidence

## Purpose

The earlier Codex-container failure was an infrastructure limitation, not a scientific result. The real expanded-seed evaluation begins only when the GitHub Actions workflow completes its smoke run and final ten-seed run successfully.

You do **not** need to run anything locally.

## Workflow location

The manually triggered workflow is:

```text
.github/workflows/expanded-seed-evidence.yml
```

Its GitHub Actions display name is **Expanded seed evidence**.

## How to run it from the GitHub UI

1. Open the repository on GitHub: `https://github.com/rizvi19/spicscon26`.
2. Open the **Actions** tab.
3. In the workflow list, select **Expanded seed evidence**.
4. Click **Run workflow**.
5. In the branch selector, choose `codex/research-evidence-upgrades` if it is available. The workflow now checks out and writes evidence to that target branch even if the UI dispatch branch differs.
6. Click the green **Run workflow** button.
7. Wait for the workflow to install dependencies, run the two-seed smoke experiment, and then run the final ten-seed experiment.

The workflow uploads an artifact even if execution fails. It also commits generated outputs, logs, and reports back to `codex/research-evidence-upgrades` when they change.

## Commands executed by the workflow

```bash
python -m src.expanded_seed_experiments --config configs/expanded_seeds.yaml --mode smoke
python -m src.expanded_seed_experiments --config configs/expanded_seeds.yaml --mode final
```

Smoke mode uses seeds `101` and `102`. Final mode uses seeds `101` through `110`.

## Files to check after a successful run

The most important quick-read file is:

```text
results/expanded_seed_20260601/reports/expanded_seed_numeric_summary.txt
```

Also review:

```text
results/expanded_seed_20260601/reports/expanded_seed_summary.md
results/expanded_seed_20260601/reports/02_sanity_check_report.md
results/expanded_seed_20260601/logs/expanded_seed_summary.json
results/expanded_seed_20260601/raw/errors_by_seed_scenario_method_expanded.csv
results/expanded_seed_20260601/tables/table_main_expanded_seed_results.csv
results/expanded_seed_20260601/tables/table_ablation_expanded_seed_results.csv
results/expanded_seed_20260601/tables/table_seed_stability_comparison.csv
results/expanded_seed_20260601/tables/table_best_method_by_scenario.csv
paper/tables/expanded_seed_20260601/compact_main_results_expanded.tex
paper/tables/expanded_seed_20260601/compact_ablation_expanded.tex
paper/tables/expanded_seed_20260601/compact_seed_stability.tex
```

## If the workflow fails

Download the uploaded `expanded-seed-evidence-<run-id>` artifact and inspect:

```text
results/expanded_seed_20260601/reports/github_actions_failure_report.md
results/expanded_seed_20260601/reports/github_actions_run_status.md
results/expanded_seed_20260601/logs/
```

Do not interpret an infrastructure or execution failure as a research conclusion. Do not update `paper/main.tex` until a complete ten-seed run has generated and passed the sanity checks.
