"""
Full-trajectory GSP localization evaluation for the SPICSCON 2026 project.

This module evaluates graph-smoothed location probability maps over full
trajectories, not only one heatmap sample.

Compared methods:
- static_raw
- graph_diffusion_1
- graph_diffusion_3
- laplacian

The purpose is to evaluate RQ2:
Does topology-aware graph smoothing improve probability stability, trajectory
smoothness, failure rate, or localization error under simulated degradation?
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Dict, List, Mapping, Tuple

import networkx as nx
import numpy as np
import pandas as pd
from scipy import sparse

from src.baselines import SCENARIOS
from src.environment import create_grid_spec, make_grid_graph
from src.gsp_smoothing import (
    build_adjacency_matrix,
    graph_diffusion_smooth,
    graph_laplacian,
    laplacian_smooth,
    row_normalized_adjacency,
)
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


GSP_METHODS = [
    "static_raw",
    "graph_diffusion_1",
    "graph_diffusion_3",
    "laplacian",
]


def load_signal_file(seed: int, scenario: str) -> pd.DataFrame:
    """
    Load raw signal file for one scenario.
    """
    path = Path(f"results/raw/signals_seed{seed}_{scenario}.csv")

    if not path.exists():
        raise FileNotFoundError(
            f"Missing signal file: {path}. "
            f"Run: python -m src.signal_models --config configs/default.yaml --seed {seed}"
        )

    return pd.read_csv(path)


def prepare_graph_operators(cfg: Mapping, num_cells: int) -> Dict[str, object]:
    """
    Build graph operators used by all GSP methods.
    """
    grid = create_grid_spec(cfg)
    graph = make_grid_graph(grid, neighbor_type=int(cfg["gsp"]["neighbor_type"]))

    adj = build_adjacency_matrix(graph, num_nodes=num_cells)
    adj_norm = row_normalized_adjacency(adj)
    lap = graph_laplacian(adj, normalized=False)

    lambda_values = cfg["gsp"].get("lambda_values", [0.1])
    lambda_value = float(lambda_values[1] if len(lambda_values) > 1 else lambda_values[0])

    return {
        "graph": graph,
        "adj": adj,
        "adj_norm": adj_norm,
        "laplacian": lap,
        "alpha": float(cfg["gsp"]["smoothing_alpha"]),
        "lambda_value": lambda_value,
    }


def probability_maps_for_row(
    cfg: Mapping,
    cells: pd.DataFrame,
    row: pd.Series,
    graph_ops: Mapping[str, object],
    wifi_weight: float,
) -> Dict[str, np.ndarray]:
    """
    Create raw and graph-smoothed probability maps for one time step.
    """
    p_wifi = wifi_probability_map(cfg=cfg, cells=cells, row=row)
    p_vlp = vlp_probability_map(cfg=cfg, cells=cells, row=row)

    p_static = fuse_probability_maps(
        p_wifi=p_wifi,
        p_vlp=p_vlp,
        wifi_weight=wifi_weight,
    )

    p_diffusion_1 = graph_diffusion_smooth(
        p_static,
        adj_norm=graph_ops["adj_norm"],
        alpha=float(graph_ops["alpha"]),
        iterations=1,
    )

    p_diffusion_3 = graph_diffusion_smooth(
        p_static,
        adj_norm=graph_ops["adj_norm"],
        alpha=float(graph_ops["alpha"]),
        iterations=3,
    )

    p_laplacian = laplacian_smooth(
        p_static,
        laplacian=graph_ops["laplacian"],
        lambda_value=float(graph_ops["lambda_value"]),
    )

    return {
        "static_raw": p_static,
        "graph_diffusion_1": p_diffusion_1,
        "graph_diffusion_3": p_diffusion_3,
        "laplacian": p_laplacian,
    }


def run_gsp_for_signal_df(
    cfg: Mapping,
    cells: pd.DataFrame,
    signal_df: pd.DataFrame,
    wifi_weight: float = 0.5,
    estimate_method: str = "argmax",
) -> Tuple[pd.DataFrame, Dict[str, float]]:
    """
    Run GSP methods over a full signal trajectory.
    """
    graph_ops = prepare_graph_operators(cfg, num_cells=len(cells))

    rows: List[Dict[str, object]] = []
    runtime_accumulator = {method: 0.0 for method in GSP_METHODS}

    for _, row in signal_df.iterrows():
        t = int(row["t"])

        start_all = time.perf_counter()
        prob_maps = probability_maps_for_row(
            cfg=cfg,
            cells=cells,
            row=row,
            graph_ops=graph_ops,
            wifi_weight=wifi_weight,
        )
        total_prob_time = time.perf_counter() - start_all

        common = {
            "t": t,
            "scenario": row["scenario"],
            "true_x": float(row["true_x"]),
            "true_y": float(row["true_y"]),
            "wifi_degraded": bool(row["wifi_degraded"]),
            "vlp_blocked": bool(row["vlp_blocked"]),
            "mixed_dynamic": bool(row["mixed_dynamic"]),
        }

        for method, prob in prob_maps.items():
            start = time.perf_counter()
            est = estimate_position(prob, cells, method=estimate_method)
            runtime_accumulator[method] += time.perf_counter() - start

            # Add a shared probability-map construction cost to static_raw.
            # For smoothed methods, probability map construction is also required,
            # but the exact decomposition is less important than reproducible timing.
            if method == "static_raw":
                runtime_accumulator[method] += total_prob_time

            rows.append(
                {
                    **common,
                    "gsp_method": method,
                    "pred_cell_id": int(est["cell_id"]),
                    "pred_x": float(est["x"]),
                    "pred_y": float(est["y"]),
                    "max_prob": float(est["max_prob"]),
                }
            )

    predictions = pd.DataFrame(rows)
    num_steps = len(signal_df)

    runtime_by_method = {
        method: runtime_accumulator[method] / max(num_steps, 1)
        for method in GSP_METHODS
    }

    return predictions, runtime_by_method


def summarize_gsp_predictions(
    predictions: pd.DataFrame,
    cfg: Mapping,
) -> pd.DataFrame:
    """
    Compute metrics for each GSP method in one scenario.
    """
    metric_rows = []

    zone_radius_m = float(cfg["metrics"]["zone_radius_m"])
    failure_threshold_m = float(cfg["metrics"]["failure_threshold_m"])

    scenario = str(predictions["scenario"].iloc[0])

    for method in GSP_METHODS:
        method_df = predictions[predictions["gsp_method"] == method].copy()

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
                "gsp_method": method,
                **metrics,
                "wifi_event_recovery_steps": wifi_recovery,
                "vlp_event_recovery_steps": vlp_recovery,
            }
        )

    return pd.DataFrame(metric_rows)


def build_gsp_evaluation_outputs(
    config_path: str | Path = "configs/default.yaml",
    seed: int = 101,
    wifi_weight: float = 0.5,
    estimate_method: str = "argmax",
) -> Dict[str, str]:
    """
    Run full-trajectory GSP evaluation across all scenarios.
    """
    cfg = load_config(config_path)
    cells = load_grid_cells("results/raw/grid_cells.csv")

    all_predictions = []
    all_metrics = []
    runtime_rows = []

    outputs: Dict[str, str] = {}

    for scenario in SCENARIOS:
        signal_df = load_signal_file(seed=seed, scenario=scenario)

        predictions, runtime_by_method = run_gsp_for_signal_df(
            cfg=cfg,
            cells=cells,
            signal_df=signal_df,
            wifi_weight=wifi_weight,
            estimate_method=estimate_method,
        )

        all_predictions.append(predictions)

        metrics_df = summarize_gsp_predictions(predictions, cfg=cfg)
        all_metrics.append(metrics_df)

        for method, runtime_s in runtime_by_method.items():
            runtime_rows.append(
                {
                    "seed": seed,
                    "scenario": scenario,
                    "gsp_method": method,
                    "mean_runtime_s_per_step": runtime_s,
                    "mean_runtime_ms_per_step": runtime_s * 1000.0,
                }
            )

    predictions_all = pd.concat(all_predictions, ignore_index=True)
    metrics_all = pd.concat(all_metrics, ignore_index=True)
    runtime_df = pd.DataFrame(runtime_rows)

    predictions_path = f"results/processed/gsp_predictions_seed{seed}.csv"
    metrics_path = f"results/tables/table_gsp_metrics_seed{seed}.csv"
    runtime_path = f"results/tables/table_gsp_runtime_seed{seed}.csv"

    save_csv(predictions_all, predictions_path)
    save_csv(metrics_all, metrics_path)
    save_csv(runtime_df, runtime_path)

    outputs["gsp_predictions"] = predictions_path
    outputs["gsp_metrics_table"] = metrics_path
    outputs["gsp_runtime_table"] = runtime_path

    summary = {
        "seed": seed,
        "scenarios": SCENARIOS,
        "gsp_methods": GSP_METHODS,
        "wifi_weight": float(wifi_weight),
        "estimate_method": estimate_method,
        "gsp_config": {
            "neighbor_type": int(cfg["gsp"]["neighbor_type"]),
            "smoothing_alpha": float(cfg["gsp"]["smoothing_alpha"]),
            "lambda_values": cfg["gsp"]["lambda_values"],
        },
        "outputs": outputs,
    }

    summary_path = f"results/logs/gsp_evaluation_summary_seed{seed}.json"
    save_json(summary, summary_path)
    outputs["gsp_evaluation_summary"] = summary_path

    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate GSP smoothing over full trajectories."
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
        help="WiFi weight for static fusion before graph smoothing.",
    )
    parser.add_argument(
        "--estimate-method",
        type=str,
        default="argmax",
        choices=["argmax", "expected"],
        help="How to estimate position from probability maps.",
    )

    args = parser.parse_args()

    outputs = build_gsp_evaluation_outputs(
        config_path=args.config,
        seed=args.seed,
        wifi_weight=args.wifi_weight,
        estimate_method=args.estimate_method,
    )

    print("GSP EVALUATION TEST OK")
    for name, path in outputs.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
