"""
Baseline localization methods for the SPICSCON 2026 indoor positioning project.

This module evaluates three first-stage baselines over full trajectories:

1. WiFi-only localization
2. VLP-only localization
3. Static WiFi-VLP fusion

These baselines are required before DSP, GSP, or adaptive fusion. They create
the first real localization error tables for the paper.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Dict, List, Mapping, Tuple

import numpy as np
import pandas as pd

from src.metrics import (
    euclidean_errors,
    metrics_from_prediction_frame,
    recovery_time_after_events,
)
from src.probability_maps import (
    estimate_position,
    fuse_probability_maps,
    load_grid_cells,
    vlp_probability_map,
    wifi_probability_map,
)
from src.utils import load_config, save_csv, save_json


SCENARIOS = [
    "s1_clean",
    "s2_wifi_degraded",
    "s3_vlp_blocked",
    "s4_mixed_dynamic",
]


BASELINE_METHODS = [
    "wifi_only",
    "vlp_only",
    "static_fusion",
]


def load_signal_file(seed: int, scenario: str) -> pd.DataFrame:
    """
    Load a generated signal CSV for one seed and scenario.
    """
    path = Path(f"results/raw/signals_seed{seed}_{scenario}.csv")

    if not path.exists():
        raise FileNotFoundError(
            f"Missing signal file: {path}. "
            f"Run: python -m src.signal_models --config configs/default.yaml --seed {seed}"
        )

    return pd.read_csv(path)


def run_baselines_for_signal_df(
    cfg: Mapping,
    cells: pd.DataFrame,
    signal_df: pd.DataFrame,
    wifi_weight: float = 0.5,
    estimate_method: str = "argmax",
) -> Tuple[pd.DataFrame, Dict[str, float]]:
    """
    Run WiFi-only, VLP-only, and static-fusion baselines for a full trajectory.

    Parameters
    ----------
    cfg:
        Configuration dictionary.
    cells:
        Grid-cell table.
    signal_df:
        Signal DataFrame for one scenario.
    wifi_weight:
        WiFi weight for static fusion.
    estimate_method:
        'argmax' or 'expected' position estimate from probability map.

    Returns
    -------
    tuple
        predictions_df, runtime_by_method
    """
    rows: List[Dict[str, object]] = []
    runtime_accumulator = {method: 0.0 for method in BASELINE_METHODS}

    for _, row in signal_df.iterrows():
        t = int(row["t"])

        # Build modality probability maps once per time step.
        start = time.perf_counter()
        p_wifi = wifi_probability_map(cfg=cfg, cells=cells, row=row)
        wifi_est = estimate_position(p_wifi, cells, method=estimate_method)
        runtime_accumulator["wifi_only"] += time.perf_counter() - start

        start = time.perf_counter()
        p_vlp = vlp_probability_map(cfg=cfg, cells=cells, row=row)
        vlp_est = estimate_position(p_vlp, cells, method=estimate_method)
        runtime_accumulator["vlp_only"] += time.perf_counter() - start

        start = time.perf_counter()
        p_static = fuse_probability_maps(
            p_wifi=p_wifi,
            p_vlp=p_vlp,
            wifi_weight=wifi_weight,
        )
        static_est = estimate_position(p_static, cells, method=estimate_method)
        runtime_accumulator["static_fusion"] += time.perf_counter() - start

        common = {
            "t": t,
            "scenario": row["scenario"],
            "true_x": float(row["true_x"]),
            "true_y": float(row["true_y"]),
            "wifi_degraded": bool(row["wifi_degraded"]),
            "vlp_blocked": bool(row["vlp_blocked"]),
            "mixed_dynamic": bool(row["mixed_dynamic"]),
        }

        rows.append(
            {
                **common,
                "method": "wifi_only",
                "pred_cell_id": int(wifi_est["cell_id"]),
                "pred_x": float(wifi_est["x"]),
                "pred_y": float(wifi_est["y"]),
                "max_prob": float(wifi_est["max_prob"]),
            }
        )

        rows.append(
            {
                **common,
                "method": "vlp_only",
                "pred_cell_id": int(vlp_est["cell_id"]),
                "pred_x": float(vlp_est["x"]),
                "pred_y": float(vlp_est["y"]),
                "max_prob": float(vlp_est["max_prob"]),
            }
        )

        rows.append(
            {
                **common,
                "method": "static_fusion",
                "pred_cell_id": int(static_est["cell_id"]),
                "pred_x": float(static_est["x"]),
                "pred_y": float(static_est["y"]),
                "max_prob": float(static_est["max_prob"]),
            }
        )

    predictions = pd.DataFrame(rows)
    num_steps = len(signal_df)

    runtime_by_method = {
        method: runtime_accumulator[method] / max(num_steps, 1)
        for method in BASELINE_METHODS
    }

    return predictions, runtime_by_method


def summarize_baseline_predictions(
    predictions: pd.DataFrame,
    cfg: Mapping,
) -> pd.DataFrame:
    """
    Compute metric summary for each method in one scenario.
    """
    metric_rows = []

    zone_radius_m = float(cfg["metrics"]["zone_radius_m"])
    failure_threshold_m = float(cfg["metrics"]["failure_threshold_m"])

    scenario = str(predictions["scenario"].iloc[0])

    for method in BASELINE_METHODS:
        method_df = predictions[predictions["method"] == method].copy()

        metrics = metrics_from_prediction_frame(
            method_df,
            true_x_col="true_x",
            true_y_col="true_y",
            pred_x_col="pred_x",
            pred_y_col="pred_y",
            zone_radius_m=zone_radius_m,
            failure_threshold_m=failure_threshold_m,
        )

        true_xy = method_df[["true_x", "true_y"]].to_numpy(dtype=float)
        pred_xy = method_df[["pred_x", "pred_y"]].to_numpy(dtype=float)
        errors = euclidean_errors(true_xy, pred_xy)

        wifi_recovery = recovery_time_after_events(
            errors=errors,
            event_mask=method_df["wifi_degraded"].to_numpy(dtype=bool),
            failure_threshold_m=failure_threshold_m,
            trigger="start",
        )

        vlp_recovery = recovery_time_after_events(
            errors=errors,
            event_mask=method_df["vlp_blocked"].to_numpy(dtype=bool),
            failure_threshold_m=failure_threshold_m,
            trigger="start",
        )

        metric_rows.append(
            {
                "scenario": scenario,
                "method": method,
                **metrics,
                "wifi_event_recovery_steps": wifi_recovery,
                "vlp_event_recovery_steps": vlp_recovery,
            }
        )

    return pd.DataFrame(metric_rows)


def build_baseline_outputs(
    config_path: str | Path = "configs/default.yaml",
    seed: int = 101,
    wifi_weight: float = 0.5,
    estimate_method: str = "argmax",
) -> Dict[str, str]:
    """
    Run all first-stage baselines over all scenarios for one seed.

    Saves:
    - per-scenario prediction CSV files
    - baseline metrics table
    - runtime table
    - baseline summary JSON
    """
    cfg = load_config(config_path)
    cells = load_grid_cells("results/raw/grid_cells.csv")

    all_metric_tables = []
    runtime_rows = []
    outputs: Dict[str, str] = {}

    for scenario in SCENARIOS:
        signal_df = load_signal_file(seed=seed, scenario=scenario)

        predictions, runtime_by_method = run_baselines_for_signal_df(
            cfg=cfg,
            cells=cells,
            signal_df=signal_df,
            wifi_weight=wifi_weight,
            estimate_method=estimate_method,
        )

        pred_path = f"results/processed/baseline_predictions_seed{seed}_{scenario}.csv"
        save_csv(predictions, pred_path)
        outputs[f"predictions_{scenario}"] = pred_path

        metric_table = summarize_baseline_predictions(predictions, cfg=cfg)
        all_metric_tables.append(metric_table)

        for method, runtime_s in runtime_by_method.items():
            runtime_rows.append(
                {
                    "seed": seed,
                    "scenario": scenario,
                    "method": method,
                    "mean_runtime_s_per_step": runtime_s,
                    "mean_runtime_ms_per_step": runtime_s * 1000.0,
                }
            )

    metrics_df = pd.concat(all_metric_tables, ignore_index=True)

    metrics_path = f"results/tables/table_baseline_metrics_seed{seed}.csv"
    runtime_path = f"results/tables/table_baseline_runtime_seed{seed}.csv"

    save_csv(metrics_df, metrics_path)
    save_csv(pd.DataFrame(runtime_rows), runtime_path)

    outputs["baseline_metrics_table"] = metrics_path
    outputs["baseline_runtime_table"] = runtime_path

    summary = {
        "seed": seed,
        "scenarios": SCENARIOS,
        "methods": BASELINE_METHODS,
        "wifi_weight_for_static_fusion": wifi_weight,
        "estimate_method": estimate_method,
        "outputs": outputs,
    }

    summary_path = f"results/logs/baseline_summary_seed{seed}.json"
    save_json(summary, summary_path)
    outputs["baseline_summary"] = summary_path

    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run WiFi-only, VLP-only, and static-fusion baselines."
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
        help="How to estimate position from a probability map.",
    )

    args = parser.parse_args()

    outputs = build_baseline_outputs(
        config_path=args.config,
        seed=args.seed,
        wifi_weight=args.wifi_weight,
        estimate_method=args.estimate_method,
    )

    print("BASELINE TEST OK")
    for name, path in outputs.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
