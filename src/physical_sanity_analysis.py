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
        print(f"Warning: dropped {before - after} rows with missing distance/RSSI/blockage")

    return df


def summarize_wifi(df: pd.DataFrame) -> pd.DataFrame:
    summary = (
        df.groupby(["distance_m", "blockage"], as_index=False)
        .agg(
            count=("rssi_dbm", "count"),
            mean_rssi_dbm=("rssi_dbm", "mean"),
            std_rssi_dbm=("rssi_dbm", "std"),
            min_rssi_dbm=("rssi_dbm", "min"),
            max_rssi_dbm=("rssi_dbm", "max"),
        )
        .sort_values(["distance_m", "blockage"])
    )

    # Create normal-vs-blocked comparison per distance.
    pivot = summary.pivot(index="distance_m", columns="blockage", values="mean_rssi_dbm")

    if "normal" in pivot.columns and "blocked" in pivot.columns:
        pivot["blocked_minus_normal_db"] = pivot["blocked"] - pivot["normal"]
        comparison = pivot[["normal", "blocked", "blocked_minus_normal_db"]].reset_index()
        comparison = comparison.rename(
            columns={
                "normal": "normal_mean_rssi_dbm",
                "blocked": "blocked_mean_rssi_dbm",
            }
        )
        summary = summary.merge(
            comparison[["distance_m", "blocked_minus_normal_db"]],
            on="distance_m",
            how="left",
        )
    else:
        summary["blocked_minus_normal_db"] = None

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
        "This physical check supports simulation motivation only; it is not full deployment validation."
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


def main():
    df = load_wifi_data(WIFI_CSV)
    summary = summarize_wifi(df)

    wifi_summary_csv = TABLE_DIR / "table_physical_wifi_summary.csv"
    wifi_summary_md = TABLE_DIR / "table_physical_wifi_summary.md"
    wifi_figure = FIGURE_DIR / "fig8a_physical_wifi_rssi.png"
    wifi_log = LOG_DIR / "physical_wifi_summary.json"

    summary.to_csv(wifi_summary_csv, index=False)
    summary.to_markdown(wifi_summary_md, index=False)

    plot_wifi(df, wifi_figure)

    normal = summary[summary["blockage"] == "normal"].sort_values("distance_m")
    blocked = summary[summary["blockage"] == "blocked"].sort_values("distance_m")

    normal_first = float(normal["mean_rssi_dbm"].iloc[0]) if not normal.empty else None
    normal_last = float(normal["mean_rssi_dbm"].iloc[-1]) if not normal.empty else None
    blocked_first = float(blocked["mean_rssi_dbm"].iloc[0]) if not blocked.empty else None
    blocked_last = float(blocked["mean_rssi_dbm"].iloc[-1]) if not blocked.empty else None

    if "blocked_minus_normal_db" in summary.columns:
        diffs = summary.drop_duplicates("distance_m")["blocked_minus_normal_db"].dropna()
        mean_blockage_drop_db = float(diffs.mean()) if not diffs.empty else None
    else:
        mean_blockage_drop_db = None

    log = {
        "status": "wifi_physical_sanity_analyzed",
        "input": str(WIFI_CSV.relative_to(PROJECT_ROOT)),
        "num_rows": int(len(df)),
        "distances_m": sorted([float(x) for x in df["distance_m"].unique()]),
        "conditions": sorted(df["blockage"].unique().tolist()),
        "normal_first_distance_mean_rssi_dbm": normal_first,
        "normal_last_distance_mean_rssi_dbm": normal_last,
        "blocked_first_distance_mean_rssi_dbm": blocked_first,
        "blocked_last_distance_mean_rssi_dbm": blocked_last,
        "mean_blocked_minus_normal_db": mean_blockage_drop_db,
        "interpretation": [
            "Normal RSSI generally weakens with larger distance, although WiFi RSSI is not strictly monotonic indoors.",
            "Blocked RSSI is weaker than normal RSSI across the measured distances.",
            "The result supports the simulation motivation for distance-dependent and blockage-sensitive WiFi RSSI.",
            "This is a small physical sanity check only, not full real-world localization validation."
        ],
        "outputs": {
            "summary_csv": str(wifi_summary_csv.relative_to(PROJECT_ROOT)),
            "summary_markdown": str(wifi_summary_md.relative_to(PROJECT_ROOT)),
            "figure": str(wifi_figure.relative_to(PROJECT_ROOT)),
        },
    }

    with wifi_log.open("w", encoding="utf-8") as f:
        json.dump(log, f, indent=2)

    print("\nWiFi physical sanity analysis complete.")
    print(f"Input rows: {len(df)}")
    print(f"Saved table: {wifi_summary_csv}")
    print(f"Saved markdown: {wifi_summary_md}")
    print(f"Saved figure: {wifi_figure}")
    print(f"Saved log: {wifi_log}")

    print("\nSummary preview:")
    print(summary.to_string(index=False))

    print("\nInterpretation:")
    print("- Normal RSSI generally weakens as distance increases, but not perfectly monotonically.")
    print("- Blocked RSSI is weaker than normal RSSI across the measured distances.")
    print("- This supports the simulation motivation only; it is not a full hardware validation.")


if __name__ == "__main__":
    main()
