"""
Adaptive reliability-based fusion for the SPICSCON 2026 indoor positioning project.

This module implements a lightweight adaptive fusion layer.

Important claim boundary:
- This is not a new RL algorithm.
- This is not end-to-end learned localization.
- It is a transparent reliability-based adaptive fusion policy using predefined actions.

The method combines:
1. raw WiFi/VLP probability maps
2. DSP-filtered signal maps when degradation is detected
3. graph-smoothed static probability maps
4. simple reliability scores based on entropy and peak probability

Actions:
- wifi_heavy
- vlp_heavy
- balanced
- graph_prior_heavy
- recovery
"""

from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path
from typing import Dict, List, Mapping, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.baselines import SCENARIOS
from src.environment import create_grid_spec, make_grid_graph
from src.gsp_smoothing import (
    build_adjacency_matrix,
    graph_diffusion_smooth,
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
    normalize_prob,
    vlp_probability_map,
    wifi_probability_map,
)
from src.utils import ensure_dir, load_config, save_csv, save_json


ACTIONS = [
    "wifi_heavy",
    "vlp_heavy",
    "balanced",
    "graph_prior_heavy",
    "recovery",
]


def load_raw_signal(seed: int, scenario: str) -> pd.DataFrame:
    """
    Load raw signal file.
    """
    path = Path(f"results/raw/signals_seed{seed}_{scenario}.csv")
    if not path.exists():
        raise FileNotFoundError(f"Missing raw signal file: {path}")
    return pd.read_csv(path)


def load_filtered_signal(seed: int, scenario: str, filter_name: str) -> pd.DataFrame:
    """
    Load DSP-filtered signal file.
    """
    path = Path(f"results/processed/filtered_signals_seed{seed}_{scenario}_{filter_name}.csv")
    if not path.exists():
        raise FileNotFoundError(
            f"Missing filtered signal file: {path}. "
            "Run: python -m src.dsp_filters --config configs/default.yaml --seed 101"
        )
    return pd.read_csv(path)


def entropy(prob: np.ndarray) -> float:
    """
    Shannon entropy of probability vector.
    """
    p = normalize_prob(prob)
    return float(-np.sum(p * np.log(p + 1e-12)))


def normalized_entropy(prob: np.ndarray) -> float:
    """
    Entropy normalized to [0, 1] approximately.
    """
    p = normalize_prob(prob)
    max_entropy = math.log(len(p))
    if max_entropy <= 0:
        return 0.0
    return float(entropy(p) / max_entropy)


def peak_probability(prob: np.ndarray) -> float:
    """
    Maximum probability value.
    """
    return float(np.max(normalize_prob(prob)))


def reliability_score(
    prob: np.ndarray,
    is_degraded: bool,
    degradation_penalty: float,
) -> float:
    """
    Compute a simple probability-map reliability score.

    High reliability:
    - high peak probability
    - low entropy
    - no known degradation flag

    Low reliability:
    - broad/uncertain probability map
    - degradation flag active
    """
    peak = peak_probability(prob)
    ent = normalized_entropy(prob)

    score = peak * (1.0 - ent)

    if is_degraded:
        score *= float(degradation_penalty)

    return float(max(score, 1e-9))


def choose_action(
    wifi_reliability: float,
    vlp_reliability: float,
    wifi_degraded: bool,
    vlp_blocked: bool,
    mixed_dynamic: bool,
) -> str:
    """
    Choose one of the predefined adaptive fusion actions.

    This is a transparent heuristic policy, not learned RL.
    """
    total_reliability = wifi_reliability + vlp_reliability

    # If both signals are unreliable or mixed conditions are active, use graph-prior/recovery.
    if total_reliability < 0.01:
        return "recovery"

    if wifi_degraded and vlp_blocked:
        return "graph_prior_heavy"

    if wifi_degraded and not vlp_blocked:
        return "vlp_heavy"

    if vlp_blocked and not wifi_degraded:
        # Do not blindly trust WiFi; choose based on reliability.
        if wifi_reliability > vlp_reliability * 1.15:
            return "wifi_heavy"
        return "graph_prior_heavy"

    if mixed_dynamic:
        if max(wifi_reliability, vlp_reliability) < 0.03:
            return "graph_prior_heavy"

    ratio = wifi_reliability / max(vlp_reliability, 1e-9)

    if ratio > 1.35:
        return "wifi_heavy"

    if ratio < 0.75:
        return "vlp_heavy"

    return "balanced"


def action_weights(action: str) -> Dict[str, float]:
    """
    Return fusion weights for WiFi, VLP, and graph-smoothed prior.
    """
    if action == "wifi_heavy":
        return {"wifi": 0.70, "vlp": 0.20, "graph": 0.10}

    if action == "vlp_heavy":
        return {"wifi": 0.15, "vlp": 0.75, "graph": 0.10}

    if action == "balanced":
        return {"wifi": 0.45, "vlp": 0.45, "graph": 0.10}

    if action == "graph_prior_heavy":
        return {"wifi": 0.20, "vlp": 0.20, "graph": 0.60}

    if action == "recovery":
        return {"wifi": 0.15, "vlp": 0.15, "graph": 0.70}

    raise ValueError(f"Unknown action: {action}")


def prepare_graph_prior_operator(cfg: Mapping, num_cells: int):
    """
    Prepare row-normalized adjacency for graph diffusion.
    """
    grid = create_grid_spec(cfg)
    graph = make_grid_graph(grid, neighbor_type=int(cfg["gsp"]["neighbor_type"]))
    adj = build_adjacency_matrix(graph, num_nodes=num_cells)
    return row_normalized_adjacency(adj)


def adaptive_probability_for_step(
    cfg: Mapping,
    cells: pd.DataFrame,
    raw_row: pd.Series,
    ma_row: pd.Series,
    median_row: pd.Series,
    ema_row: pd.Series,
    adj_norm,
) -> Tuple[np.ndarray, Dict[str, object]]:
    """
    Build adaptive fused probability for one time step.

    DSP-aware map selection:
    - WiFi degraded: use moving-average WiFi map.
    - Otherwise: use raw WiFi map.
    - VLP blocked: use median-filtered VLP map.
    - Otherwise: use raw VLP map.

    Graph prior:
    - diffusion-3 smoothing of a balanced static raw map.
    """
    wifi_degraded = bool(raw_row["wifi_degraded"])
    vlp_blocked = bool(raw_row["vlp_blocked"])
    mixed_dynamic = bool(raw_row["mixed_dynamic"])

    if wifi_degraded:
        wifi_source = "moving_average"
        p_wifi = wifi_probability_map(cfg=cfg, cells=cells, row=ma_row)
    else:
        wifi_source = "raw"
        p_wifi = wifi_probability_map(cfg=cfg, cells=cells, row=raw_row)

    if vlp_blocked:
        vlp_source = "median"
        p_vlp = vlp_probability_map(cfg=cfg, cells=cells, row=median_row)
    else:
        vlp_source = "raw"
        p_vlp = vlp_probability_map(cfg=cfg, cells=cells, row=raw_row)

    p_static_raw = fuse_probability_maps(
        p_wifi=wifi_probability_map(cfg=cfg, cells=cells, row=raw_row),
        p_vlp=vlp_probability_map(cfg=cfg, cells=cells, row=raw_row),
        wifi_weight=0.5,
    )

    p_graph = graph_diffusion_smooth(
        p_static_raw,
        adj_norm=adj_norm,
        alpha=float(cfg["gsp"]["smoothing_alpha"]),
        iterations=3,
    )

    wifi_rel = reliability_score(
        p_wifi,
        is_degraded=wifi_degraded,
        degradation_penalty=0.55,
    )

    vlp_rel = reliability_score(
        p_vlp,
        is_degraded=vlp_blocked,
        degradation_penalty=0.45,
    )

    action = choose_action(
        wifi_reliability=wifi_rel,
        vlp_reliability=vlp_rel,
        wifi_degraded=wifi_degraded,
        vlp_blocked=vlp_blocked,
        mixed_dynamic=mixed_dynamic,
    )

    weights = action_weights(action)

    p_adaptive = (
        weights["wifi"] * normalize_prob(p_wifi)
        + weights["vlp"] * normalize_prob(p_vlp)
        + weights["graph"] * normalize_prob(p_graph)
    )

    p_adaptive = normalize_prob(p_adaptive)

    info = {
        "action": action,
        "wifi_source": wifi_source,
        "vlp_source": vlp_source,
        "wifi_reliability": wifi_rel,
        "vlp_reliability": vlp_rel,
        "p_adaptive_peak": peak_probability(p_adaptive),
        "p_adaptive_entropy": entropy(p_adaptive),
        "weight_wifi": weights["wifi"],
        "weight_vlp": weights["vlp"],
        "weight_graph": weights["graph"],
    }

    return p_adaptive, info


def run_adaptive_for_scenario(
    cfg: Mapping,
    seed: int,
    scenario: str,
    cells: pd.DataFrame,
    estimate_method: str = "argmax",
) -> Tuple[pd.DataFrame, float]:
    """
    Run adaptive fusion over one full scenario trajectory.
    """
    raw_df = load_raw_signal(seed=seed, scenario=scenario)
    ma_df = load_filtered_signal(seed=seed, scenario=scenario, filter_name="moving_average")
    median_df = load_filtered_signal(seed=seed, scenario=scenario, filter_name="median")
    ema_df = load_filtered_signal(seed=seed, scenario=scenario, filter_name="ema")

    adj_norm = prepare_graph_prior_operator(cfg, num_cells=len(cells))

    rows: List[Dict[str, object]] = []
    total_runtime = 0.0

    for idx, raw_row in raw_df.iterrows():
        start = time.perf_counter()

        p_adaptive, info = adaptive_probability_for_step(
            cfg=cfg,
            cells=cells,
            raw_row=raw_row,
            ma_row=ma_df.iloc[idx],
            median_row=median_df.iloc[idx],
            ema_row=ema_df.iloc[idx],
            adj_norm=adj_norm,
        )

        estimate = estimate_position(p_adaptive, cells, method=estimate_method)

        total_runtime += time.perf_counter() - start

        rows.append(
            {
                "t": int(raw_row["t"]),
                "scenario": scenario,
                "true_x": float(raw_row["true_x"]),
                "true_y": float(raw_row["true_y"]),
                "wifi_degraded": bool(raw_row["wifi_degraded"]),
                "vlp_blocked": bool(raw_row["vlp_blocked"]),
                "mixed_dynamic": bool(raw_row["mixed_dynamic"]),
                "method": "adaptive_fusion",
                "pred_cell_id": int(estimate["cell_id"]),
                "pred_x": float(estimate["x"]),
                "pred_y": float(estimate["y"]),
                "max_prob": float(estimate["max_prob"]),
                **info,
            }
        )

    predictions = pd.DataFrame(rows)
    mean_runtime = total_runtime / max(len(raw_df), 1)

    return predictions, mean_runtime


def summarize_adaptive_predictions(
    predictions: pd.DataFrame,
    cfg: Mapping,
    seed: int,
) -> pd.DataFrame:
    """
    Compute adaptive-fusion metrics by scenario.
    """
    zone_radius_m = float(cfg["metrics"]["zone_radius_m"])
    failure_threshold_m = float(cfg["metrics"]["failure_threshold_m"])

    metric_rows: List[Dict[str, object]] = []

    for scenario, scenario_df in predictions.groupby("scenario"):
        metrics = metrics_from_prediction_frame(
            scenario_df,
            true_x_col="true_x",
            true_y_col="true_y",
            pred_x_col="pred_x",
            pred_y_col="pred_y",
            zone_radius_m=zone_radius_m,
            failure_threshold_m=failure_threshold_m,
        )

        true_xy = scenario_df[["true_x", "true_y"]].to_numpy(dtype=float)
        pred_xy = scenario_df[["pred_x", "pred_y"]].to_numpy(dtype=float)
        errors = euclidean_errors(true_xy, pred_xy)

        wifi_recovery = recovery_time_after_events(
            errors=errors,
            event_mask=scenario_df["wifi_degraded"].to_numpy(dtype=bool),
            failure_threshold_m=failure_threshold_m,
            trigger="start",
        )

        vlp_recovery = recovery_time_after_events(
            errors=errors,
            event_mask=scenario_df["vlp_blocked"].to_numpy(dtype=bool),
            failure_threshold_m=failure_threshold_m,
            trigger="start",
        )

        metric_rows.append(
            {
                "seed": seed,
                "scenario": scenario,
                "method": "adaptive_fusion",
                **metrics,
                "wifi_event_recovery_steps": wifi_recovery,
                "vlp_event_recovery_steps": vlp_recovery,
            }
        )

    return pd.DataFrame(metric_rows)


def plot_adaptive_actions(
    predictions: pd.DataFrame,
    output_path: str | Path = "results/figures/fig6_adaptive_actions_seed101.png",
) -> Path:
    """
    Plot adaptive action timeline and localization error for S4 mixed dynamic.
    """
    output_path = Path(output_path)
    ensure_dir(output_path.parent)

    scenario = "s4_mixed_dynamic"
    df = predictions[predictions["scenario"] == scenario].copy()

    if df.empty:
        df = predictions.copy()
        scenario = str(df["scenario"].iloc[0])

    action_to_id = {action: idx for idx, action in enumerate(ACTIONS)}
    df["action_id"] = df["action"].map(action_to_id)

    errors = np.sqrt((df["pred_x"] - df["true_x"]) ** 2 + (df["pred_y"] - df["true_y"]) ** 2)

    fig, axes = plt.subplots(2, 1, figsize=(9.5, 5.8), sharex=True)

    axes[0].step(df["t"], df["action_id"], where="post", linewidth=1.8)
    axes[0].set_yticks(list(action_to_id.values()))
    axes[0].set_yticklabels(list(action_to_id.keys()), fontsize=8)
    axes[0].set_ylabel("Adaptive action")
    axes[0].set_title(f"Adaptive Fusion Action Timeline ({scenario})")
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(df["t"], errors, linewidth=1.6, label="localization error")
    axes[1].fill_between(
        df["t"],
        0,
        errors,
        where=df["wifi_degraded"].to_numpy(dtype=bool),
        alpha=0.15,
        label="WiFi degraded",
    )
    axes[1].fill_between(
        df["t"],
        0,
        errors,
        where=df["vlp_blocked"].to_numpy(dtype=bool),
        alpha=0.15,
        label="VLP blocked",
    )
    axes[1].set_xlabel("Time step")
    axes[1].set_ylabel("Error (m)")
    axes[1].set_title("Adaptive Fusion Localization Error")
    axes[1].grid(True, alpha=0.3)
    axes[1].legend(fontsize=8)

    fig.tight_layout()
    fig.savefig(output_path, dpi=300)
    plt.close(fig)

    return output_path


def build_adaptive_outputs(
    config_path: str | Path = "configs/default.yaml",
    seed: int = 101,
    estimate_method: str = "argmax",
) -> Dict[str, str]:
    """
    Run adaptive fusion for all scenarios and save outputs.
    """
    cfg = load_config(config_path)
    cells = load_grid_cells("results/raw/grid_cells.csv")

    all_predictions = []
    runtime_rows = []

    for scenario in SCENARIOS:
        predictions, mean_runtime = run_adaptive_for_scenario(
            cfg=cfg,
            seed=seed,
            scenario=scenario,
            cells=cells,
            estimate_method=estimate_method,
        )

        all_predictions.append(predictions)

        runtime_rows.append(
            {
                "seed": seed,
                "scenario": scenario,
                "method": "adaptive_fusion",
                "mean_runtime_s_per_step": mean_runtime,
                "mean_runtime_ms_per_step": mean_runtime * 1000.0,
            }
        )

    predictions_all = pd.concat(all_predictions, ignore_index=True)

    metrics_df = summarize_adaptive_predictions(
        predictions=predictions_all,
        cfg=cfg,
        seed=seed,
    )

    action_counts = (
        predictions_all.groupby(["scenario", "action"])
        .size()
        .reset_index(name="count")
        .sort_values(["scenario", "action"])
    )

    pred_path = f"results/processed/adaptive_fusion_predictions_seed{seed}.csv"
    metrics_path = f"results/tables/table_adaptive_fusion_metrics_seed{seed}.csv"
    actions_path = f"results/tables/table_adaptive_action_counts_seed{seed}.csv"
    runtime_path = f"results/tables/table_adaptive_runtime_seed{seed}.csv"

    save_csv(predictions_all, pred_path)
    save_csv(metrics_df, metrics_path)
    save_csv(action_counts, actions_path)
    save_csv(pd.DataFrame(runtime_rows), runtime_path)

    fig_path = plot_adaptive_actions(
        predictions=predictions_all,
        output_path=f"results/figures/fig6_adaptive_actions_seed{seed}.png",
    )

    outputs = {
        "adaptive_predictions": pred_path,
        "adaptive_metrics_table": metrics_path,
        "adaptive_action_counts_table": actions_path,
        "adaptive_runtime_table": runtime_path,
        "adaptive_action_figure": str(fig_path),
    }

    summary = {
        "seed": seed,
        "scenarios": SCENARIOS,
        "method": "adaptive_fusion",
        "estimate_method": estimate_method,
        "actions": ACTIONS,
        "policy_type": "transparent_reliability_heuristic",
        "uses_dsp_filtered_signals": True,
        "uses_graph_prior": True,
        "outputs": outputs,
    }

    summary_path = f"results/logs/adaptive_fusion_summary_seed{seed}.json"
    save_json(summary, summary_path)
    outputs["adaptive_summary"] = summary_path

    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run adaptive reliability-based fusion."
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
        help="Seed matching generated signals.",
    )
    parser.add_argument(
        "--estimate-method",
        type=str,
        default="argmax",
        choices=["argmax", "expected"],
        help="How to estimate position from adaptive probability map.",
    )

    args = parser.parse_args()

    outputs = build_adaptive_outputs(
        config_path=args.config,
        seed=args.seed,
        estimate_method=args.estimate_method,
    )

    print("ADAPTIVE FUSION TEST OK")
    for name, path in outputs.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
