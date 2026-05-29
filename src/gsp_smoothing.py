"""
Graph signal processing smoothing for the SPICSCON 2026 indoor positioning project.

This module treats the 100-cell location probability vector as a graph signal over
the indoor grid graph.

Implemented smoothing methods:
1. Graph diffusion smoothing:
   p_smooth = normalize((1 - alpha) p + alpha A_norm p)

2. Laplacian/Tikhonov-style smoothing:
   p_smooth = normalize((I + lambda L)^(-1) p)

The goal is not to invent a new GSP algorithm. The goal is to test whether
topology-aware probability smoothing can reduce unstable probability maps and
support robust simulated indoor positioning.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Mapping, Tuple

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from scipy import sparse
from scipy.sparse.linalg import spsolve

from src.environment import create_grid_spec, make_grid_graph
from src.probability_maps import (
    choose_sample_time,
    estimate_position,
    fuse_probability_maps,
    load_grid_cells,
    probability_to_grid,
    vlp_probability_map,
    wifi_probability_map,
)
from src.utils import ensure_dir, load_config, save_csv, save_json


def normalize_probability(prob: np.ndarray, prob_floor: float = 1e-12) -> np.ndarray:
    """
    Normalize a probability vector with a small floor to avoid exact zeros.
    """
    prob = np.asarray(prob, dtype=float)
    prob = np.clip(prob, a_min=prob_floor, a_max=None)
    total = float(np.sum(prob))

    if not np.isfinite(total) or total <= 0:
        return np.ones_like(prob) / len(prob)

    return prob / total


def build_adjacency_matrix(graph: nx.Graph, num_nodes: int) -> sparse.csr_matrix:
    """
    Build sparse adjacency matrix using node IDs from 0 to num_nodes-1.
    """
    rows = []
    cols = []
    data = []

    for u, v in graph.edges():
        rows.extend([u, v])
        cols.extend([v, u])
        data.extend([1.0, 1.0])

    return sparse.csr_matrix((data, (rows, cols)), shape=(num_nodes, num_nodes))


def row_normalized_adjacency(adj: sparse.csr_matrix) -> sparse.csr_matrix:
    """
    Compute row-normalized adjacency D^-1 A.

    Isolated nodes, if any, receive zero row weights.
    """
    degree = np.asarray(adj.sum(axis=1)).ravel()
    inv_degree = np.zeros_like(degree, dtype=float)

    nonzero = degree > 0
    inv_degree[nonzero] = 1.0 / degree[nonzero]

    d_inv = sparse.diags(inv_degree)
    return d_inv @ adj


def graph_diffusion_smooth(
    prob: np.ndarray,
    adj_norm: sparse.csr_matrix,
    alpha: float = 0.25,
    iterations: int = 1,
    prob_floor: float = 1e-12,
) -> np.ndarray:
    """
    Smooth probability signal using graph diffusion.

    Each iteration mixes the current node probability with the average probability
    of neighboring grid cells.
    """
    p = normalize_probability(prob, prob_floor=prob_floor)
    alpha = float(np.clip(alpha, 0.0, 1.0))

    for _ in range(int(iterations)):
        p = (1.0 - alpha) * p + alpha * (adj_norm @ p)
        p = normalize_probability(p, prob_floor=prob_floor)

    return p


def graph_laplacian(adj: sparse.csr_matrix, normalized: bool = False) -> sparse.csr_matrix:
    """
    Create graph Laplacian.

    If normalized=False:
        L = D - A

    If normalized=True:
        L = I - D^(-1/2) A D^(-1/2)
    """
    degree = np.asarray(adj.sum(axis=1)).ravel()

    if not normalized:
        return sparse.diags(degree) - adj

    inv_sqrt_degree = np.zeros_like(degree, dtype=float)
    nonzero = degree > 0
    inv_sqrt_degree[nonzero] = 1.0 / np.sqrt(degree[nonzero])

    d_inv_sqrt = sparse.diags(inv_sqrt_degree)
    identity = sparse.eye(adj.shape[0], format="csr")

    return identity - d_inv_sqrt @ adj @ d_inv_sqrt


def laplacian_smooth(
    prob: np.ndarray,
    laplacian: sparse.csr_matrix,
    lambda_value: float = 0.1,
    prob_floor: float = 1e-12,
) -> np.ndarray:
    """
    Smooth probability signal using Tikhonov/Laplacian regularization.

    Solve:
        (I + lambda L) p_smooth = p_raw
    """
    p = normalize_probability(prob, prob_floor=prob_floor)
    n = len(p)

    identity = sparse.eye(n, format="csr")
    system = identity + float(lambda_value) * laplacian

    smoothed = spsolve(system, p)
    smoothed = np.asarray(smoothed, dtype=float)

    return normalize_probability(smoothed, prob_floor=prob_floor)


def entropy(prob: np.ndarray) -> float:
    """
    Shannon entropy of a probability vector.
    """
    p = normalize_probability(prob)
    return float(-np.sum(p * np.log(p + 1e-12)))


def peak_probability(prob: np.ndarray) -> float:
    """
    Highest cell probability.
    """
    p = normalize_probability(prob)
    return float(np.max(p))


def estimate_error(est: Mapping[str, float], true_x: float, true_y: float) -> float:
    """
    Euclidean error between estimated position and true position.
    """
    return float(((float(est["x"]) - true_x) ** 2 + (float(est["y"]) - true_y) ** 2) ** 0.5)


def load_signal_for_sample(seed: int, scenario: str) -> pd.DataFrame:
    """
    Load signal file for one seed/scenario.
    """
    path = Path(f"results/raw/signals_seed{seed}_{scenario}.csv")

    if not path.exists():
        raise FileNotFoundError(
            f"Missing signal file: {path}. "
            f"Run: python -m src.signal_models --config configs/default.yaml --seed {seed}"
        )

    return pd.read_csv(path)


def make_gsp_probability_sample(
    cfg: Mapping,
    seed: int,
    scenario: str,
    time_step: int | None = None,
    wifi_weight: float = 0.5,
) -> Tuple[pd.DataFrame, Dict[str, object]]:
    """
    Build raw and graph-smoothed probability maps for one sample time step.

    Returns
    -------
    tuple
        gsp_table, summary
    """
    cells = load_grid_cells("results/raw/grid_cells.csv")
    signal_df = load_signal_for_sample(seed=seed, scenario=scenario)

    if time_step is None:
        time_step = choose_sample_time(signal_df, scenario=scenario)

    selected = signal_df[signal_df["t"] == int(time_step)]
    if selected.empty:
        raise ValueError(f"time_step={time_step} not found for scenario={scenario}")

    row = selected.iloc[0]

    p_wifi = wifi_probability_map(cfg=cfg, cells=cells, row=row)
    p_vlp = vlp_probability_map(cfg=cfg, cells=cells, row=row)
    p_static = fuse_probability_maps(p_wifi=p_wifi, p_vlp=p_vlp, wifi_weight=wifi_weight)

    grid = create_grid_spec(cfg)
    graph = make_grid_graph(grid, neighbor_type=int(cfg["gsp"]["neighbor_type"]))
    num_nodes = len(cells)

    adj = build_adjacency_matrix(graph, num_nodes=num_nodes)
    adj_norm = row_normalized_adjacency(adj)
    lap = graph_laplacian(adj, normalized=False)

    alpha = float(cfg["gsp"]["smoothing_alpha"])
    lambda_values = cfg["gsp"].get("lambda_values", [0.1])
    lambda_value = float(lambda_values[1] if len(lambda_values) > 1 else lambda_values[0])

    p_diffusion_1 = graph_diffusion_smooth(
        p_static,
        adj_norm=adj_norm,
        alpha=alpha,
        iterations=1,
    )

    p_diffusion_3 = graph_diffusion_smooth(
        p_static,
        adj_norm=adj_norm,
        alpha=alpha,
        iterations=3,
    )

    p_laplacian = laplacian_smooth(
        p_static,
        laplacian=lap,
        lambda_value=lambda_value,
    )

    table = cells.copy()
    table["p_wifi"] = p_wifi
    table["p_vlp"] = p_vlp
    table["p_static_raw"] = p_static
    table["p_graph_diffusion_1"] = p_diffusion_1
    table["p_graph_diffusion_3"] = p_diffusion_3
    table["p_laplacian"] = p_laplacian

    true_x = float(row["true_x"])
    true_y = float(row["true_y"])

    estimates = {}
    for name, prob in [
        ("static_raw", p_static),
        ("graph_diffusion_1", p_diffusion_1),
        ("graph_diffusion_3", p_diffusion_3),
        ("laplacian", p_laplacian),
    ]:
        est = estimate_position(prob, cells, method="argmax")
        estimates[name] = {
            **est,
            "error_m": estimate_error(est, true_x=true_x, true_y=true_y),
            "entropy": entropy(prob),
            "peak_probability": peak_probability(prob),
        }

    summary = {
        "seed": seed,
        "scenario": scenario,
        "time_step": int(time_step),
        "wifi_weight": float(wifi_weight),
        "gsp_config": {
            "neighbor_type": int(cfg["gsp"]["neighbor_type"]),
            "smoothing_alpha": alpha,
            "diffusion_iterations": [1, 3],
            "lambda_value": lambda_value,
        },
        "true_position": {
            "x": true_x,
            "y": true_y,
        },
        "estimates": estimates,
    }

    return table, summary


def plot_gsp_sanity_figure(
    table: pd.DataFrame,
    cfg: Mapping,
    summary: Mapping[str, object],
    output_path: str | Path = "results/figures/fig4_raw_vs_graph_smoothed_heatmap.png",
) -> Path:
    """
    Plot raw static probability and graph-smoothed probability heatmaps.

    This is the draft Fig. 4 for the paper.
    """
    output_path = Path(output_path)
    ensure_dir(output_path.parent)

    grid_size = int(cfg["room"]["grid_size"])
    room_width = float(cfg["room"]["width_m"])
    room_height = float(cfg["room"]["height_m"])

    map_specs = [
        ("Raw static fusion", "p_static_raw"),
        ("Graph diffusion, 1 iter", "p_graph_diffusion_1"),
        ("Graph diffusion, 3 iter", "p_graph_diffusion_3"),
        ("Laplacian smoothing", "p_laplacian"),
    ]

    fig, axes = plt.subplots(1, 4, figsize=(15.0, 3.8), constrained_layout=True)

    true_x = float(summary["true_position"]["x"])
    true_y = float(summary["true_position"]["y"])

    for ax, (title, col) in zip(axes, map_specs):
        prob = table[col].to_numpy(dtype=float)
        grid_prob = probability_to_grid(prob, table, grid_size=grid_size)

        im = ax.imshow(
            grid_prob,
            origin="lower",
            extent=[0, room_width, 0, room_height],
            aspect="equal",
        )

        ax.scatter(true_x, true_y, marker="x", s=80, label="True")
        ax.set_title(title, fontsize=9)
        ax.set_xlabel("x (m)")
        ax.set_ylabel("y (m)")
        ax.legend(fontsize=7)
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    fig.suptitle(
        f"Raw vs Graph-Smoothed Probability Maps: {summary['scenario']} at t={summary['time_step']}",
        fontsize=12,
    )

    fig.savefig(output_path, dpi=300)
    plt.close(fig)

    return output_path


def build_gsp_outputs(
    config_path: str | Path = "configs/default.yaml",
    seed: int = 101,
    scenario: str = "s3_vlp_blocked",
    time_step: int | None = None,
    wifi_weight: float = 0.5,
) -> Dict[str, str]:
    """
    Build sample GSP probability smoothing outputs.

    Saves:
    - results/processed/gsp_probability_sample_seed101_<scenario>_t<time>.csv
    - results/figures/fig4_raw_vs_graph_smoothed_heatmap.png
    - results/logs/gsp_smoothing_summary_seed101.json
    """
    cfg = load_config(config_path)

    table, summary = make_gsp_probability_sample(
        cfg=cfg,
        seed=seed,
        scenario=scenario,
        time_step=time_step,
        wifi_weight=wifi_weight,
    )

    time_step_final = int(summary["time_step"])

    csv_path = f"results/processed/gsp_probability_sample_seed{seed}_{scenario}_t{time_step_final}.csv"
    save_csv(table, csv_path)

    fig_path = plot_gsp_sanity_figure(
        table=table,
        cfg=cfg,
        summary=summary,
        output_path="results/figures/fig4_raw_vs_graph_smoothed_heatmap.png",
    )

    summary["outputs"] = {
        "gsp_probability_sample_csv": csv_path,
        "gsp_sanity_figure": str(fig_path),
    }

    summary_path = f"results/logs/gsp_smoothing_summary_seed{seed}.json"
    save_json(summary, summary_path)

    return {
        "gsp_probability_sample_csv": csv_path,
        "gsp_sanity_figure": str(fig_path),
        "gsp_smoothing_summary": summary_path,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apply graph smoothing to location probability maps."
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
        "--scenario",
        type=str,
        default="s3_vlp_blocked",
        choices=["s1_clean", "s2_wifi_degraded", "s3_vlp_blocked", "s4_mixed_dynamic"],
        help="Scenario for GSP sample figure.",
    )
    parser.add_argument(
        "--time-step",
        type=int,
        default=None,
        help="Optional time step. If omitted, a useful degraded/blocked time is chosen.",
    )
    parser.add_argument(
        "--wifi-weight",
        type=float,
        default=0.5,
        help="WiFi weight for raw static fusion before smoothing.",
    )

    args = parser.parse_args()

    outputs = build_gsp_outputs(
        config_path=args.config,
        seed=args.seed,
        scenario=args.scenario,
        time_step=args.time_step,
        wifi_weight=args.wifi_weight,
    )

    print("GSP SMOOTHING TEST OK")
    for name, path in outputs.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
