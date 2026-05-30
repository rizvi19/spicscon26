"""
Paper-ready table and figure generator for the SPICSCON 2026 project.

This script converts the final repeated-seed experiment outputs into cleaner,
paper-friendly assets with readable scenario/method labels.

Inputs:
- results/tables/table_final_method_comparison_long.csv
- results/tables/table_ablation.csv
- results/tables/table_runtime.csv

Outputs:
- paper-ready main result tables
- paper-ready ablation tables
- polished Fig. 5
- failure/smoothness summary figure
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.utils import ensure_dir, save_csv, save_json


SCENARIO_LABELS = {
    "s1_clean": "Clean",
    "s2_wifi_degraded": "WiFi degraded",
    "s3_vlp_blocked": "VLP blocked",
    "s4_mixed_dynamic": "Mixed dynamic",
}

METHOD_LABELS = {
    "wifi_only": "WiFi-only",
    "vlp_only": "VLP-only",
    "static_fusion": "Static fusion",
    "static_fusion_median": "Median-DSP fusion",
    "graph_diffusion_3": "Graph-smoothed fusion",
    "adaptive_fusion": "Adaptive fusion",
}

METHOD_ORDER = [
    "wifi_only",
    "vlp_only",
    "static_fusion",
    "static_fusion_median",
    "graph_diffusion_3",
    "adaptive_fusion",
]

SCENARIO_ORDER = [
    "s1_clean",
    "s2_wifi_degraded",
    "s3_vlp_blocked",
    "s4_mixed_dynamic",
]


def mean_std_string(mean_value: float, std_value: float, decimals: int = 3) -> str:
    """
    Format mean ± std for paper tables.
    """
    return f"{mean_value:.{decimals}f} ± {std_value:.{decimals}f}"


def load_final_long(path: str | Path = "results/tables/table_final_method_comparison_long.csv") -> pd.DataFrame:
    """
    Load final long repeated-seed method comparison table.
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            f"Missing {path}. Run: python -m src.final_experiments first."
        )

    return pd.read_csv(path)


def select_paper_methods(final_long: pd.DataFrame) -> pd.DataFrame:
    """
    Keep only the methods intended for paper-facing figures/tables.
    """
    selected = final_long[final_long["method_label"].isin(METHOD_ORDER)].copy()

    selected["scenario_label"] = selected["scenario"].map(SCENARIO_LABELS)
    selected["method_label_paper"] = selected["method_label"].map(METHOD_LABELS)

    selected["scenario_order"] = selected["scenario"].map(
        {name: idx for idx, name in enumerate(SCENARIO_ORDER)}
    )

    selected["method_order"] = selected["method_label"].map(
        {name: idx for idx, name in enumerate(METHOD_ORDER)}
    )

    return selected.sort_values(["scenario_order", "method_order", "seed"])


def aggregate_paper_metrics(selected: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate repeated-seed metrics for paper-ready tables.
    """
    metric_cols = [
        "mean_error_m",
        "p90_error_m",
        "zone_accuracy",
        "failure_rate",
        "trajectory_smoothness_m_per_step",
    ]

    grouped = selected.groupby(
        [
            "scenario",
            "scenario_label",
            "scenario_order",
            "method_label",
            "method_label_paper",
            "method_order",
        ],
        dropna=False,
    )

    rows = []

    for keys, group in grouped:
        (
            scenario,
            scenario_label,
            scenario_order,
            method_label,
            method_label_paper,
            method_order,
        ) = keys

        row = {
            "scenario": scenario,
            "scenario_label": scenario_label,
            "scenario_order": scenario_order,
            "method_label": method_label,
            "method": method_label_paper,
            "method_order": method_order,
            "num_seeds": int(group["seed"].nunique()),
        }

        for col in metric_cols:
            row[f"{col}_mean"] = float(group[col].mean())
            row[f"{col}_std"] = float(group[col].std(ddof=1))

        rows.append(row)

    out = pd.DataFrame(rows)
    return out.sort_values(["scenario_order", "method_order"])


def build_main_results_table(agg: pd.DataFrame) -> pd.DataFrame:
    """
    Build compact paper table with mean ± std strings.
    """
    table = agg.copy()

    out = pd.DataFrame(
        {
            "Scenario": table["scenario_label"],
            "Method": table["method"],
            "Mean error (m)": [
                mean_std_string(m, s)
                for m, s in zip(table["mean_error_m_mean"], table["mean_error_m_std"])
            ],
            "P90 error (m)": [
                mean_std_string(m, s)
                for m, s in zip(table["p90_error_m_mean"], table["p90_error_m_std"])
            ],
            "Failure rate": [
                mean_std_string(m, s)
                for m, s in zip(table["failure_rate_mean"], table["failure_rate_std"])
            ],
            "Smoothness (m/step)": [
                mean_std_string(m, s)
                for m, s in zip(
                    table["trajectory_smoothness_m_per_step_mean"],
                    table["trajectory_smoothness_m_per_step_std"],
                )
            ],
        }
    )

    return out


def build_best_method_summary(agg: pd.DataFrame) -> pd.DataFrame:
    """
    Build best method per scenario summary by mean error.
    """
    rows = []

    for scenario, group in agg.groupby("scenario"):
        best = group.sort_values("mean_error_m_mean").iloc[0]
        rows.append(
            {
                "Scenario": best["scenario_label"],
                "Best method": best["method"],
                "Mean error (m)": mean_std_string(
                    best["mean_error_m_mean"],
                    best["mean_error_m_std"],
                ),
                "P90 error (m)": mean_std_string(
                    best["p90_error_m_mean"],
                    best["p90_error_m_std"],
                ),
                "Failure rate": mean_std_string(
                    best["failure_rate_mean"],
                    best["failure_rate_std"],
                ),
            }
        )

    return pd.DataFrame(rows)


def save_markdown_and_latex(df: pd.DataFrame, base_path: str | Path) -> Dict[str, str]:
    """
    Save a DataFrame as CSV, Markdown, and LaTeX.
    """
    base_path = Path(base_path)
    ensure_dir(base_path.parent)

    csv_path = base_path.with_suffix(".csv")
    md_path = base_path.with_suffix(".md")
    tex_path = base_path.with_suffix(".tex")

    df.to_csv(csv_path, index=False)
    md_path.write_text(df.to_markdown(index=False), encoding="utf-8")
    tex_path.write_text(df.to_latex(index=False, escape=False), encoding="utf-8")

    return {
        "csv": str(csv_path),
        "markdown": str(md_path),
        "latex": str(tex_path),
    }


def plot_paper_fig5(agg: pd.DataFrame, output_path: str | Path) -> Path:
    """
    Polished scenario-wise mean-error figure for the paper.
    """
    output_path = Path(output_path)
    ensure_dir(output_path.parent)

    fig, ax = plt.subplots(figsize=(11.0, 4.8))

    scenarios = SCENARIO_ORDER
    methods = METHOD_ORDER

    x = np.arange(len(scenarios))
    width = 0.12

    for i, method in enumerate(methods):
        method_df = agg[agg["method_label"] == method].set_index("scenario")

        means = [
            method_df.loc[s, "mean_error_m_mean"] if s in method_df.index else np.nan
            for s in scenarios
        ]
        stds = [
            method_df.loc[s, "mean_error_m_std"] if s in method_df.index else 0.0
            for s in scenarios
        ]

        offset = (i - (len(methods) - 1) / 2.0) * width

        ax.bar(
            x + offset,
            means,
            width,
            yerr=stds,
            capsize=2,
            label=METHOD_LABELS[method],
        )

    ax.set_xticks(x)
    ax.set_xticklabels([SCENARIO_LABELS[s] for s in scenarios])
    ax.set_ylabel("Mean localization error (m)")
    ax.set_title("Scenario-wise Localization Error Across Methods")
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend(fontsize=8, ncols=3, loc="upper right")

    fig.tight_layout()
    fig.savefig(output_path, dpi=300)
    plt.close(fig)

    return output_path


def plot_failure_smoothness(agg: pd.DataFrame, output_path: str | Path) -> Path:
    """
    Plot failure-rate and smoothness summaries for key methods.
    """
    output_path = Path(output_path)
    ensure_dir(output_path.parent)

    key_methods = ["static_fusion", "static_fusion_median", "adaptive_fusion"]
    plot_df = agg[agg["method_label"].isin(key_methods)].copy()

    scenarios = SCENARIO_ORDER
    x = np.arange(len(scenarios))
    width = 0.22

    fig, axes = plt.subplots(2, 1, figsize=(9.5, 6.0), sharex=True)

    for i, method in enumerate(key_methods):
        method_df = plot_df[plot_df["method_label"] == method].set_index("scenario")
        offset = (i - (len(key_methods) - 1) / 2.0) * width

        failure_means = [
            method_df.loc[s, "failure_rate_mean"] if s in method_df.index else np.nan
            for s in scenarios
        ]
        failure_stds = [
            method_df.loc[s, "failure_rate_std"] if s in method_df.index else 0.0
            for s in scenarios
        ]

        smooth_means = [
            method_df.loc[s, "trajectory_smoothness_m_per_step_mean"] if s in method_df.index else np.nan
            for s in scenarios
        ]
        smooth_stds = [
            method_df.loc[s, "trajectory_smoothness_m_per_step_std"] if s in method_df.index else 0.0
            for s in scenarios
        ]

        axes[0].bar(
            x + offset,
            failure_means,
            width,
            yerr=failure_stds,
            capsize=2,
            label=METHOD_LABELS[method],
        )

        axes[1].bar(
            x + offset,
            smooth_means,
            width,
            yerr=smooth_stds,
            capsize=2,
            label=METHOD_LABELS[method],
        )

    axes[0].set_ylabel("Failure rate")
    axes[0].set_title("Failure Rate Across Key Fusion Methods")
    axes[0].grid(True, axis="y", alpha=0.3)
    axes[0].legend(fontsize=8, ncols=3)

    axes[1].set_ylabel("Smoothness (m/step)")
    axes[1].set_title("Trajectory Smoothness Across Key Fusion Methods")
    axes[1].grid(True, axis="y", alpha=0.3)
    axes[1].set_xticks(x)
    axes[1].set_xticklabels([SCENARIO_LABELS[s] for s in scenarios])

    fig.tight_layout()
    fig.savefig(output_path, dpi=300)
    plt.close(fig)

    return output_path


def build_paper_assets() -> Dict[str, object]:
    """
    Build all paper-ready assets.
    """
    ensure_dir("results/figures")
    ensure_dir("results/tables")
    ensure_dir("results/logs")

    final_long = load_final_long()
    selected = select_paper_methods(final_long)
    agg = aggregate_paper_metrics(selected)

    main_table = build_main_results_table(agg)
    best_table = build_best_method_summary(agg)

    main_paths = save_markdown_and_latex(
        main_table,
        "results/tables/table_main_results_paper",
    )

    best_paths = save_markdown_and_latex(
        best_table,
        "results/tables/table_best_method_summary_paper",
    )

    ablation_source = Path("results/tables/table_ablation.csv")
    if ablation_source.exists():
        ablation = pd.read_csv(ablation_source)
        ablation_paper = ablation.copy()
        ablation_paper["scenario"] = ablation_paper["scenario"].map(SCENARIO_LABELS)
        ablation_paper = ablation_paper.rename(
            columns={
                "scenario": "Scenario",
                "ablation_stage": "Method",
                "mean_error_m_mean": "Mean error mean",
                "mean_error_m_std": "Mean error std",
                "p90_error_m_mean": "P90 error mean",
                "p90_error_m_std": "P90 error std",
                "failure_rate_mean": "Failure rate mean",
                "failure_rate_std": "Failure rate std",
                "trajectory_smoothness_m_per_step_mean": "Smoothness mean",
                "trajectory_smoothness_m_per_step_std": "Smoothness std",
            }
        )
        ablation_paths = save_markdown_and_latex(
            ablation_paper,
            "results/tables/table_ablation_paper",
        )
    else:
        ablation_paths = {}

    fig5_path = plot_paper_fig5(
        agg=agg,
        output_path="results/figures/fig5_scenario_wise_error_paper.png",
    )

    fig7_path = plot_failure_smoothness(
        agg=agg,
        output_path="results/figures/fig7_failure_smoothness_paper.png",
    )

    outputs = {
        "main_results_table": main_paths,
        "best_method_table": best_paths,
        "ablation_table": ablation_paths,
        "fig5_paper": str(fig5_path),
        "fig7_failure_smoothness": str(fig7_path),
    }

    summary = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": "results/tables/table_final_method_comparison_long.csv",
        "selected_methods": METHOD_ORDER,
        "scenario_labels": SCENARIO_LABELS,
        "method_labels": METHOD_LABELS,
        "outputs": outputs,
    }

    save_json(summary, "results/logs/paper_assets_summary.json")

    outputs["paper_assets_summary"] = "results/logs/paper_assets_summary.json"

    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate paper-ready tables and figures."
    )
    parser.parse_args()

    outputs = build_paper_assets()

    print("PAPER ASSETS TEST OK")
    print(json.dumps(outputs, indent=2))


if __name__ == "__main__":
    main()
