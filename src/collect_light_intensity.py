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
    "light_value",
    "unit",
    "notes",
]

DEFAULT_DISTANCES = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
DEFAULT_CONDITIONS = ["unblocked", "blocked"]


def parse_distances(text: str):
    if not text.strip():
        return DEFAULT_DISTANCES
    values = []
    for item in text.split(","):
        item = item.strip()
        if item:
            values.append(float(item))
    return values


def write_header(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()


def ensure_csv(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        write_header(path)


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


def append_row(path: Path, row: dict):
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writerow(row)


def print_collection_instruction(condition: str):
    print("\n" + "=" * 78)
    print(f"NOW COLLECTING CONDITION: {condition.upper()}")
    print("=" * 78)
    if condition == "unblocked":
        print("Keep the phone/app exposed to the LED room light.")
        print("Do NOT intentionally block the light path.")
    else:
        print("Partially block the light path using your hand/body/object.")
        print("Use the same blockage style for all blocked readings.")
        print("Do not fully cover the camera/sensor unless you intentionally want complete blockage.")
    print("=" * 78)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        default="results/physical/light_intensity_measurements.csv",
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

    print("\nLight Intensity Collection Helper")
    print("- Use Light Meter LM-3000 or another numeric light meter app")
    print("- Type only the numeric light value shown by the app, e.g., 120 or 325.5")
    print("- Type q to quit safely")
    print("- Type s to skip a sample")
    print("- Recommended unit for iPhone app readings: lux_app_estimate")

    device = input("\nEnter iPhone model/device label [default: iPhone 17]: ").strip()
    if not device:
        device = "iPhone 17"

    app_name = input("Enter app name [default: Light Meter LM-3000]: ").strip()
    if not app_name:
        app_name = "Light Meter LM-3000"

    light_source = input("Enter light source [default: LED room light]: ").strip()
    if not light_source:
        light_source = "LED room light"

    unit = input("Enter unit [default: lux_app_estimate]: ").strip()
    if not unit:
        unit = "lux_app_estimate"

    distance_text = input(
        "Enter distances in meters separated by comma, or press Enter for 1,2,3,4,5,6: "
    )
    distances = parse_distances(distance_text)

    samples_text = input("Samples per distance per condition? Press Enter for 10: ").strip()
    samples_per_distance = int(samples_text) if samples_text else 10

    print("\nFinal collection plan:")
    print(f"Device: {device}")
    print(f"App: {app_name}")
    print(f"Light source: {light_source}")
    print(f"Unit: {unit}")
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

    print("\nIMPORTANT MEASUREMENT RULES")
    print("- Keep the LED room light fixed.")
    print("- Keep phone orientation as consistent as possible.")
    print("- If using the camera-facing method, point the phone/app toward the light consistently.")
    print("- Stand still while reading each sample.")
    print("- Wait about 2 seconds between samples.")
    print("- Record the value honestly even if repeated.")

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
            print("Wait 5 seconds for the light app value to stabilize.")
            print("Then enter the light readings one by one.")
            print("-" * 78)

            input(f"Press Enter when you are standing at {distance_m} m and ready...")

            collected_here = 0
            rep = 1

            while rep <= samples_per_distance:
                value = input(
                    f"{condition} | {position_id} | {distance_m} m | sample {rep}/{samples_per_distance} | light value: "
                ).strip()

                if value.lower() == "q":
                    print("Quit requested. Data saved up to this point.")
                    return

                if value.lower() == "s":
                    print("Skipped this sample.")
                    rep += 1
                    continue

                try:
                    light_value = float(value)
                except ValueError:
                    print("Invalid value. Type a number like 120 or 325.5, or q to quit.")
                    continue

                if light_value < 0:
                    confirm = input(
                        "Light value is negative. Save anyway? yes/no: "
                    ).strip().lower()
                    if confirm != "yes":
                        continue

                row = {
                    "sample_id": sample_id,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "device": device,
                    "scenario": "light_physical_sanity",
                    "distance_m": distance_m,
                    "position_id": position_id,
                    "blockage": condition,
                    "light_value": light_value,
                    "unit": unit,
                    "notes": f"app={app_name}; source={light_source}; rep={rep}",
                }

                append_row(out_path, row)

                print(f"Saved sample_id={sample_id}, light_value={light_value}")
                sample_id += 1
                rep += 1
                collected_here += 1

            print(f"Completed {collected_here} readings for {position_id}, {condition}.")

    print("\nDone. Light intensity collection completed.")
    print(f"Saved to: {out_path}")


if __name__ == "__main__":
    main()
