"""
Evaluation metrics for the SPICSCON 2026 indoor positioning simulation.

This module provides reusable metrics for:
- mean localization error
- median localization error
- 90th percentile error
- zone/radius accuracy
- failure rate
- trajectory smoothness
- recovery time after degradation events

The metrics are intentionally simple, transparent, and paper-friendly.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, Mapping, Optional

import numpy as np
import pandas as pd

from src.utils import ensure_dir, save_json


def euclidean_errors(
    true_xy: np.ndarray,
    pred_xy: np.ndarray,
) -> np.ndarray:
    """
    Compute Euclidean localization error for each time step.

    Parameters
    ----------
    true_xy:
        Array with shape (T, 2), true x-y positions.
    pred_xy:
        Array with shape (T, 2), predicted x-y positions.

    Returns
    -------
    np.ndarray
        Error vector with shape (T,).
    """
    true_xy = np.asarray(true_xy, dtype=float)
    pred_xy = np.asarray(pred_xy, dtype=float)

    if true_xy.shape != pred_xy.shape:
        raise ValueError(
            f"true_xy and pred_xy must have the same shape. "
            f"Got {true_xy.shape} and {pred_xy.shape}."
        )

    if true_xy.ndim != 2 or true_xy.shape[1] != 2:
        raise ValueError("true_xy and pred_xy must have shape (T, 2).")

    return np.linalg.norm(true_xy - pred_xy, axis=1)


def mean_error(errors: np.ndarray) -> float:
    """
    Mean localization error.
    """
    errors = np.asarray(errors, dtype=float)
    return float(np.mean(errors))


def median_error(errors: np.ndarray) -> float:
    """
    Median localization error.
    """
    errors = np.asarray(errors, dtype=float)
    return float(np.median(errors))


def percentile_error(errors: np.ndarray, percentile: float = 90.0) -> float:
    """
    Percentile localization error, e.g., 90th percentile error.
    """
    errors = np.asarray(errors, dtype=float)
    return float(np.percentile(errors, percentile))


def zone_accuracy(errors: np.ndarray, zone_radius_m: float = 1.0) -> float:
    """
    Fraction of predictions within a radius threshold.

    This is useful because exact cell match may be too strict for a 1 m grid.
    """
    errors = np.asarray(errors, dtype=float)
    return float(np.mean(errors <= float(zone_radius_m)))


def failure_rate(errors: np.ndarray, failure_threshold_m: float = 2.0) -> float:
    """
    Fraction of predictions whose error exceeds a failure threshold.
    """
    errors = np.asarray(errors, dtype=float)
    return float(np.mean(errors > float(failure_threshold_m)))


def trajectory_smoothness(pred_xy: np.ndarray) -> float:
    """
    Average step-to-step movement in the estimated trajectory.

    A very large value may indicate impossible localization jumps.
    A smaller value usually means smoother estimates, although oversmoothing
    can also hide real movement. This metric should be interpreted with error.
    """
    pred_xy = np.asarray(pred_xy, dtype=float)

    if pred_xy.ndim != 2 or pred_xy.shape[1] != 2:
        raise ValueError("pred_xy must have shape (T, 2).")

    if len(pred_xy) < 2:
        return 0.0

    jumps = np.linalg.norm(np.diff(pred_xy, axis=0), axis=1)
    return float(np.mean(jumps))


def recovery_time_after_events(
    errors: np.ndarray,
    event_mask: np.ndarray,
    failure_threshold_m: float = 2.0,
    trigger: str = "start",
) -> float:
    """
    Estimate recovery time around degradation events.

    For each degradation event, this function checks how many time steps are
    needed until the localization error becomes <= failure_threshold_m.

    Parameters
    ----------
    errors:
        Error vector with shape (T,).
    event_mask:
        Boolean vector with shape (T,), True during degradation/blockage.
    failure_threshold_m:
        Error threshold used to define failure.
    trigger:
        "start" measures recovery after event start.
        "end" measures recovery after event ends.

    Returns
    -------
    float
        Average recovery time in time steps. Returns 0 if no relevant events exist.

    Notes
    -----
    This is a simple simulation metric. In the paper, we should describe it
    carefully and avoid overclaiming real-world self-healing.
    """
    errors = np.asarray(errors, dtype=float)
    event_mask = np.asarray(event_mask, dtype=bool)

    if errors.shape[0] != event_mask.shape[0]:
        raise ValueError("errors and event_mask must have the same length.")

    if trigger not in {"start", "end"}:
        raise ValueError("trigger must be either 'start' or 'end'.")

    recovery_steps = []
    T = len(errors)

    if trigger == "start":
        candidate_indices = [
            i for i in range(T)
            if event_mask[i] and (i == 0 or not event_mask[i - 1])
        ]
    else:
        candidate_indices = [
            i for i in range(T)
            if (not event_mask[i]) and i > 0 and event_mask[i - 1]
        ]

    for start_idx in candidate_indices:
        recovered = None

        for j in range(start_idx, T):
            if errors[j] <= failure_threshold_m:
                recovered = j - start_idx
                break

        if recovered is not None:
            recovery_steps.append(recovered)

    if not recovery_steps:
        return 0.0

    return float(np.mean(recovery_steps))


def summarize_errors(
    errors: np.ndarray,
    pred_xy: Optional[np.ndarray] = None,
    zone_radius_m: float = 1.0,
    failure_threshold_m: float = 2.0,
) -> Dict[str, float]:
    """
    Create a compact metric summary from localization errors.

    Parameters
    ----------
    errors:
        Error vector.
    pred_xy:
        Optional predicted trajectory for smoothness calculation.
    zone_radius_m:
        Threshold for zone accuracy.
    failure_threshold_m:
        Threshold for failure rate.

    Returns
    -------
    dict
        Summary metric dictionary.
    """
    errors = np.asarray(errors, dtype=float)

    summary = {
        "mean_error_m": mean_error(errors),
        "median_error_m": median_error(errors),
        "p90_error_m": percentile_error(errors, 90.0),
        "zone_accuracy": zone_accuracy(errors, zone_radius_m=zone_radius_m),
        "failure_rate": failure_rate(errors, failure_threshold_m=failure_threshold_m),
    }

    if pred_xy is not None:
        summary["trajectory_smoothness_m_per_step"] = trajectory_smoothness(pred_xy)

    return summary


def summarize_runtime(runtime_seconds: Iterable[float]) -> Dict[str, float]:
    """
    Summarize runtime measurements.
    """
    values = np.asarray(list(runtime_seconds), dtype=float)

    if len(values) == 0:
        return {
            "mean_runtime_s": 0.0,
            "median_runtime_s": 0.0,
            "p90_runtime_s": 0.0,
        }

    return {
        "mean_runtime_s": float(np.mean(values)),
        "median_runtime_s": float(np.median(values)),
        "p90_runtime_s": float(np.percentile(values, 90.0)),
    }


def metrics_from_prediction_frame(
    df: pd.DataFrame,
    true_x_col: str = "true_x",
    true_y_col: str = "true_y",
    pred_x_col: str = "pred_x",
    pred_y_col: str = "pred_y",
    zone_radius_m: float = 1.0,
    failure_threshold_m: float = 2.0,
) -> Dict[str, float]:
    """
    Compute summary metrics from a DataFrame containing true and predicted positions.
    """
    required = [true_x_col, true_y_col, pred_x_col, pred_y_col]
    missing = [col for col in required if col not in df.columns]

    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    true_xy = df[[true_x_col, true_y_col]].to_numpy(dtype=float)
    pred_xy = df[[pred_x_col, pred_y_col]].to_numpy(dtype=float)

    errors = euclidean_errors(true_xy, pred_xy)

    return summarize_errors(
        errors=errors,
        pred_xy=pred_xy,
        zone_radius_m=zone_radius_m,
        failure_threshold_m=failure_threshold_m,
    )


def build_metrics_sample(
    probability_summary_path: str | Path = "results/logs/probability_map_summary.json",
    output_path: str | Path = "results/logs/metrics_sample_summary.json",
) -> Dict[str, object]:
    """
    Build a small metrics sanity check using the probability-map summary.

    This is not the final experiment table. It simply verifies that the metric
    functions work using the already-generated sample WiFi/VLP/static estimates.
    """
    probability_summary_path = Path(probability_summary_path)

    if not probability_summary_path.exists():
        raise FileNotFoundError(
            f"Missing {probability_summary_path}. "
            "Run: python -m src.probability_maps first."
        )

    with probability_summary_path.open("r", encoding="utf-8") as f:
        summary = json.load(f)

    true_xy = np.array(
        [
            [
                summary["true_position"]["x"],
                summary["true_position"]["y"],
            ]
        ],
        dtype=float,
    )

    method_estimates = {
        "wifi": summary["wifi_estimate"],
        "vlp": summary["vlp_estimate"],
        "static_fusion": summary["static_fusion_estimate"],
    }

    metric_results = {}

    for method, estimate in method_estimates.items():
        pred_xy = np.array([[estimate["x"], estimate["y"]]], dtype=float)
        errors = euclidean_errors(true_xy, pred_xy)

        metric_results[method] = summarize_errors(
            errors=errors,
            pred_xy=pred_xy,
            zone_radius_m=1.0,
            failure_threshold_m=2.0,
        )

    output = {
        "source": str(probability_summary_path),
        "note": "Single-time-step sanity check only. Final metrics require full trajectories.",
        "metrics": metric_results,
    }

    save_json(output, output_path)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a small metrics sanity check from probability-map summary."
    )
    parser.add_argument(
        "--probability-summary",
        type=str,
        default="results/logs/probability_map_summary.json",
        help="Path to probability-map summary JSON.",
    )
    parser.add_argument(
        "--out",
        type=str,
        default="results/logs/metrics_sample_summary.json",
        help="Output JSON path.",
    )

    args = parser.parse_args()

    output = build_metrics_sample(
        probability_summary_path=args.probability_summary,
        output_path=args.out,
    )

    print("METRICS TEST OK")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
