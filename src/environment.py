"""
Environment generation for the SPICSCON 2026 indoor positioning simulation.

This module creates:
- a 10 m x 10 m indoor room
- a 10 x 10 grid of candidate location cells
- WiFi AP and LED anchor coordinates
- a 4-neighbor grid graph for later graph signal processing
- smooth synthetic walking trajectories
- scenario masks for clean/noisy/blocked/mixed conditions
- Fig. 1: room layout with anchors and a sample trajectory

The goal is not to model a real building perfectly. The goal is to create a
controlled and reproducible simulation testbed for the conference paper.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Tuple

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd

from src.utils import ensure_dir, load_config, save_csv, save_json, set_seed


@dataclass(frozen=True)
class GridSpec:
    """
    Basic grid description.

    Attributes
    ----------
    width_m:
        Room width in meters.
    height_m:
        Room height in meters.
    grid_size:
        Number of cells along each axis.
    cell_size_x:
        Width of one grid cell in meters.
    cell_size_y:
        Height of one grid cell in meters.
    """
    width_m: float
    height_m: float
    grid_size: int
    cell_size_x: float
    cell_size_y: float


def create_grid_spec(cfg: Mapping) -> GridSpec:
    """
    Create grid metadata from the configuration.

    Parameters
    ----------
    cfg:
        Full configuration dictionary.

    Returns
    -------
    GridSpec
        Grid geometry information.
    """
    room = cfg["room"]
    width_m = float(room["width_m"])
    height_m = float(room["height_m"])
    grid_size = int(room["grid_size"])

    return GridSpec(
        width_m=width_m,
        height_m=height_m,
        grid_size=grid_size,
        cell_size_x=width_m / grid_size,
        cell_size_y=height_m / grid_size,
    )


def cell_centers(grid: GridSpec) -> pd.DataFrame:
    """
    Generate center coordinates for all grid cells.

    Cell indexing:
        row-major order, index = row * grid_size + col

    Returns
    -------
    pandas.DataFrame
        Columns: cell_id, row, col, x, y
    """
    rows = []

    for row in range(grid.grid_size):
        for col in range(grid.grid_size):
            cell_id = row * grid.grid_size + col
            x = (col + 0.5) * grid.cell_size_x
            y = (row + 0.5) * grid.cell_size_y

            rows.append(
                {
                    "cell_id": cell_id,
                    "row": row,
                    "col": col,
                    "x": x,
                    "y": y,
                }
            )

    return pd.DataFrame(rows)


def create_anchors(cfg: Mapping) -> Dict[str, np.ndarray]:
    """
    Load WiFi AP and LED anchor positions from config.

    Returns
    -------
    dict
        {
            "wifi_ap": array of shape (num_wifi_ap, 2),
            "leds": array of shape (num_leds, 2)
        }
    """
    anchors = cfg["anchors"]

    wifi_ap = np.array(anchors["wifi_ap"], dtype=float)
    leds = np.array(anchors["leds"], dtype=float)

    return {
        "wifi_ap": wifi_ap,
        "leds": leds,
    }


def make_grid_graph(grid: GridSpec, neighbor_type: int = 4) -> nx.Graph:
    """
    Create a grid graph where each cell is a node.

    Parameters
    ----------
    grid:
        Grid specification.
    neighbor_type:
        4 for up/down/left/right neighbors.
        8 additionally includes diagonal neighbors.

    Returns
    -------
    networkx.Graph
        Grid graph with node attributes row and col.
    """
    if neighbor_type not in (4, 8):
        raise ValueError("neighbor_type must be 4 or 8.")

    graph = nx.Graph()
    n = grid.grid_size

    for row in range(n):
        for col in range(n):
            node = row * n + col
            graph.add_node(node, row=row, col=col)

    directions_4 = [
        (-1, 0),
        (1, 0),
        (0, -1),
        (0, 1),
    ]

    directions_diag = [
        (-1, -1),
        (-1, 1),
        (1, -1),
        (1, 1),
    ]

    directions = directions_4
    if neighbor_type == 8:
        directions = directions_4 + directions_diag

    for row in range(n):
        for col in range(n):
            node = row * n + col

            for dr, dc in directions:
                nr = row + dr
                nc = col + dc

                if 0 <= nr < n and 0 <= nc < n:
                    neighbor = nr * n + nc
                    graph.add_edge(node, neighbor)

    return graph


def clip_position(position: np.ndarray, grid: GridSpec) -> np.ndarray:
    """
    Keep a position inside the room boundaries.
    """
    clipped = np.array(position, dtype=float).copy()
    clipped[0] = np.clip(clipped[0], 0.05, grid.width_m - 0.05)
    clipped[1] = np.clip(clipped[1], 0.05, grid.height_m - 0.05)
    return clipped


def generate_trajectory(
    cfg: Mapping,
    seed: int,
    start: Tuple[float, float] | None = None,
) -> pd.DataFrame:
    """
    Generate one smooth synthetic walking trajectory.

    The person moves by taking small random directional steps. Direction changes
    are smoothed to avoid teleport-like motion.

    Parameters
    ----------
    cfg:
        Full configuration dictionary.
    seed:
        Random seed.
    start:
        Optional starting coordinate. If None, a random point is chosen.

    Returns
    -------
    pandas.DataFrame
        Columns: t, x, y
    """
    set_seed(seed)
    rng = np.random.default_rng(seed)

    grid = create_grid_spec(cfg)
    steps = int(cfg["trajectory"]["steps_per_trajectory"])
    max_step_m = float(cfg["trajectory"]["max_step_m"])

    if start is None:
        position = np.array(
            [
                rng.uniform(1.0, grid.width_m - 1.0),
                rng.uniform(1.0, grid.height_m - 1.0),
            ],
            dtype=float,
        )
    else:
        position = np.array(start, dtype=float)

    # Initial direction.
    angle = rng.uniform(0.0, 2.0 * np.pi)
    direction = np.array([np.cos(angle), np.sin(angle)], dtype=float)

    records = []

    for t in range(steps):
        records.append(
            {
                "t": t,
                "x": float(position[0]),
                "y": float(position[1]),
            }
        )

        # Smoothly update direction.
        noise_angle = rng.normal(loc=0.0, scale=0.35)
        rotation = np.array(
            [
                [np.cos(noise_angle), -np.sin(noise_angle)],
                [np.sin(noise_angle), np.cos(noise_angle)],
            ]
        )

        direction = rotation @ direction
        norm = np.linalg.norm(direction)
        if norm < 1e-12:
            direction = np.array([1.0, 0.0])
        else:
            direction = direction / norm

        step_length = rng.uniform(0.2 * max_step_m, max_step_m)
        next_position = position + step_length * direction

        # If hitting wall, reflect direction and step inward.
        if (
            next_position[0] <= 0.05
            or next_position[0] >= grid.width_m - 0.05
            or next_position[1] <= 0.05
            or next_position[1] >= grid.height_m - 0.05
        ):
            direction = -direction
            next_position = position + step_length * direction

        position = clip_position(next_position, grid)

    return pd.DataFrame(records)


def generate_scenario_masks(cfg: Mapping, scenario: str, seed: int) -> pd.DataFrame:
    """
    Generate time-step masks for each degradation scenario.

    Scenario meanings:
    - S1_clean: low noise, no blockage
    - S2_wifi_degraded: WiFi multipath/noise bursts
    - S3_vlp_blocked: visible-light blockage periods
    - S4_mixed_dynamic: alternating WiFi degradation and VLP blockage

    Returns
    -------
    pandas.DataFrame
        Columns:
        t, wifi_degraded, vlp_blocked, mixed_dynamic
    """
    rng = np.random.default_rng(seed)
    steps = int(cfg["trajectory"]["steps_per_trajectory"])

    wifi_degraded = np.zeros(steps, dtype=bool)
    vlp_blocked = np.zeros(steps, dtype=bool)
    mixed_dynamic = np.zeros(steps, dtype=bool)

    scenario = scenario.lower()

    if scenario == "s1_clean":
        pass

    elif scenario == "s2_wifi_degraded":
        # Random WiFi burst windows.
        for start in range(10, steps, 25):
            end = min(start + rng.integers(8, 16), steps)
            wifi_degraded[start:end] = True

    elif scenario == "s3_vlp_blocked":
        # Random VLP blockage windows.
        for start in range(15, steps, 30):
            end = min(start + rng.integers(8, 18), steps)
            vlp_blocked[start:end] = True

    elif scenario == "s4_mixed_dynamic":
        mixed_dynamic[:] = True

        # Alternating degradation windows.
        for start in range(10, steps, 35):
            end = min(start + rng.integers(8, 16), steps)
            wifi_degraded[start:end] = True

        for start in range(25, steps, 40):
            end = min(start + rng.integers(8, 18), steps)
            vlp_blocked[start:end] = True

    else:
        raise ValueError(
            "Unknown scenario. Use one of: "
            "s1_clean, s2_wifi_degraded, s3_vlp_blocked, s4_mixed_dynamic"
        )

    return pd.DataFrame(
        {
            "t": np.arange(steps),
            "wifi_degraded": wifi_degraded,
            "vlp_blocked": vlp_blocked,
            "mixed_dynamic": mixed_dynamic,
        }
    )


def plot_layout_and_trajectory(
    cfg: Mapping,
    trajectory: pd.DataFrame,
    output_path: str | Path = "results/figures/fig1_layout_trajectory.png",
) -> Path:
    """
    Plot room layout, grid, anchors, and one sample trajectory.

    Returns
    -------
    Path
        Saved figure path.
    """
    grid = create_grid_spec(cfg)
    anchors = create_anchors(cfg)

    output_path = Path(output_path)
    ensure_dir(output_path.parent)

    fig, ax = plt.subplots(figsize=(7.0, 7.0))

    # Draw grid lines.
    for i in range(grid.grid_size + 1):
        x = i * grid.cell_size_x
        y = i * grid.cell_size_y
        ax.plot([x, x], [0, grid.height_m], linewidth=0.5, alpha=0.35)
        ax.plot([0, grid.width_m], [y, y], linewidth=0.5, alpha=0.35)

    # Plot WiFi APs.
    wifi = anchors["wifi_ap"]
    ax.scatter(
        wifi[:, 0],
        wifi[:, 1],
        marker="^",
        s=130,
        label="WiFi APs",
        edgecolors="black",
    )

    for idx, (x, y) in enumerate(wifi):
        ax.text(x + 0.12, y + 0.12, f"AP{idx + 1}", fontsize=9)

    # Plot LEDs.
    leds = anchors["leds"]
    ax.scatter(
        leds[:, 0],
        leds[:, 1],
        marker="s",
        s=110,
        label="LED anchors",
        edgecolors="black",
    )

    for idx, (x, y) in enumerate(leds):
        ax.text(x + 0.12, y + 0.12, f"LED{idx + 1}", fontsize=9)

    # Plot trajectory.
    ax.plot(
        trajectory["x"],
        trajectory["y"],
        linewidth=2.0,
        label="Sample trajectory",
    )

    ax.scatter(
        trajectory["x"].iloc[0],
        trajectory["y"].iloc[0],
        marker="o",
        s=90,
        label="Start",
        edgecolors="black",
    )

    ax.scatter(
        trajectory["x"].iloc[-1],
        trajectory["y"].iloc[-1],
        marker="X",
        s=90,
        label="End",
        edgecolors="black",
    )

    ax.set_xlim(0, grid.width_m)
    ax.set_ylim(0, grid.height_m)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("x position (m)")
    ax.set_ylabel("y position (m)")
    ax.set_title("Indoor Layout with WiFi APs, LED Anchors, and Sample Trajectory")
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(False)

    fig.tight_layout()
    fig.savefig(output_path, dpi=300)
    plt.close(fig)

    return output_path


def build_environment_outputs(
    config_path: str | Path = "configs/default.yaml",
    seed: int = 101,
) -> Dict[str, str]:
    """
    Build and save the first environment outputs.

    Saves:
    - results/raw/trajectory_seed101.csv
    - results/raw/scenario_masks_seed101_<scenario>.csv
    - results/raw/grid_cells.csv
    - results/logs/environment_summary.json
    - results/figures/fig1_layout_trajectory.png

    Returns
    -------
    dict
        Paths to saved outputs.
    """
    cfg = load_config(config_path)
    grid = create_grid_spec(cfg)
    cells = cell_centers(grid)
    anchors = create_anchors(cfg)
    graph = make_grid_graph(grid, neighbor_type=int(cfg["gsp"]["neighbor_type"]))
    trajectory = generate_trajectory(cfg, seed=seed)

    outputs = {}

    outputs["grid_cells"] = str(save_csv(cells, "results/raw/grid_cells.csv"))
    outputs["trajectory"] = str(
        save_csv(trajectory, f"results/raw/trajectory_seed{seed}.csv")
    )

    scenarios = [
        "s1_clean",
        "s2_wifi_degraded",
        "s3_vlp_blocked",
        "s4_mixed_dynamic",
    ]

    for scenario in scenarios:
        masks = generate_scenario_masks(cfg, scenario=scenario, seed=seed)
        outputs[f"scenario_{scenario}"] = str(
            save_csv(masks, f"results/raw/scenario_masks_seed{seed}_{scenario}.csv")
        )

    outputs["figure_layout"] = str(
        plot_layout_and_trajectory(
            cfg,
            trajectory,
            output_path="results/figures/fig1_layout_trajectory.png",
        )
    )

    summary = {
        "seed": seed,
        "room_width_m": grid.width_m,
        "room_height_m": grid.height_m,
        "grid_size": grid.grid_size,
        "num_cells": int(len(cells)),
        "num_graph_nodes": int(graph.number_of_nodes()),
        "num_graph_edges": int(graph.number_of_edges()),
        "wifi_ap": anchors["wifi_ap"].tolist(),
        "leds": anchors["leds"].tolist(),
        "trajectory_steps": int(len(trajectory)),
        "outputs": outputs,
    }

    outputs["environment_summary"] = str(
        save_json(summary, "results/logs/environment_summary.json")
    )

    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate indoor environment, trajectory, scenario masks, and layout figure."
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
        help="Random seed for sample trajectory and scenario masks.",
    )

    args = parser.parse_args()

    outputs = build_environment_outputs(config_path=args.config, seed=args.seed)

    print("ENVIRONMENT TEST OK")
    for name, path in outputs.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
