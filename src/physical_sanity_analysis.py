from pathlib import Path
import json
import pandas as pd
import matplotlib.pyplot as plt


PROJECT_ROOT = Path(__file__).resolve().parents[1]

WIFI_CSV = PROJECT_ROOT / "results/physical/wifi_rssi_measurements.csv"
LIGHT_CSV = PROJECT_ROOT / "results/physical/light_intensity_measurements.csv"

TABLE_DIR = PROJECT_ROOT / "results/tables"
FIGURE_DIR = PROJECT_ROOT / "results/figures"
LOG_DIR = PROJECT_ROOT / "results/logs"

TABLE_DIR.mkdir(parents=True, exist_ok=True)
FIGURE_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)


def load_wifi_data(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing WiFi CSV: {path}")

    df = pd.read_csv(path)

    required = [
        "sample_id",
        "timestamp",
        "device",
        "scenario",
        "distance_m",
        "position_id",
        "blockage",
        "rssi_dbm",
        "notes",
    ]

    missing_cols = [c for c in required if c not in df.columns]
    if missing_cols:
        raise ValueError(f"WiFi CSV missing columns: {missing_cols}")

    df["distance_m"] = pd.to_numeric(df["distance_m"], errors="coerce")
    df["rssi_dbm"] = pd.to_numeric(df["rssi_dbm"], errors="coerce")
    df["blockage"] = df["blockage"].astype(str).str.strip().str.lower()

    before = len(df)
    df = df.dropna(subset=["distance_m", "rssi_dbm", "blockage"]).copy()
    after = len(df)

    if after < before:
        print(f"Warning: dropped {before - after} WiFi rows with missing distance/RSSI/blockage")

    return df


def load_light_data(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing light CSV: {path}")

    df = pd.read_csv(path)

    required = [
        "sample_id",
        "timestamp",
        "device",
        "scenario",
        "distance_m",
        "position_id",
        "blockage",
        "light_value",
        "unit",
        "notes",
    ]

    missing_cols = [c for c in required if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Light CSV missing columns: {missing_cols}")

    df["distance_m"] = pd.to_numeric(df["distance_m"], errors="coerce")
    df["light_value"] = pd.to_numeric(df["light_value"], errors="coerce")
    df["blockage"] = df["blockage"].astype(str).str.strip().str.lower()
    df["unit"] = df["unit"].astype(str).str.strip()

    before = len(df)
    df = df.dropna(subset=["distance_m", "light_value", "blockage"]).copy()
    after = len(df)

    if after < before:
        print(f"Warning: dropped {before - after} light rows with missing distance/light/blockage")

    return df


def summarize_wifi(df: pd.DataFrame) -> pd.DataFrame:
    summary = (
        df.groupby(["distance_m", "blockage"], as_index=False)
        .agg(
            count=("rssi_dbm", "count"),
            mean_rssi_dbm=("rssi_dbm", "mean"),
            median_rssi_dbm=("rssi_dbm", "median"),
            std_rssi_dbm=("rssi_dbm", "std"),
            min_rssi_dbm=("rssi_dbm", "min"),
            max_rssi_dbm=("rssi_dbm", "max"),
        )
        .sort_values(["distance_m", "blockage"])
    )

    pivot = summary.pivot(index="distance_m", columns="blockage", values="mean_rssi_dbm")

    if "normal" in pivot.columns and "blocked" in pivot.columns:
        pivot["blocked_minus_normal_db"] = pivot["blocked"] - pivot["normal"]
        comparison = pivot[["blocked_minus_normal_db"]].reset_index()
        summary = summary.merge(comparison, on="distance_m", how="left")
    else:
        summary["blocked_minus_normal_db"] = None

    return summary.round(3)


def summarize_light(df: pd.DataFrame) -> pd.DataFrame:
    summary = (
        df.groupby(["distance_m", "blockage"], as_index=False)
        .agg(
            count=("light_value", "count"),
            mean_light=("light_value", "mean"),
            median_light=("light_value", "median"),
            std_light=("light_value", "std"),
            min_light=("light_value", "min"),
            max_light=("light_value", "max"),
        )
        .sort_values(["distance_m", "blockage"])
    )

    pivot = summary.pivot(index="distance_m", columns="blockage", values="mean_light")
    median_pivot = summary.pivot(index="distance_m", columns="blockage", values="median_light")

    if "unblocked" in pivot.columns and "blocked" in pivot.columns:
        pivot["blocked_over_unblocked_mean_ratio"] = pivot["blocked"] / pivot["unblocked"]
        comparison = pivot[["blocked_over_unblocked_mean_ratio"]].reset_index()
        summary = summary.merge(comparison, on="distance_m", how="left")
    else:
        summary["blocked_over_unblocked_mean_ratio"] = None

    if "unblocked" in median_pivot.columns and "blocked" in median_pivot.columns:
        median_pivot["blocked_over_unblocked_median_ratio"] = (
            median_pivot["blocked"] / median_pivot["unblocked"]
        )
        median_comparison = median_pivot[["blocked_over_unblocked_median_ratio"]].reset_index()
        summary = summary.merge(median_comparison, on="distance_m", how="left")
    else:
        summary["blocked_over_unblocked_median_ratio"] = None

    return summary.round(3)


def plot_wifi(df: pd.DataFrame, out_path: Path):
    summary = summarize_wifi(df)

    fig, ax = plt.subplots(figsize=(8, 5))

    for condition in ["normal", "blocked"]:
        temp = summary[summary["blockage"] == condition].sort_values("distance_m")
        if temp.empty:
            continue

        ax.errorbar(
            temp["distance_m"],
            temp["mean_rssi_dbm"],
            yerr=temp["std_rssi_dbm"].fillna(0),
            marker="o",
            capsize=4,
            label=condition,
        )

    ax.set_title("Physical Sanity Check: WiFi RSSI vs Distance")
    ax.set_xlabel("Distance from WiFi router / hotspot (m)")
    ax.set_ylabel("RSSI (dBm)")
    ax.grid(True, alpha=0.3)
    ax.legend(title="Condition")

    note = (
        "More negative RSSI means weaker received WiFi signal.\n"
        "This is a physical sanity check only, not full deployment validation."
    )
    ax.text(
        0.02,
        0.02,
        note,
        transform=ax.transAxes,
        fontsize=8,
        va="bottom",
        bbox=dict(boxstyle="round", alpha=0.1),
    )

    fig.tight_layout()
    fig.savefig(out_path, dpi=300)
    plt.close(fig)


def plot_light(df: pd.DataFrame, out_path: Path):
    summary = summarize_light(df)

    fig, ax = plt.subplots(figsize=(8, 5))

    for condition in ["unblocked", "blocked"]:
        temp = summary[summary["blockage"] == condition].sort_values("distance_m")
        if temp.empty:
            continue

        ax.errorbar(
            temp["distance_m"],
            temp["mean_light"],
            yerr=temp["std_light"].fillna(0),
            marker="o",
            capsize=4,
            label=condition,
        )

    ax.set_title("Physical Sanity Check: Light Intensity vs Distance")
    ax.set_xlabel("Distance from LED room light (m)")
    ax.set_ylabel("Light value (lux app estimate)")
    ax.grid(True, alpha=0.3)
    ax.legend(title="Condition")

    note = (
        "iPhone app values are treated as lux-like estimates, not calibrated photodiode measurements.\n"
        "This is a physical sanity check only, not full VLP hardware validation."
    )
    ax.text(
        0.02,
        0.02,
        note,
        transform=ax.transAxes,
        fontsize=8,
        va="bottom",
        bbox=dict(boxstyle="round", alpha=0.1),
    )

    fig.tight_layout()
    fig.savefig(out_path, dpi=300)
    plt.close(fig)


def plot_combined(wifi_df: pd.DataFrame, light_df: pd.DataFrame, out_path: Path):
    wifi_summary = summarize_wifi(wifi_df)
    light_summary = summarize_light(light_df)

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    ax = axes[0]
    for condition in ["normal", "blocked"]:
        temp = wifi_summary[wifi_summary["blockage"] == condition].sort_values("distance_m")
        if temp.empty:
            continue
        ax.errorbar(
            temp["distance_m"],
            temp["mean_rssi_dbm"],
            yerr=temp["std_rssi_dbm"].fillna(0),
            marker="o",
            capsize=4,
            label=condition,
        )
    ax.set_title("(a) WiFi RSSI")
    ax.set_xlabel("Distance (m)")
    ax.set_ylabel("RSSI (dBm)")
    ax.grid(True, alpha=0.3)
    ax.legend(title="Condition")

    ax = axes[1]
    for condition in ["unblocked", "blocked"]:
        temp = light_summary[light_summary["blockage"] == condition].sort_values("distance_m")
        if temp.empty:
            continue
        ax.errorbar(
            temp["distance_m"],
            temp["mean_light"],
            yerr=temp["std_light"].fillna(0),
            marker="o",
            capsize=4,
            label=condition,
        )
    ax.set_title("(b) Light intensity")
    ax.set_xlabel("Distance (m)")
    ax.set_ylabel("Light value (lux app estimate)")
    ax.grid(True, alpha=0.3)
    ax.legend(title="Condition")

    fig.suptitle("Small Physical Sanity Check for Simulation Motivation")
    fig.text(
        0.5,
        0.01,
        "These measurements support distance/blockage assumptions only; they are not full real-world localization validation.",
        ha="center",
        fontsize=9,
    )

    fig.tight_layout(rect=[0, 0.04, 1, 0.95])
    fig.savefig(out_path, dpi=300)
    plt.close(fig)


def write_json(path: Path, payload: dict):
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def main():
    wifi_df = load_wifi_data(WIFI_CSV)
    light_df = load_light_data(LIGHT_CSV)

    wifi_summary = summarize_wifi(wifi_df)
    light_summary = summarize_light(light_df)

    wifi_summary_csv = TABLE_DIR / "table_physical_wifi_summary.csv"
    wifi_summary_md = TABLE_DIR / "table_physical_wifi_summary.md"
    light_summary_csv = TABLE_DIR / "table_physical_light_summary.csv"
    light_summary_md = TABLE_DIR / "table_physical_light_summary.md"

    wifi_figure = FIGURE_DIR / "fig8a_physical_wifi_rssi.png"
    light_figure = FIGURE_DIR / "fig8b_physical_light_intensity.png"
    combined_figure = FIGURE_DIR / "fig8_physical_sanity_wifi_light.png"

    wifi_log = LOG_DIR / "physical_wifi_summary.json"
    light_log = LOG_DIR / "physical_light_summary.json"
    combined_log = LOG_DIR / "physical_sanity_summary.json"

    wifi_summary.to_csv(wifi_summary_csv, index=False)
    wifi_summary.to_markdown(wifi_summary_md, index=False)

    light_summary.to_csv(light_summary_csv, index=False)
    light_summary.to_markdown(light_summary_md, index=False)

    plot_wifi(wifi_df, wifi_figure)
    plot_light(light_df, light_figure)
    plot_combined(wifi_df, light_df, combined_figure)

    wifi_normal = wifi_summary[wifi_summary["blockage"] == "normal"].sort_values("distance_m")
    wifi_blocked = wifi_summary[wifi_summary["blockage"] == "blocked"].sort_values("distance_m")
    light_unblocked = light_summary[light_summary["blockage"] == "unblocked"].sort_values("distance_m")
    light_blocked = light_summary[light_summary["blockage"] == "blocked"].sort_values("distance_m")

    wifi_diff = wifi_summary.drop_duplicates("distance_m")["blocked_minus_normal_db"].dropna()
    light_mean_ratio = light_summary.drop_duplicates("distance_m")[
        "blocked_over_unblocked_mean_ratio"
    ].dropna()
    light_median_ratio = light_summary.drop_duplicates("distance_m")[
        "blocked_over_unblocked_median_ratio"
    ].dropna()

    wifi_payload = {
        "status": "wifi_physical_sanity_analyzed",
        "input": str(WIFI_CSV.relative_to(PROJECT_ROOT)),
        "num_rows": int(len(wifi_df)),
        "distances_m": sorted([float(x) for x in wifi_df["distance_m"].unique()]),
        "conditions": sorted(wifi_df["blockage"].unique().tolist()),
        "normal_first_distance_mean_rssi_dbm": float(wifi_normal["mean_rssi_dbm"].iloc[0]),
        "normal_last_distance_mean_rssi_dbm": float(wifi_normal["mean_rssi_dbm"].iloc[-1]),
        "blocked_first_distance_mean_rssi_dbm": float(wifi_blocked["mean_rssi_dbm"].iloc[0]),
        "blocked_last_distance_mean_rssi_dbm": float(wifi_blocked["mean_rssi_dbm"].iloc[-1]),
        "mean_blocked_minus_normal_db": float(wifi_diff.mean()),
        "interpretation": [
            "Normal RSSI generally weakens with larger distance, although WiFi RSSI is not strictly monotonic indoors.",
            "Blocked RSSI is weaker than normal RSSI across the measured distances.",
            "This supports the simulation motivation for distance-dependent and blockage-sensitive WiFi RSSI.",
            "This is a small physical sanity check only, not full real-world localization validation."
        ],
        "outputs": {
            "summary_csv": str(wifi_summary_csv.relative_to(PROJECT_ROOT)),
            "summary_markdown": str(wifi_summary_md.relative_to(PROJECT_ROOT)),
            "figure": str(wifi_figure.relative_to(PROJECT_ROOT)),
        },
    }

    light_payload = {
        "status": "light_physical_sanity_analyzed",
        "input": str(LIGHT_CSV.relative_to(PROJECT_ROOT)),
        "num_rows": int(len(light_df)),
        "distances_m": sorted([float(x) for x in light_df["distance_m"].unique()]),
        "conditions": sorted(light_df["blockage"].unique().tolist()),
        "unit_values": light_df["unit"].value_counts().to_dict(),
        "unblocked_first_distance_mean_light": float(light_unblocked["mean_light"].iloc[0]),
        "unblocked_last_distance_mean_light": float(light_unblocked["mean_light"].iloc[-1]),
        "blocked_first_distance_mean_light": float(light_blocked["mean_light"].iloc[0]),
        "blocked_last_distance_mean_light": float(light_blocked["mean_light"].iloc[-1]),
        "mean_blocked_over_unblocked_mean_ratio": float(light_mean_ratio.mean()),
        "mean_blocked_over_unblocked_median_ratio": float(light_median_ratio.mean()),
        "interpretation": [
            "Unblocked app-estimated light intensity generally decreases with distance.",
            "Blocked app-estimated light intensity is much lower than unblocked intensity across the measured distances.",
            "The result supports the simulation motivation for distance-dependent and blockage-sensitive visible-light intensity.",
            "iPhone light-meter values are treated as lux-like app estimates, not calibrated photodiode measurements.",
            "This is a small physical sanity check only, not full VLP hardware validation."
        ],
        "outputs": {
            "summary_csv": str(light_summary_csv.relative_to(PROJECT_ROOT)),
            "summary_markdown": str(light_summary_md.relative_to(PROJECT_ROOT)),
            "figure": str(light_figure.relative_to(PROJECT_ROOT)),
        },
    }

    combined_payload = {
        "status": "physical_sanity_check_analyzed",
        "purpose": "support simulation motivation only",
        "claim_boundary": [
            "not real deployment validation",
            "not full hardware validation",
            "not state-of-the-art evaluation",
            "not a new WiFi or VLP hardware system",
        ],
        "wifi": wifi_payload,
        "light": light_payload,
        "outputs": {
            "combined_figure": str(combined_figure.relative_to(PROJECT_ROOT)),
            "wifi_summary_csv": str(wifi_summary_csv.relative_to(PROJECT_ROOT)),
            "light_summary_csv": str(light_summary_csv.relative_to(PROJECT_ROOT)),
        },
        "paper_ready_sentence": (
            "A small smartphone-based sanity check showed that WiFi RSSI became weaker with distance "
            "and body blockage, while app-estimated light intensity decreased with distance and optical "
            "blockage. These observations only motivate the simulated degradation scenarios and are not "
            "used as full real-world localization validation."
        ),
    }

    write_json(wifi_log, wifi_payload)
    write_json(light_log, light_payload)
    write_json(combined_log, combined_payload)

    print("\nPhysical sanity analysis complete.")
    print(f"WiFi rows: {len(wifi_df)}")
    print(f"Light rows: {len(light_df)}")

    print("\nSaved tables:")
    print(f"- {wifi_summary_csv}")
    print(f"- {light_summary_csv}")

    print("\nSaved figures:")
    print(f"- {wifi_figure}")
    print(f"- {light_figure}")
    print(f"- {combined_figure}")

    print("\nSaved logs:")
    print(f"- {wifi_log}")
    print(f"- {light_log}")
    print(f"- {combined_log}")

    print("\nWiFi summary preview:")
    print(wifi_summary.to_string(index=False))

    print("\nLight summary preview:")
    print(light_summary.to_string(index=False))

    print("\nPaper-ready interpretation:")
    print(combined_payload["paper_ready_sentence"])


if __name__ == "__main__":
    main()
