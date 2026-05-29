"""
Repeated-seed final experiment runner for the SPICSCON 2026 project.

This script runs the current full simulation/evaluation pipeline for multiple
test seeds and aggregates paper-ready results.

Pipeline per seed:
1. Environment/trajectory/scenario masks
2. WiFi/VLP signal generation
3. Baselines
4. DSP filtering
5. DSP localization evaluation
6. GSP evaluation with expected-position estimation
7. Adaptive reliability-based fusion

Final outputs:
- table_scenario_params.csv
- table_baseline_comparison.csv
- table_ablation.csv
- table_runtime.csv
- table_final_method_comparison_long.csv
- fig5_scenario_wise_error.png
- final_experiment_summary.json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Mapping

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.utils import ensure_dir, load_config, save_csv, save_json


SCENARIOS = [
    "s1_clean",
    "s2_wifi_degraded",
    "s3_vlp_blocked",
    "s4_mixed_dynamic",
]


METRIC_COLUMNS = [
    "mean_error_m",
    "median_error_m",
    "p90_error_m",
    "zone_accuracy",
    "failure_rate",
    "trajectory_smoothness_m_per_step",
]


def run_command(command: list[str]) -> str:
    """
    Run a command and return stdout/stderr combined.

    Raises RuntimeError if the command fails.
    """
    print("RUN:", " ".join(command), flush=True)

    result = subprocess.run(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    print(result.stdout, flush=True)

    if result.returncode != 0:
        raise RuntimeError(
            "Command failed with return code "
            f"{result.returncode}: {' '.join(command)}\n{result.stdout}"
        )

    return result.stdout


def get_test_seeds(cfg: Mapping, explicit_seeds: list[int] | None = None) -> list[int]:
    """
    Get repeated-test seeds from config or CLI.
    """
    if explicit_seeds:
        return explicit_seeds

    if "seeds" in cfg and "test" in cfg["seeds"]:
        return [int(x) for x in cfg["seeds"]["test"]]

    if "random_seeds" in cfg and "test" in cfg["random_seeds"]:
        return [int(x) for x in cfg["random_seeds"]["test"]]

    return [101, 102, 103, 104, 105]


def run_pipeline_for_seed(config_path: str, seed: int) -> list[str]:
    """
    Run all needed modules for one seed.
    """
    logs: list[str] = []

    commands = [
        [sys.executable, "-m", "src.environment", "--config", config_path, "--seed", str(seed)],
        [sys.executable, "-m", "src.signal_models", "--config", config_path, "--seed", str(seed)],
        [sys.executable, "-m", "src.baselines", "--config", config_path, "--seed", str(seed)],
        [sys.executable, "-m", "src.dsp_filters", "--config", config_path, "--seed", str(seed)],
        [sys.executable, "-m", "src.dsp_evaluation", "--config", config_path, "--seed", str(seed)],
        [
            sys.executable,
            "-m",
            "src.gsp_evaluation",
            "--config",
            config_path,
            "--seed",
            str(seed),
            "--estimate-method",
            "expected",
        ],
        [
            sys.executable,
            "-m",
            "src.adaptive_fusion",
            "--config",
            config_path,
            "--seed",
            str(seed),
            "--estimate-method",
            "argmax",
        ],
    ]

    for command in commands:
        logs.append(run_command(command))

    return logs


def read_csv_with_seed(path: Path, seed: int) -> pd.DataFrame:
    """
    Read a CSV and attach seed if needed.
    """
    if not path.exists():
        raise FileNotFoundError(f"Missing expected file: {path}")

    df = pd.read_csv(path)

    if "seed" not in df.columns:
        df.insert(0, "seed", seed)

    return df


def aggregate_mean_std(
    df: pd.DataFrame,
    group_cols: list[str],
    value_cols: list[str],
) -> pd.DataFrame:
    """
    Aggregate repeated-seed metrics as mean/std.
    """
    grouped = df.groupby(group_cols, dropna=False)

    pieces = []

    for col in value_cols:
        mean_s = grouped[col].mean().rename(f"{col}_mean")
        std_s = grouped[col].std(ddof=1).fillna(0.0).rename(f"{col}_std")
        pieces.extend([mean_s, std_s])

    out = pd.concat(pieces, axis=1).reset_index()
    return out


def collect_scenario_params(seeds: list[int]) -> pd.DataFrame:
    """
    Collect scenario mask statistics across seeds.
    """
    rows = []

    for seed in seeds:
        for scenario in SCENARIOS:
            path = Path(f"results/raw/scenario_masks_seed{seed}_{scenario}.csv")

            if not path.exists():
                raise FileNotFoundError(f"Missing scenario mask: {path}")

            df = pd.read_csv(path)

            rows.append(
                {
                    "seed": seed,
                    "scenario": scenario,
                    "num_steps": int(len(df)),
                    "wifi_degraded_steps": int(df["wifi_degraded"].sum()),
                    "vlp_blocked_steps": int(df["vlp_blocked"].sum()),
                    "mixed_dynamic_steps": int(df["mixed_dynamic"].sum()),
                    "wifi_degraded_fraction": float(df["wifi_degraded"].mean()),
                    "vlp_blocked_fraction": float(df["vlp_blocked"].mean()),
                    "mixed_dynamic_fraction": float(df["mixed_dynamic"].mean()),
                }
            )

    return pd.DataFrame(rows)


def collect_baseline_metrics(seeds: list[int]) -> pd.DataFrame:
    """
    Collect baseline metrics across seeds.
    """
    frames = []

    for seed in seeds:
        path = Path(f"results/tables/table_baseline_metrics_seed{seed}.csv")
        frames.append(read_csv_with_seed(path, seed))

    return pd.concat(frames, ignore_index=True)


def collect_dsp_metrics(seeds: list[int]) -> pd.DataFrame:
    """
    Collect DSP localization metrics across seeds.
    """
    frames = []

    for seed in seeds:
        path = Path(f"results/tables/table_dsp_localization_metrics_seed{seed}.csv")
        frames.append(read_csv_with_seed(path, seed))

    return pd.concat(frames, ignore_index=True)


def collect_gsp_metrics(seeds: list[int]) -> pd.DataFrame:
    """
    Collect GSP localization metrics across seeds.
    """
    frames = []

    for seed in seeds:
        path = Path(f"results/tables/table_gsp_metrics_seed{seed}.csv")
        frames.append(read_csv_with_seed(path, seed))

    return pd.concat(frames, ignore_index=True)


def collect_adaptive_metrics(seeds: list[int]) -> pd.DataFrame:
    """
    Collect adaptive-fusion metrics across seeds.
    """
    frames = []

    for seed in seeds:
        path = Path(f"results/tables/table_adaptive_fusion_metrics_seed{seed}.csv")
        frames.append(read_csv_with_seed(path, seed))

    return pd.concat(frames, ignore_index=True)


def collect_runtime_tables(seeds: list[int]) -> pd.DataFrame:
    """
    Collect runtime results across methods.
    """
    frames = []

    for seed in seeds:
        runtime_sources = [
            ("baseline", Path(f"results/tables/table_baseline_runtime_seed{seed}.csv")),
            ("gsp", Path(f"results/tables/table_gsp_runtime_seed{seed}.csv")),
            ("adaptive", Path(f"results/tables/table_adaptive_runtime_seed{seed}.csv")),
        ]

        for family, path in runtime_sources:
            if not path.exists():
                raise FileNotFoundError(f"Missing runtime file: {path}")

            df = pd.read_csv(path)
            df.insert(0, "method_family", family)

            if "seed" not in df.columns:
                df.insert(0, "seed", seed)

            frames.append(df)

    return pd.concat(frames, ignore_index=True)


def build_final_method_long_table(
    baseline_df: pd.DataFrame,
    dsp_df: pd.DataFrame,
    gsp_df: pd.DataFrame,
    adaptive_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build long method table combining key methods from different stages.
    """
    frames = []

    # Baseline methods.
    baseline_keep = baseline_df.copy()
    baseline_keep["method_family"] = "baseline"
    baseline_keep["method_label"] = baseline_keep["method"]
    frames.append(
        baseline_keep[
            ["seed", "scenario", "method_family", "method_label"] + METRIC_COLUMNS
        ]
    )

    # DSP static variants.
    dsp_static = dsp_df[dsp_df["method"] == "static_fusion"].copy()
    dsp_static["method_family"] = "dsp_static"
    dsp_static["method_label"] = "static_fusion_" + dsp_static["signal_variant"].astype(str)
    frames.append(
        dsp_static[
            ["seed", "scenario", "method_family", "method_label"] + METRIC_COLUMNS
        ]
    )

    # GSP methods.
    gsp_keep = gsp_df.copy()
    gsp_keep["method_family"] = "gsp_expected"
    gsp_keep["method_label"] = gsp_keep["gsp_method"]
    frames.append(
        gsp_keep[
            ["seed", "scenario", "method_family", "method_label"] + METRIC_COLUMNS
        ]
    )

    # Adaptive.
    adaptive_keep = adaptive_df.copy()
    adaptive_keep["method_family"] = "adaptive"
    adaptive_keep["method_label"] = "adaptive_fusion"
    frames.append(
        adaptive_keep[
            ["seed", "scenario", "method_family", "method_label"] + METRIC_COLUMNS
        ]
    )

    return pd.concat(frames, ignore_index=True)


def build_ablation_table(final_long: pd.DataFrame) -> pd.DataFrame:
    """
    Build a compact ablation table from selected representative methods.

    Selected methods:
    - WiFi-only
    - VLP-only
    - static fusion
    - static fusion + median DSP
    - graph diffusion 3 expected-position GSP
    - adaptive fusion
    """
    selected = final_long[
        (
            (final_long["method_family"] == "baseline")
            & final_long["method_label"].isin(["wifi_only", "vlp_only", "static_fusion"])
        )
        | (
            (final_long["method_family"] == "dsp_static")
            & (final_long["method_label"] == "static_fusion_median")
        )
        | (
            (final_long["method_family"] == "gsp_expected")
            & (final_long["method_label"] == "graph_diffusion_3")
        )
        | (
            (final_long["method_family"] == "adaptive")
            & (final_long["method_label"] == "adaptive_fusion")
        )
    ].copy()

    selected["ablation_stage"] = selected["method_label"].map(
        {
            "wifi_only": "WiFi only",
            "vlp_only": "VLP only",
            "static_fusion": "Static fusion",
            "static_fusion_median": "Static fusion + median DSP",
            "graph_diffusion_3": "Static fusion + graph diffusion",
            "adaptive_fusion": "Adaptive DSP+GSP fusion",
        }
    )

    return aggregate_mean_std(
        selected,
        group_cols=["scenario", "ablation_stage"],
        value_cols=METRIC_COLUMNS,
    )


def plot_scenario_wise_error(final_long: pd.DataFrame, output_path: str | Path) -> Path:
    """
    Plot scenario-wise mean error for selected methods.
    """
    output_path = Path(output_path)
    ensure_dir(output_path.parent)

    selected_labels = [
        "wifi_only",
        "vlp_only",
        "static_fusion",
        "static_fusion_median",
        "graph_diffusion_3",
        "adaptive_fusion",
    ]

    plot_df = final_long[final_long["method_label"].isin(selected_labels)].copy()

    agg = (
        plot_df.groupby(["scenario", "method_label"])["mean_error_m"]
        .agg(["mean", "std"])
        .reset_index()
    )
    agg["std"] = agg["std"].fillna(0.0)

    scenarios = SCENARIOS
    methods = selected_labels

    x = np.arange(len(scenarios))
    width = 0.12

    fig, ax = plt.subplots(figsize=(11.5, 5.2))

    for i, method in enumerate(methods):
        method_df = agg[agg["method_label"] == method].set_index("scenario")
        means = [method_df.loc[s, "mean"] if s in method_df.index else np.nan for s in scenarios]
        stds = [method_df.loc[s, "std"] if s in method_df.index else 0.0 for s in scenarios]

        offset = (i - (len(methods) - 1) / 2.0) * width
        ax.bar(x + offset, means, width, yerr=stds, capsize=2, label=method)

    ax.set_xticks(x)
    ax.set_xticklabels(scenarios, rotation=15, ha="right")
    ax.set_ylabel("Mean localization error (m)")
    ax.set_title("Scenario-wise Localization Error Across Methods")
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend(fontsize=8, ncols=2)

    fig.tight_layout()
    fig.savefig(output_path, dpi=300)
    plt.close(fig)

    return output_path


def build_final_outputs(config_path: str, seeds: list[int], skip_run: bool = False) -> Dict[str, str]:
    """
    Run repeated seed experiments and aggregate final outputs.
    """
    cfg = load_config(config_path)

    ensure_dir("results/logs")
    ensure_dir("results/tables")
    ensure_dir("results/figures")

    run_logs: dict[str, list[str]] = {}

    if not skip_run:
        for seed in seeds:
            run_logs[str(seed)] = run_pipeline_for_seed(config_path=config_path, seed=seed)

    scenario_params = collect_scenario_params(seeds)
    baseline_metrics = collect_baseline_metrics(seeds)
    dsp_metrics = collect_dsp_metrics(seeds)
    gsp_metrics = collect_gsp_metrics(seeds)
    adaptive_metrics = collect_adaptive_metrics(seeds)
    runtime_metrics = collect_runtime_tables(seeds)

    final_long = build_final_method_long_table(
        baseline_df=baseline_metrics,
        dsp_df=dsp_metrics,
        gsp_df=gsp_metrics,
        adaptive_df=adaptive_metrics,
    )

    baseline_comparison = aggregate_mean_std(
        baseline_metrics,
        group_cols=["scenario", "method"],
        value_cols=METRIC_COLUMNS,
    )

    ablation = build_ablation_table(final_long)

    runtime_group_cols = ["method_family", "scenario"]

    if "method" in runtime_metrics.columns:
        runtime_metrics["runtime_method"] = runtime_metrics["method"]
    elif "gsp_method" in runtime_metrics.columns:
        runtime_metrics["runtime_method"] = runtime_metrics["gsp_method"]
    else:
        runtime_metrics["runtime_method"] = "unknown"

    if "gsp_method" in runtime_metrics.columns:
        runtime_metrics["runtime_method"] = runtime_metrics["runtime_method"].fillna(
            runtime_metrics["gsp_method"]
        )

    runtime_comparison = aggregate_mean_std(
        runtime_metrics,
        group_cols=["method_family", "scenario", "runtime_method"],
        value_cols=["mean_runtime_ms_per_step"],
    )

    outputs = {}

    paths = {
        "scenario_params": "results/tables/table_scenario_params.csv",
        "baseline_comparison": "results/tables/table_baseline_comparison.csv",
        "ablation": "results/tables/table_ablation.csv",
        "runtime": "results/tables/table_runtime.csv",
        "final_method_long": "results/tables/table_final_method_comparison_long.csv",
    }

    save_csv(scenario_params, paths["scenario_params"])
    save_csv(baseline_comparison, paths["baseline_comparison"])
    save_csv(ablation, paths["ablation"])
    save_csv(runtime_comparison, paths["runtime"])
    save_csv(final_long, paths["final_method_long"])

    outputs.update(paths)

    fig_path = plot_scenario_wise_error(
        final_long=final_long,
        output_path="results/figures/fig5_scenario_wise_error.png",
    )
    outputs["fig5_scenario_wise_error"] = str(fig_path)

    summary = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "config_path": config_path,
        "seeds": seeds,
        "skip_run": skip_run,
        "scenarios": SCENARIOS,
        "metric_columns": METRIC_COLUMNS,
        "outputs": outputs,
        "run_logs": run_logs,
    }

    summary_path = "results/logs/final_experiment_summary.json"
    save_json(summary, summary_path)
    outputs["final_experiment_summary"] = summary_path

    return outputs


def parse_seed_list(seed_text: str | None) -> list[int] | None:
    """
    Parse comma-separated seed text.
    """
    if seed_text is None or not seed_text.strip():
        return None

    return [int(x.strip()) for x in seed_text.split(",") if x.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run repeated-seed final experiments and aggregate paper tables."
    )
    parser.add_argument(
        "--config",
        type=str,
        default="configs/default.yaml",
        help="Path to YAML config file.",
    )
    parser.add_argument(
        "--seeds",
        type=str,
        default=None,
        help="Comma-separated seed list. If omitted, uses config test seeds.",
    )
    parser.add_argument(
        "--skip-run",
        action="store_true",
        help="Only aggregate existing seed outputs; do not rerun modules.",
    )

    args = parser.parse_args()

    cfg = load_config(args.config)
    seeds = get_test_seeds(cfg, explicit_seeds=parse_seed_list(args.seeds))

    outputs = build_final_outputs(
        config_path=args.config,
        seeds=seeds,
        skip_run=args.skip_run,
    )

    print("FINAL EXPERIMENT TEST OK")
    print("Seeds:", seeds)
    for name, path in outputs.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
