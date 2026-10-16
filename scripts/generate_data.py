"""Generate reproducible, explicitly synthetic BikeShare demonstration scenarios.

Standard library only. Run from the repository root: py scripts/generate_data.py
"""
import csv
import gzip
import hashlib
import io
import math
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
START = datetime(2026, 9, 7, tzinfo=timezone.utc)
PERIODS = 21 * 24 * 12
FIELDS = ["timestamp", "station_id", "station_name", "district", "latitude",
          "longitude", "total_docks", "broken_docks", "bikes", "broken_bikes",
          "service_status", "last_reported"]
ORDER_FIELDS = ["ticket_id", "station_id", "opened_at", "assigned_at",
                "resolved_at", "cause", "response_min"]
SCENARIOS = {"normal_week": (401, 0.35, 1),
             "high_failure_week": (402, 0.49, 3),
             "improvement_week": (403, 0.22, 0.55)}
DISTRICTS = ["Residential", "Downtown", "University", "Riverside"]


def stamp(value):
    return value.isoformat().replace("+00:00", "Z")


def stations():
    """Twenty invented stations and schematic coordinates; no real assets."""
    return [{"station_id": f"S{i + 1:02d}",
             "station_name": f"{DISTRICTS[i // 5]} {i % 5 + 1}",
             "district": DISTRICTS[i // 5],
             "latitude": round(42.44 + (i // 5) * 0.008 + (i % 5) * 0.001, 6),
             "longitude": round(-76.51 + (i % 5) * 0.007, 6),
             "total_docks": 10 + i % 11} for i in range(20)]


def episodes(rng, multiplier, station_index):
    """Nonoverlapping technical failures; S07 has deliberately more failures."""
    count = max(1, round(multiplier * (6 if station_index == 6 else 2)))
    result = []
    for number in range(count):
        # Separate bins prevent overlapping tickets and preserve interpretable times.
        width = PERIODS // count
        begin = number * width + rng.randrange(12, max(13, width - 150))
        length = rng.randrange(12, 73) if multiplier > 1 else rng.randrange(3, 19)
        cause = ["dock_fault", "bike_fault", "offline", "stale"][number % 4]
        result.append((begin, min(begin + length, PERIODS), cause))
    return result


def generate(name, seed, amplitude, multiplier):
    rng = random.Random(seed)
    metadata = stations()
    faults = {s["station_id"]: episodes(rng, multiplier, i)
              for i, s in enumerate(metadata)}
    folder = ROOT / "data" / name
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "snapshots.csv.gz"
    # Fix gzip metadata as well as random seed, so byte checksums reproduce.
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with io.TextIOWrapper(compressed, encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=FIELDS)
                writer.writeheader()
                for tick in range(PERIODS):
                    now = START + timedelta(minutes=5 * tick)
                    hour = now.hour + now.minute / 60
                    for index, station in enumerate(metadata):
                        row = dict(station)
                        row.update(timestamp=stamp(now), broken_docks=0,
                                   broken_bikes=0, service_status="operational",
                                   last_reported=stamp(now))
                        if now.weekday() < 5:
                            morning = math.exp(-((hour - 8) / 1.15) ** 2)
                            evening = math.exp(-((hour - 17) / 1.15) ** 2)
                            direction = [-1, 1, 0.65, -0.4][index // 5]
                            fill = 0.5 + amplitude * direction * (morning - evening)
                        else:
                            daylight = math.exp(-((hour - 14) / 3) ** 2)
                            fill = 0.5 + amplitude * [-0.5, -0.3, -0.2, 0.8][index // 5] * daylight
                        fill += rng.gauss(0, 0.085)
                        for begin, end, cause in faults[station["station_id"]]:
                            if begin <= tick < end:
                                if cause == "dock_fault":
                                    row["broken_docks"] = max(1, station["total_docks"] // 3)
                                elif cause == "bike_fault":
                                    row["broken_bikes"] = max(1, station["total_docks"] // 4)
                                elif cause == "offline":
                                    row["service_status"] = "offline"
                                else:
                                    row["last_reported"] = stamp(START + timedelta(minutes=5 * (begin - 1)))
                                break
                        capacity = station["total_docks"] - row["broken_docks"]
                        row["bikes"] = max(0, min(capacity - row["broken_bikes"],
                                                  round(capacity * fill)))
                        writer.writerow(row)
    orders = []
    for station in metadata:
        for begin, end, cause in faults[station["station_id"]]:
            opened = START + timedelta(minutes=begin * 5)
            resolved = START + timedelta(minutes=end * 5)
            delay = min((end - begin) * 5 - 5, 5 * rng.randrange(1, 5))
            orders.append(dict(ticket_id=f"{name[:3].upper()}-{len(orders)+1:04d}",
                               station_id=station["station_id"], opened_at=stamp(opened),
                               assigned_at=stamp(opened + timedelta(minutes=delay)),
                               resolved_at=stamp(resolved) if end < PERIODS else "",
                               cause=cause, response_min=delay))
    with (folder / "work_orders.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=ORDER_FIELDS)
        writer.writeheader()
        writer.writerows(orders)
    print(f"{name}: {PERIODS * 20:,} snapshots; {len(orders)} work orders; "
          f"sha256={hashlib.sha256(path.read_bytes()).hexdigest()}")


def validate():
    """Fail loudly on row counts, cadence, bounds, timestamps or ticket ordering."""
    for name in SCENARIOS:
        count, previous, seen = 0, {}, set()
        rush = {key: [] for key in ("Residential_am", "Downtown_am", "Residential_pm", "Downtown_pm")}
        with gzip.open(ROOT / "data" / name / "snapshots.csv.gz", "rt", newline="") as stream:
            for row in csv.DictReader(stream):
                sid = row["station_id"]
                now = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
                assert sid not in previous or now - previous[sid] == timedelta(minutes=5)
                previous[sid] = now
                seen.add(sid)
                total, broken, bikes, bad_bikes = [int(row[k]) for k in
                    ("total_docks", "broken_docks", "bikes", "broken_bikes")]
                assert 10 <= total <= 20 and min(broken, bikes, bad_bikes) >= 0
                assert bikes + bad_bikes <= total - broken
                assert row["last_reported"] <= row["timestamp"]
                if now.weekday() < 5 and row["district"] in ("Residential", "Downtown"):
                    period = "am" if 7 <= now.hour < 9 else "pm" if 16 <= now.hour < 18 else None
                    if period:
                        rush[row["district"] + "_" + period].append(bikes / total)
                count += 1
        assert count == PERIODS * 20 and len(seen) == 20
        means = {key: sum(values) / len(values) for key, values in rush.items()}
        assert means["Residential_am"] < means["Downtown_am"]
        assert means["Residential_pm"] > means["Downtown_pm"]
        with (ROOT / "data" / name / "work_orders.csv").open(newline="") as stream:
            for row in csv.DictReader(stream):
                assert row["opened_at"] <= row["assigned_at"]
                assert not row["resolved_at"] or row["assigned_at"] <= row["resolved_at"]
        print(f"PASS {name}: rows={count}, stations=20, cadence=5 min, bounds/times valid")
        print("  Rush-hour rentable fill: " + ", ".join(f"{k}={v:.3f}" for k, v in means.items()))


if __name__ == "__main__":
    for scenario, parameters in SCENARIOS.items():
        generate(scenario, *parameters)
    validate()
