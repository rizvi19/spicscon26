"""Fixed-parameter constant-velocity Kalman tracking baselines.

The tracker consumes localization estimates only. Ground truth is used after
tracking for evaluation and is never used for initialization or filtering.
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class KalmanSettings:
    """Transparent fixed parameters selected before held-out-seed evaluation."""

    dt: float = 1.0
    process_acceleration_variance: float = 0.04
    measurement_variance: float = 1.0
    initial_velocity_variance: float = 1.0


def constant_velocity_kalman(observed_xy: np.ndarray, settings: KalmanSettings = KalmanSettings()) -> np.ndarray:
    """Filter x-y observations with a standard [x, y, vx, vy] Kalman model."""
    observations = np.asarray(observed_xy, dtype=float)
    if observations.ndim != 2 or observations.shape[1] != 2 or len(observations) == 0:
        raise ValueError("observed_xy must be a non-empty array with shape (T, 2)")
    if not np.isfinite(observations).all():
        raise ValueError("observed_xy must contain only finite values")

    dt = settings.dt
    transition = np.array([[1.0, 0.0, dt, 0.0], [0.0, 1.0, 0.0, dt], [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]])
    measurement = np.array([[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]])
    q = settings.process_acceleration_variance
    process_noise = q * np.array([[dt**4 / 4, 0.0, dt**3 / 2, 0.0], [0.0, dt**4 / 4, 0.0, dt**3 / 2], [dt**3 / 2, 0.0, dt**2, 0.0], [0.0, dt**3 / 2, 0.0, dt**2]])
    measurement_noise = settings.measurement_variance * np.eye(2)
    state = np.array([observations[0, 0], observations[0, 1], 0.0, 0.0])
    covariance = np.diag([settings.measurement_variance, settings.measurement_variance, settings.initial_velocity_variance, settings.initial_velocity_variance])
    identity = np.eye(4)
    filtered = []
    for index, observation in enumerate(observations):
        if index:
            state = transition @ state
            covariance = transition @ covariance @ transition.T + process_noise
        innovation = observation - measurement @ state
        innovation_covariance = measurement @ covariance @ measurement.T + measurement_noise
        gain = covariance @ measurement.T @ np.linalg.inv(innovation_covariance)
        state = state + gain @ innovation
        covariance = (identity - gain @ measurement) @ covariance
        filtered.append(state[:2].copy())
    return np.asarray(filtered)


def track_prediction_frame(predictions: pd.DataFrame, source_method: str, output_method: str, settings: KalmanSettings = KalmanSettings()) -> pd.DataFrame:
    """Create a tracking prediction frame from one ordered source-method frame."""
    source = predictions[predictions["method"] == source_method].sort_values("t").copy()
    if source.empty:
        raise ValueError(f"No predictions found for source method {source_method}")
    source[["pred_x", "pred_y"]] = constant_velocity_kalman(source[["pred_x", "pred_y"]].to_numpy(), settings=settings)
    source["method"] = output_method
    source["source_method"] = source_method
    return source
