"""
Signal generation for the SPICSCON 2026 hybrid indoor positioning project.

This module creates simplified but physically motivated signal streams:

1. WiFi RSSI-like signal:
   RSSI = P0 - 10 n log10(d) + noise + multipath/body-shadowing disturbance

2. Visible-light intensity-like signal:
   I = LED_power / distance_3d^2 + noise, with optional blockage loss

The purpose is controlled simulation, not hardware-level RF/VLP channel accuracy.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, Mapping

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.environment import create_anchors
from src.utils import ensure_dir, load_config, save_csv, save_json


SCENARIOS = [
    "s1_clean",
    "s2_wifi_degraded",
    "s3_vlp_blocked",
    "s4_mixed_dynamic",
]


def distance_2d(points_xy: np.ndarray, anchors_xy: np.ndarray, min_distance: float = 0.25) -> np.ndarray:
    """
    Compute 2D distance from each point to each anchor.

    Parameters
    ----------
    points_xy:
        Array with shape (T, 2).
    anchors_xy:
        Array with shape (A, 2).
    min_distance:
        Minimum distance used to avoid log/division problems.

    Returns
    -------
    np.ndarray
        Distance matrix with shape (T, A).
    """
    diff = points_xy[:, None, :] - anchors_xy[None, :, :]
    dist = np.linalg.norm(diff, axis=2)
    return np.maximum(dist, min_distance)


def distance_3d_to_leds(
    points_xy: np.ndarray,
    led_xy: np.ndarray,
    receiver_height_m: float,
    ceiling_height_m: float,
    min_distance: float = 0.25,
) -> np.ndarray:
    """
    Compute 3D distance from receiver position to ceiling LED anchors.
    """
    horizontal = distance_2d(points_xy, led_xy, min_distance=min_distance)
    dz = float(ceiling_height_m) - float(receiver_height_m)
    dist_3d = np.sqrt(horizontal**2 + dz**2)
    return np.maximum(dist_3d, min_distance)


def expected_wifi_rssi(
    points_xy: np.ndarray,
    wifi_ap_xy: np.ndarray,
    p0_dbm: float,
    path_loss_n: float,
) -> np.ndarray:
    """
    Compute clean expected WiFi RSSI for each point and WiFi AP.

    RSSI = P0 - 10 n log10(d)
    """
    dist = distance_2d(points_xy, wifi_ap_xy)
    return float(p0_dbm) - 10.0 * float(path_loss_n) * np.log10(dist)


def expected_vlp_intensity(
    points_xy: np.ndarray,
    led_xy: np.ndarray,
    led_power: float,
    receiver_height_m: float,
    ceiling_height_m: float,
) -> np.ndarray:
    """
    Compute clean expected visible-light intensity for each point and LED.

    I = LED_power / distance_3d^2
    """
    dist_3d = distance_3d_to_leds(
        points_xy=points_xy,
        led_xy=led_xy,
        receiver_height_m=receiver_height_m,
        ceiling_height_m=ceiling_height_m,
    )
    return float(led_power) / (dist_3d**2)


def add_wifi_noise(
    clean_rssi: np.ndarray,
    masks: pd.DataFrame,
    cfg: Mapping,
    rng: np.random.Generator,
) -> np.ndarray:
    """
    Add Gaussian noise and burst-like WiFi disturbance.

    Clean period:
        base Gaussian noise.

    WiFi degraded period:
        stronger Gaussian noise plus occasional attenuation bursts.
    """
    wifi_cfg = cfg["wifi_model"]

    base_sigma_db = float(wifi_cfg["base_sigma_db"])
    noisy_sigma_db = float(wifi_cfg["noisy_sigma_db"])
    burst_prob = float(wifi_cfg["multipath_burst_prob"])
    shadow_low, shadow_high = wifi_cfg["shadowing_db_range"]

    measured = clean_rssi.copy()
    wifi_degraded = masks["wifi_degraded"].to_numpy(dtype=bool)

    time_steps, num_aps = measured.shape

    for t in range(time_steps):
        sigma = noisy_sigma_db if wifi_degraded[t] else base_sigma_db
        measured[t, :] += rng.normal(loc=0.0, scale=sigma, size=num_aps)

        if wifi_degraded[t]:
            burst_mask = rng.random(num_aps) < burst_prob
            attenuation = rng.uniform(float(shadow_low), float(shadow_high), size=num_aps)
            measured[t, burst_mask] -= attenuation[burst_mask]

    return measured


def add_vlp_noise_and_blockage(
    clean_intensity: np.ndarray,
    masks: pd.DataFrame,
    cfg: Mapping,
    rng: np.random.Generator,
) -> np.ndarray:
    """
    Add optical noise and blockage to VLP intensity.

    VLP blocked period:
        one or more LEDs are attenuated.
    """
    vlp_cfg = cfg["vlp_model"]

    base_sigma = float(vlp_cfg["base_sigma"])
    blockage_loss = float(vlp_cfg["blockage_loss"])
    blockage_prob = float(vlp_cfg["blockage_prob"])

    measured = clean_intensity.copy()
    vlp_blocked = masks["vlp_blocked"].to_numpy(dtype=bool)

    time_steps, num_leds = measured.shape
    typical_scale = max(float(np.mean(clean_intensity)), 1e-9)

    for t in range(time_steps):
        measured[t, :] += rng.normal(loc=0.0, scale=base_sigma * typical_scale, size=num_leds)

        if vlp_blocked[t]:
            blocked_mask = rng.random(num_leds) < blockage_prob

            if not np.any(blocked_mask):
                blocked_mask[rng.integers(0, num_leds)] = True

            measured[t, blocked_mask] *= (1.0 - blockage_loss)

    return np.clip(measured, a_min=1e-9, a_max=None)


def generate_signals_for_scenario(
    cfg: Mapping,
    trajectory: pd.DataFrame,
    masks: pd.DataFrame,
    scenario: str,
    seed: int,
) -> pd.DataFrame:
    """
    Generate WiFi and VLP signals for one scenario.
    """
    rng = np.random.default_rng(seed)

    anchors = create_anchors(cfg)
    points_xy = trajectory[["x", "y"]].to_numpy(dtype=float)

    wifi_cfg = cfg["wifi_model"]
    vlp_cfg = cfg["vlp_model"]

    clean_wifi = expected_wifi_rssi(
        points_xy=points_xy,
        wifi_ap_xy=anchors["wifi_ap"],
        p0_dbm=float(wifi_cfg["p0_dbm"]),
        path_loss_n=float(wifi_cfg["path_loss_n"]),
    )

    clean_vlp = expected_vlp_intensity(
        points_xy=points_xy,
        led_xy=anchors["leds"],
        led_power=float(vlp_cfg["led_power"]),
        receiver_height_m=float(vlp_cfg["receiver_height_m"]),
        ceiling_height_m=float(vlp_cfg["ceiling_height_m"]),
    )

    measured_wifi = add_wifi_noise(
        clean_rssi=clean_wifi,
        masks=masks,
        cfg=cfg,
        rng=rng,
    )

    measured_vlp = add_vlp_noise_and_blockage(
        clean_intensity=clean_vlp,
        masks=masks,
        cfg=cfg,
        rng=rng,
    )

    output = pd.DataFrame(
        {
            "t": trajectory["t"].to_numpy(),
            "scenario": scenario,
            "true_x": trajectory["x"].to_numpy(),
            "true_y": trajectory["y"].to_numpy(),
            "wifi_degraded": masks["wifi_degraded"].to_numpy(dtype=bool),
            "vlp_blocked": masks["vlp_blocked"].to_numpy(dtype=bool),
            "mixed_dynamic": masks["mixed_dynamic"].to_numpy(dtype=bool),
        }
    )

    for i in range(measured_wifi.shape[1]):
        output[f"wifi_ap{i + 1}_dbm"] = measured_wifi[:, i]
        output[f"wifi_ap{i + 1}_clean_dbm"] = clean_wifi[:, i]

    for i in range(measured_vlp.shape[1]):
        output[f"vlp_led{i + 1}_intensity"] = measured_vlp[:, i]
        output[f"vlp_led{i + 1}_clean_intensity"] = clean_vlp[:, i]

    return output


def load_environment_outputs(seed: int) -> Dict[str, pd.DataFrame]:
    """
    Load trajectory and scenario masks generated by src.environment.
    """
    trajectory_path = Path(f"results/raw/trajectory_seed{seed}.csv")

    if not trajectory_path.exists():
        raise FileNotFoundError(
            f"Missing {trajectory_path}. Run: python -m src.environment --config configs/default.yaml --seed {seed}"
        )

    loaded: Dict[str, pd.DataFrame] = {
        "trajectory": pd.read_csv(trajectory_path)
    }

    for scenario in SCENARIOS:
        mask_path = Path(f"results/raw/scenario_masks_seed{seed}_{scenario}.csv")

        if not mask_path.exists():
            raise FileNotFoundError(
                f"Missing {mask_path}. Run: python -m src.environment --config configs/default.yaml --seed {seed}"
            )

        loaded[scenario] = pd.read_csv(mask_path)

    return loaded


def plot_signal_model_sanity(
    signal_tables: Dict[str, pd.DataFrame],
    output_path: str | Path = "results/figures/fig_signal_model_sanity.png",
) -> Path:
    """
    Plot representative WiFi AP1 and VLP LED1 signal curves for all scenarios.

    This is a sanity plot, not the final DSP-filter comparison figure.
    """
    output_path = Path(output_path)
    ensure_dir(output_path.parent)

    fig, axes = plt.subplots(2, 1, figsize=(9.0, 6.0), sharex=True)

    for scenario, df in signal_tables.items():
        axes[0].plot(df["t"], df["wifi_ap1_dbm"], linewidth=1.2, label=scenario)
        axes[1].plot(df["t"], df["vlp_led1_intensity"], linewidth=1.2, label=scenario)

    axes[0].set_title("WiFi RSSI-like Signal Sanity Check")
    axes[0].set_ylabel("AP1 RSSI (dBm)")
    axes[0].grid(True, alpha=0.3)
    axes[0].legend(fontsize=8)

    axes[1].set_title("Visible-Light Intensity-like Signal Sanity Check")
    axes[1].set_xlabel("Time step")
    axes[1].set_ylabel("LED1 intensity")
    axes[1].grid(True, alpha=0.3)
    axes[1].legend(fontsize=8)

    fig.tight_layout()
    fig.savefig(output_path, dpi=300)
    plt.close(fig)

    return output_path


def build_signal_outputs(
    config_path: str | Path = "configs/default.yaml",
    seed: int = 101,
) -> Dict[str, str]:
    """
    Generate signal CSVs and a sanity figure for all scenarios.
    """
    cfg = load_config(config_path)
    loaded = load_environment_outputs(seed=seed)

    trajectory = loaded["trajectory"]
    signal_tables: Dict[str, pd.DataFrame] = {}
    outputs: Dict[str, str] = {}

    for idx, scenario in enumerate(SCENARIOS):
        scenario_seed = seed + 1000 + idx

        df = generate_signals_for_scenario(
            cfg=cfg,
            trajectory=trajectory,
            masks=loaded[scenario],
            scenario=scenario,
            seed=scenario_seed,
        )

        csv_path = f"results/raw/signals_seed{seed}_{scenario}.csv"
        save_csv(df, csv_path)

        signal_tables[scenario] = df
        outputs[f"signals_{scenario}"] = csv_path

    figure_path = plot_signal_model_sanity(
        signal_tables=signal_tables,
        output_path="results/figures/fig_signal_model_sanity.png",
    )
    outputs["signal_model_sanity_figure"] = str(figure_path)

    example_df = next(iter(signal_tables.values()))

    summary = {
        "seed": seed,
        "scenarios": SCENARIOS,
        "num_time_steps": int(len(trajectory)),
        "wifi_signal_columns": [col for col in example_df.columns if col.startswith("wifi_ap")],
        "vlp_signal_columns": [col for col in example_df.columns if col.startswith("vlp_led")],
        "outputs": outputs,
    }

    summary_path = save_json(summary, "results/logs/signal_model_summary.json")
    outputs["signal_model_summary"] = str(summary_path)

    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate WiFi RSSI-like and VLP intensity-like signals."
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
        help="Seed matching the generated trajectory and scenario masks.",
    )

    args = parser.parse_args()

    outputs = build_signal_outputs(config_path=args.config, seed=args.seed)

    print("SIGNAL MODEL TEST OK")
    for name, path in outputs.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
