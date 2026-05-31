from pathlib import Path
from datetime import datetime
import argparse
import csv
import shutil

FIELDNAMES = [
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

DEFAULT_DISTANCES = [0.5, 1.0, 2.0, 3.0, 4.0, 5.0]
DEFAULT_CONDITIONS = ["normal", "blocked"]


def parse_distances(text: str):
    if not text.strip():
        return DEFAULT_DISTANCES
    values = []
    for item in text.split(","):
        item = item.strip()
        if item:
            values.append(float(item))
    return values


def ensure_csv(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()


def read_existing_rows(path: Path):
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def next_sample_id(path: Path):
    rows = read_existing_rows(path)
    ids = []
    for row in rows:
        try:
            ids.append(int(row.get("sample_id", "")))
        except ValueError:
            pass
    return max(ids, default=0) + 1


def write_header(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()


def append_row(path: Path, row: dict):
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writerow(row)


def print_collection_instruction(condition: str):
    print("\n" + "=" * 78)
    print(f"NOW COLLECTING CONDITION: {condition.upper()}")
    print("=" * 78)
    if condition == "normal":
        print("Keep phone normally exposed to the router/hotspot.")
        print("Do NOT block the path intentionally.")
    else:
        print("Put your body/hand/object between phone and router/hotspot.")
        print("Keep the blockage style as similar as possible for all blocked readings.")
    print("=" * 78)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        default="results/physical/wifi_rssi_measurements.csv",
        help="Output CSV path",
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Start a fresh CSV. Existing file will be backed up.",
    )
    args = parser.parse_args()

    out_path = Path(args.out)

    if args.fresh and out_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = out_path.with_name(out_path.stem + f"_backup_{timestamp}" + out_path.suffix)
        shutil.copy2(out_path, backup)
        print(f"Existing CSV backed up to: {backup}")
        write_header(out_path)
    else:
        ensure_csv(out_path)

    print("\nWiFi RSSI Collection Helper")
    print("- Type only RSSI number, e.g., -45")
    print("- Type q to quit safely")
    print("- Type s to skip a sample")
    print("- RSSI should usually be a negative number in dBm")

    device = input("\nEnter iPhone model/device label, e.g., iPhone 13: ").strip()
    if not device:
        device = "iPhone"

    ssid = input("Enter WiFi/router/hotspot label, e.g., HomeRouter: ").strip()
    if not ssid:
        ssid = "wifi_source"

    distance_text = input(
        "Enter distances in meters separated by comma, or press Enter for 0.5,1,2,3,4,5: "
    )
    distances = parse_distances(distance_text)

    samples_text = input("Samples per distance per condition? Press Enter for 10: ").strip()
    samples_per_distance = int(samples_text) if samples_text else 10

    print("\nFinal collection plan:")
    print(f"Device: {device}")
    print(f"WiFi label: {ssid}")
    print(f"Distances: {distances}")
    print(f"Conditions: {DEFAULT_CONDITIONS}")
    print(f"Samples per distance per condition: {samples_per_distance}")
    print(f"Output: {out_path}")
    print(f"Total expected rows: {len(distances) * len(DEFAULT_CONDITIONS) * samples_per_distance}")

    start = input("\nStart collection now? Type yes to continue: ").strip().lower()
    if start != "yes":
        print("Stopped before collection.")
        return

    sample_id = next_sample_id(out_path)

    for condition in DEFAULT_CONDITIONS:
        print_collection_instruction(condition)

        ready = input(f"\nReady to start {condition} readings? Type yes: ").strip().lower()
        if ready != "yes":
            print(f"Skipping condition: {condition}")
            continue

        for idx, distance_m in enumerate(distances, start=1):
            position_id = f"P{idx}"
            print("\n" + "-" * 78)
            print(f"Move to {position_id}: distance = {distance_m} m, condition = {condition}")
            print("Wait 5-10 seconds for the AirPort Utility RSSI value to stabilize.")
            print("Then enter the RSSI readings one by one.")
            print("-" * 78)

            input(f"Press Enter when you are standing at {distance_m} m and ready...")

            collected_here = 0
            rep = 1
            while rep <= samples_per_distance:
                value = input(
                    f"{condition} | {position_id} | {distance_m} m | sample {rep}/{samples_per_distance} | RSSI dBm: "
                ).strip()

                if value.lower() == "q":
                    print("Quit requested. Data saved up to this point.")
                    return

                if value.lower() == "s":
                    print("Skipped this sample.")
                    rep += 1
                    continue

                try:
                    rssi = float(value)
                except ValueError:
                    print("Invalid value. Type a number like -45, or q to quit.")
                    continue

                if rssi > 0:
                    confirm = input(
                        "RSSI is usually negative. You entered positive. Save anyway? yes/no: "
                    ).strip().lower()
                    if confirm != "yes":
                        continue

                row = {
                    "sample_id": sample_id,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "device": device,
                    "scenario": "wifi_physical_sanity",
                    "distance_m": distance_m,
                    "position_id": position_id,
                    "blockage": condition,
                    "rssi_dbm": rssi,
                    "notes": f"ssid={ssid}; rep={rep}",
                }
                append_row(out_path, row)

                print(f"Saved sample_id={sample_id}, rssi_dbm={rssi}")
                sample_id += 1
                rep += 1
                collected_here += 1

            print(f"Completed {collected_here} readings for {position_id}, {condition}.")

    print("\nDone. WiFi RSSI collection completed.")
    print(f"Saved to: {out_path}")


if __name__ == "__main__":
    main()
