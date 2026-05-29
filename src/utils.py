"""
Utility functions for the SPICSCON 2026 indoor positioning simulation project.

This module intentionally contains only small reusable helpers:
- configuration loading
- directory creation
- random seed control
- JSON/CSV saving
- project-root detection

All experiment scripts should use these helpers so outputs remain reproducible.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional

import numpy as np
import pandas as pd
import yaml


def project_root() -> Path:
    """
    Return the project root directory.

    This function assumes this file is located at:
        <project_root>/src/utils.py

    Returns
    -------
    Path
        Absolute path to the project root.
    """
    return Path(__file__).resolve().parents[1]


def ensure_dir(path: str | Path) -> Path:
    """
    Create a directory if it does not already exist.

    Parameters
    ----------
    path:
        Directory path.

    Returns
    -------
    Path
        The created/existing directory path.
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_config(config_path: str | Path = "configs/default.yaml") -> Dict[str, Any]:
    """
    Load a YAML configuration file.

    Parameters
    ----------
    config_path:
        Path to YAML config. Relative paths are interpreted from the
        current working directory.

    Returns
    -------
    dict
        Parsed configuration dictionary.

    Raises
    ------
    FileNotFoundError
        If the config file does not exist.
    ValueError
        If the YAML file is empty or invalid.
    """
    config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    if not isinstance(cfg, dict):
        raise ValueError(f"Config file is empty or invalid: {config_path}")

    return cfg


def set_seed(seed: int) -> None:
    """
    Set random seeds for reproducible NumPy and Python random behavior.

    Parameters
    ----------
    seed:
        Integer random seed.
    """
    random.seed(seed)
    np.random.seed(seed)


def save_json(data: Mapping[str, Any], output_path: str | Path, indent: int = 2) -> Path:
    """
    Save a dictionary-like object as JSON.

    Parameters
    ----------
    data:
        Dictionary-like object.
    output_path:
        Destination JSON file.
    indent:
        JSON indentation level.

    Returns
    -------
    Path
        Saved file path.
    """
    output_path = Path(output_path)
    ensure_dir(output_path.parent)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent)

    return output_path


def save_csv(
    rows: Iterable[Mapping[str, Any]] | pd.DataFrame,
    output_path: str | Path,
    index: bool = False,
) -> Path:
    """
    Save rows or a DataFrame as CSV.

    Parameters
    ----------
    rows:
        Iterable of dictionaries or pandas DataFrame.
    output_path:
        Destination CSV file.
    index:
        Whether to write DataFrame index.

    Returns
    -------
    Path
        Saved file path.
    """
    output_path = Path(output_path)
    ensure_dir(output_path.parent)

    if isinstance(rows, pd.DataFrame):
        df = rows
    else:
        df = pd.DataFrame(list(rows))

    df.to_csv(output_path, index=index)
    return output_path


def save_numpy(array: np.ndarray, output_path: str | Path) -> Path:
    """
    Save a NumPy array to .npy format.

    Parameters
    ----------
    array:
        NumPy array to save.
    output_path:
        Destination .npy path.

    Returns
    -------
    Path
        Saved file path.
    """
    output_path = Path(output_path)
    ensure_dir(output_path.parent)
    np.save(output_path, array)
    return output_path


def config_summary(cfg: Mapping[str, Any]) -> Dict[str, Any]:
    """
    Create a compact summary of the main experiment configuration.

    Parameters
    ----------
    cfg:
        Full configuration dictionary.

    Returns
    -------
    dict
        Compact summary useful for logs.
    """
    return {
        "project": cfg.get("project", {}).get("name"),
        "room": cfg.get("room", {}),
        "anchors": cfg.get("anchors", {}),
        "trajectory": cfg.get("trajectory", {}),
        "metrics": cfg.get("metrics", {}),
    }


if __name__ == "__main__":
    cfg = load_config()
    print("UTILS TEST OK")
    print("Project root:", project_root())
    print("Project:", cfg["project"]["name"])
    print("Config summary:")
    print(json.dumps(config_summary(cfg), indent=2))
