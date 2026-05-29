"""
DSP filtering utilities for the SPICSCON 2026 indoor positioning simulation.

This module applies simple, transparent signal-processing filters:

1. Moving average filter
2. Median filter
3. Exponential moving average filter

The goal is not to invent a new DSP method. The goal is to create a reproducible
denoising stage and evaluate whether simple filtering improves robustness under
controlled WiFi noise and visible-light blockage.
"""

from __future__ import annotations

import argparse
import json
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

FILTERS = [
    "moving_average",
    "median",
    "ema",
]


def measured_wifi_columns(df: pd.DataFrame) -> List[str]:
    """
    Return measured WiFi RSSI columns, excluding clean/reference columns.
    """
    return [
        col
        for col in df.columns
        if col.startswith("wifi_ap") and col.endswith("_dbm") and "clean" not in col
    ]


def measured_vlp_columns(df: pd.DataFrame) -> List[str]:
    """
    Return measured VLP intensity columns, excluding clean/reference columns.
    """
    return [
        col
        for col in df.columns
        if col.startswith("vlp_led") and col.endswith("_intensity") and "clean" not in col
    ]


def signal_columns(df: pd.DataFrame) -> List[str]:
    """
    Return all measured signal columns to be filtered.
    """
    return measured_wifi_columns(df) + measured_vlp_columns(df)


def moving_average_filter(values: np.ndarray, window: int) -> np.ndarray:
    """
    Causal moving-average filter.

    Each output uses the current and previous samples only:
        y[t] = average(x[max(0, t-window+1) ... t])
    """
    series = pd.Series(values)
    return series.rolling(window=window, min_periods=1).mean().to_numpy(dtype=float)


def median_filter(values: np.ndarray, window: int) -> np.ndarray:
    """
    Causal median filter.

    Each output uses the current and previous samples only.
    """
    series = pd.Series(values)
    return series.rolling(window=window, min_periods=1).median().to_numpy(dtype=float)


def ema_filter(values: np.ndarray, alpha: float) -> np.ndarray:
    """
    Exponential moving average filter.

    y[t] = alpha * x[t] + (1 - alpha) * y[t-1]
    """
    series = pd.Series(values)
    return series.ewm(alpha=float(alpha), adjust=False).mean().to_numpy(dtype=float)


def apply_filter_to_dataframe(
    df: pd.DataFrame,
    cfg: Mapping,
    filter_name: str,
) -> pd.DataFrame:
    """
    Apply one DSP filter to all measured WiFi and VLP signal columns.

    Clean/reference columns are preserved unchanged.
    Mask columns and true positions are also preserved unchanged.
    """
    if filter_name not in FILTERS:
        raise ValueError(f"Unknown filter_name={filter_name}. Use one of {FILTERS}.")

    filtered = df.copy()
    cols = signal_columns(df)

    ma_window = int(cfg["dsp"]["moving_average_window"])
    med_window = int(cfg["dsp"]["median_window"])
    ema_alpha = float(cfg["dsp"]["ema_alpha"])

    for col in cols:
        values = df[col].to_numpy(dtype=float)

        if filter_name == "moving_average":
            filtered[col] = moving_average_filter(values, window=ma_window)
        elif filter_name == "median":
            filtered[col] = median_filter(values, window=med_window)
        elif filter_name == "ema":
            filtered[col] = ema_filter(values, alpha=ema_alpha)

    filtered["filter_name"] = filter_name
    return filtered


def load_signal_file(seed: int, scenario: str) -> pd.DataFrame:
    """
    Load raw signal CSV for one scenario.
    """
    path = Path(f"results/raw/signals_seed{seed}_{scenario}.csv")

    if not path.exists():
        raise FileNotFoundError(
            f"Missing signal file: {path}. "
            f"Run: python -m src.signal_models --config configs/default.yaml --seed {seed}"
        )

    return pd.read_csv(path)


def variance_reduction_rows(
    raw_df: pd.DataFrame,
    filtered_df: pd.DataFrame,
    scenario: str,
    filter_name: str,
) -> List[Dict[str, object]]:
    """
    Compute simple signal-variance reduction summaries.

    This is not the final localization metric. It is an RQ1 signal-level sanity
    table showing how much each filter smooths WiFi and VLP streams.
    """
    rows: List[Dict[str, object]] = []

    groups = {
        "wifi": measured_wifi_columns(raw_df),
        "vlp": measured_vlp_columns(raw_df),
    }

    for group_name, cols in groups.items():
        raw_std = raw_df[cols].std().mean()
        filtered_std = filtered_df[cols].std().mean()

        if raw_std <= 1e-12:
            reduction_percent = 0.0
        else:
            reduction_percent = 100.0 * (raw_std - filtered_std) / raw_std

        rows.append(
            {
                "scenario": scenario,
                "filter_name": filter_name,
                "signal_group": group_name,
                "raw_mean_std": float(raw_std),
                "filtered_mean_std": float(filtered_std),
                "std_reduction_percent": float(reduction_percent),
            }
        )

    return rows


def build_filtered_signal_outputs(
    config_path: str | Path = "configs/default.yaml",
    seed: int = 101,
) -> Dict[str, str]:
    """
    Apply all DSP filters to all scenario signal files.

    Saves:
    - results/processed/filtered_signals_seed101_<scenario>_<filter>.csv
    - results/tables/table_filter_signal_variance_seed101.csv
    - results/figures/fig3_noisy_vs_filtered_signals.png
    - results/logs/dsp_filter_summary_seed101.json
    """
    cfg = load_config(config_path)

    outputs: Dict[str, str] = {}
    variance_rows: List[Dict[str, object]] = []

    # Keep filtered tables in memory for plotting.
    filtered_tables: Dict[str, Dict[str, pd.DataFrame]] = {}
    raw_tables: Dict[str, pd.DataFrame] = {}

    for scenario in SCENARIOS:
        raw_df = load_signal_file(seed=seed, scenario=scenario)
        raw_tables[scenario] = raw_df
        filtered_tables[scenario] = {}

        for filter_name in FILTERS:
            filtered_df = apply_filter_to_dataframe(
                df=raw_df,
                cfg=cfg,
                filter_name=filter_name,
            )

            out_csv = f"results/processed/filtered_signals_seed{seed}_{scenario}_{filter_name}.csv"
            save_csv(filtered_df, out_csv)

            outputs[f"filtered_{scenario}_{filter_name}"] = out_csv
            filtered_tables[scenario][filter_name] = filtered_df

            variance_rows.extend(
                variance_reduction_rows(
                    raw_df=raw_df,
                    filtered_df=filtered_df,
                    scenario=scenario,
                    filter_name=filter_name,
                )
            )

    variance_table = pd.DataFrame(variance_rows)
    variance_path = f"results/tables/table_filter_signal_variance_seed{seed}.csv"
    save_csv(variance_table, variance_path)
    outputs["filter_signal_variance_table"] = variance_path

    fig_path = plot_filter_sanity_figure(
        raw_tables=raw_tables,
        filtered_tables=filtered_tables,
        seed=seed,
        output_path="results/figures/fig3_noisy_vs_filtered_signals.png",
    )
    outputs["filter_sanity_figure"] = str(fig_path)

    summary = {
        "seed": seed,
        "filters": FILTERS,
        "scenarios": SCENARIOS,
        "dsp_config": cfg["dsp"],
        "outputs": outputs,
    }

    summary_path = f"results/logs/dsp_filter_summary_seed{seed}.json"
    save_json(summary, summary_path)
    outputs["dsp_filter_summary"] = summary_path

    return outputs


def plot_filter_sanity_figure(
    raw_tables: Mapping[str, pd.DataFrame],
    filtered_tables: Mapping[str, Mapping[str, pd.DataFrame]],
    seed: int,
    output_path: str | Path,
) -> Path:
    """
    Create Fig. 3 draft: noisy vs filtered signal examples.

    Top panel:
        WiFi AP1 under S2 WiFi-degraded scenario.

    Bottom panel:
        VLP LED1 under S3 VLP-blocked scenario.

    This figure supports RQ1. It is still a draft and can be improved later.
    """
    output_path = Path(output_path)
    ensure_dir(output_path.parent)

    fig, axes = plt.subplots(2, 1, figsize=(9.0, 6.2), sharex=False)

    # WiFi example: S2.
    wifi_scenario = "s2_wifi_degraded"
    wifi_col = "wifi_ap1_dbm"
    raw_wifi = raw_tables[wifi_scenario]

    axes[0].plot(
        raw_wifi["t"],
        raw_wifi[wifi_col],
        linewidth=1.1,
        label="raw",
    )

    for filter_name in FILTERS:
        df = filtered_tables[wifi_scenario][filter_name]
        axes[0].plot(
            df["t"],
            df[wifi_col],
            linewidth=1.2,
            label=filter_name,
        )

    axes[0].set_title("WiFi RSSI Example: Raw vs DSP-Filtered Signal")
    axes[0].set_xlabel("Time step")
    axes[0].set_ylabel("AP1 RSSI (dBm)")
    axes[0].grid(True, alpha=0.3)
    axes[0].legend(fontsize=8)

    # VLP example: S3.
    vlp_scenario = "s3_vlp_blocked"
    vlp_col = "vlp_led1_intensity"
    raw_vlp = raw_tables[vlp_scenario]

    axes[1].plot(
        raw_vlp["t"],
        raw_vlp[vlp_col],
        linewidth=1.1,
        label="raw",
    )

    for filter_name in FILTERS:
        df = filtered_tables[vlp_scenario][filter_name]
        axes[1].plot(
            df["t"],
            df[vlp_col],
            linewidth=1.2,
            label=filter_name,
        )

    axes[1].set_title("Visible-Light Intensity Example: Raw vs DSP-Filtered Signal")
    axes[1].set_xlabel("Time step")
    axes[1].set_ylabel("LED1 intensity")
    axes[1].grid(True, alpha=0.3)
    axes[1].legend(fontsize=8)

    fig.suptitle(f"DSP Filtering Sanity Check, Seed {seed}", fontsize=12)
    fig.tight_layout()
    fig.savefig(output_path, dpi=300)
    plt.close(fig)

    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apply DSP filters to WiFi and VLP signal streams."
    )
    parser.add_argument(
        "--config",
        type=str,
        default="configs/default.yaml",
        help="Path to YAML config file.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=101,
        help="Seed matching generated signal files.",
    )

    args = parser.parse_args()

    outputs = build_filtered_signal_outputs(
        config_path=args.config,
        seed=args.seed,
    )

    print("DSP FILTER TEST OK")
    for name, path in outputs.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
