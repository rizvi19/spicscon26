"""
DSP localization evaluation for the SPICSCON 2026 indoor positioning project.

This module evaluates whether DSP-filtered signals improve localization metrics.

It compares signal variants:
- raw
- moving_average
- median
- ema

For each variant, it runs:
- WiFi-only localization
- VLP-only localization
- static WiFi-VLP fusion

Across scenarios:
- S1 clean
- S2 WiFi degraded
- S3 VLP blocked
- S4 mixed dynamic

This supports RQ1:
To what extent do simple DSP filters improve localization robustness for
simulated WiFi RSSI-like and visible-light intensity-like signals?
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Mapping

import pandas as pd

from src.baselines import (
    BASELINE_METHODS,
    SCENARIOS,
    run_baselines_for_signal_df,
    summarize_baseline_predictions,
)
from src.dsp_filters import FILTERS
from src.probability_maps import load_grid_cells
from src.utils import load_config, save_csv, save_json


SIGNAL_VARIANTS = ["raw"] + FILTERS


def load_signal_variant(seed: int, scenario: str, variant: str) -> pd.DataFrame:
    """
    Load raw or DSP-filtered signal file.

    Parameters
    ----------
    seed:
        Experiment seed.
    scenario:
        Scenario name.
    variant:
        raw, moving_average, median, or ema.

    Returns
    -------
    pandas.DataFrame
        Signal table.
    """
    if variant == "raw":
        path = Path(f"results/raw/signals_seed{seed}_{scenario}.csv")
    else:
        path = Path(f"results/processed/filtered_signals_seed{seed}_{scenario}_{variant}.csv")

    if not path.exists():
        raise FileNotFoundError(
            f"Missing signal variant file: {path}. "
            "Run signal_models.py and dsp_filters.py first."
        )

    return pd.read_csv(path)


def build_dsp_localization_outputs(
    config_path: str | Path = "configs/default.yaml",
    seed: int = 101,
    wifi_weight: float = 0.5,
    estimate_method: str = "argmax",
) -> Dict[str, str]:
    """
    Run localization baselines on raw and DSP-filtered signals.

    Saves:
    - results/processed/dsp_localization_predictions_seed101.csv
    - results/tables/table_dsp_localization_metrics_seed101.csv
    - results/logs/dsp_localization_summary_seed101.json
    """
    cfg = load_config(config_path)
    cells = load_grid_cells("results/raw/grid_cells.csv")

    all_predictions: List[pd.DataFrame] = []
    all_metrics: List[pd.DataFrame] = []
    outputs: Dict[str, str] = {}

    for scenario in SCENARIOS:
        for variant in SIGNAL_VARIANTS:
            signal_df = load_signal_variant(
                seed=seed,
                scenario=scenario,
                variant=variant,
            )

            predictions, _runtime_by_method = run_baselines_for_signal_df(
                cfg=cfg,
                cells=cells,
                signal_df=signal_df,
                wifi_weight=wifi_weight,
                estimate_method=estimate_method,
            )

            predictions["signal_variant"] = variant
            all_predictions.append(predictions)

            metrics_df = summarize_baseline_predictions(predictions, cfg=cfg)
            metrics_df["signal_variant"] = variant

            all_metrics.append(metrics_df)

    predictions_all = pd.concat(all_predictions, ignore_index=True)
    metrics_all = pd.concat(all_metrics, ignore_index=True)

    # Reorder columns for readability.
    metric_cols = [
        "scenario",
        "signal_variant",
        "method",
        "mean_error_m",
        "median_error_m",
        "p90_error_m",
        "zone_accuracy",
        "failure_rate",
        "trajectory_smoothness_m_per_step",
        "wifi_event_recovery_steps",
        "vlp_event_recovery_steps",
    ]
    metrics_all = metrics_all[metric_cols]

    pred_path = f"results/processed/dsp_localization_predictions_seed{seed}.csv"
    metrics_path = f"results/tables/table_dsp_localization_metrics_seed{seed}.csv"

    save_csv(predictions_all, pred_path)
    save_csv(metrics_all, metrics_path)

    outputs["dsp_localization_predictions"] = pred_path
    outputs["dsp_localization_metrics_table"] = metrics_path

    summary = {
        "seed": seed,
        "scenarios": SCENARIOS,
        "signal_variants": SIGNAL_VARIANTS,
        "methods": BASELINE_METHODS,
        "wifi_weight_for_static_fusion": wifi_weight,
        "estimate_method": estimate_method,
        "outputs": outputs,
    }

    summary_path = f"results/logs/dsp_localization_summary_seed{seed}.json"
    save_json(summary, summary_path)
    outputs["dsp_localization_summary"] = summary_path

    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate localization using raw and DSP-filtered signals."
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
    parser.add_argument(
        "--wifi-weight",
        type=float,
        default=0.5,
        help="WiFi weight for static fusion.",
    )
    parser.add_argument(
        "--estimate-method",
        type=str,
        default="argmax",
        choices=["argmax", "expected"],
        help="How to estimate position from probability maps.",
    )

    args = parser.parse_args()

    outputs = build_dsp_localization_outputs(
        config_path=args.config,
        seed=args.seed,
        wifi_weight=args.wifi_weight,
        estimate_method=args.estimate_method,
    )

    print("DSP LOCALIZATION TEST OK")
    for name, path in outputs.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
