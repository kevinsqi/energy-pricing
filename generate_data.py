"""Synthetic data generation for the energy pricing coding interview.

Produces two CSVs of hourly, hour-beginning UTC timestamps (end times exclusive):
  - forecast.csv: hourly usage forecasts for 3 commercial meters
  - prices.csv:   hourly settlement-point prices for 3 ERCOT hubs

All values are deterministic functions of (meter_id, location, timestamp), so
repeated runs produce identical files.
"""

import csv
import hashlib
import math
from datetime import datetime, timedelta, timezone

UTC = timezone.utc

METERS = [
    {
        "meter_id": 1,
        "location": "HB_WEST",
        "start": datetime(2027, 1, 1, 0, tzinfo=UTC),
        "end": datetime(2027, 1, 4, 5, tzinfo=UTC),
    },
    {
        "meter_id": 2,
        "location": "HB_NORTH",
        "start": datetime(2027, 1, 1, 12, tzinfo=UTC),
        "end": datetime(2027, 1, 4, 0, tzinfo=UTC),
    },
    {
        "meter_id": 3,
        "location": "HB_SOUTH",
        "start": datetime(2027, 1, 1, 14, tzinfo=UTC),
        "end": datetime(2027, 1, 5, 0, tzinfo=UTC),
    },
]

PRICE_START = datetime(2027, 1, 1, 0, tzinfo=UTC)
PRICE_END = datetime(2027, 1, 10, 0, tzinfo=UTC)
PRICE_LOCATIONS = ["HB_WEST", "HB_NORTH", "HB_SOUTH"]


def _unit_noise(*parts) -> float:
    """Deterministic pseudo-random float in [0, 1) derived from the inputs."""
    key = "|".join(str(p) for p in parts).encode()
    digest = hashlib.sha256(key).digest()
    return int.from_bytes(digest[:8], "big") / 2**64


def _hourly_range(start: datetime, end: datetime):
    ts = start
    while ts < end:
        yield ts
        ts += timedelta(hours=1)


def _local_hour(ts: datetime) -> int:
    # ERCOT hubs are US Central time, UTC-6 in January (CST).
    return (ts.hour - 6) % 24


def usage_mw(meter_id: int, location: str, ts: datetime) -> float:
    """Hourly usage for a commercial business: overnight floor with a
    business-hours peak, reduced on weekends."""
    hour = _local_hour(ts)

    # Per-meter characteristics, stable across runs.
    base = 0.25 + 0.35 * _unit_noise("meter-base", meter_id, location)
    peak = base * (2.5 + 1.5 * _unit_noise("meter-peak", meter_id, location))

    # Occupancy bump centered on the local workday (~7am ramp-up, ~7pm ramp-down).
    workday = math.exp(-(((hour - 13) / 4.5) ** 2))
    if ts.weekday() >= 5:
        workday *= 0.35

    usage = base + (peak - base) * workday
    # Small hour-to-hour wobble so the series isn't perfectly smooth.
    usage *= 1 + 0.06 * (_unit_noise("usage-wobble", meter_id, ts.isoformat()) - 0.5)
    return round(usage, 4)


def price_per_mwh(location: str, ts: datetime) -> float:
    """Hourly hub price, ballpark ERCOT: ~$20-35 off-peak with morning and
    evening peaks and the occasional scarcity spike."""
    hour = _local_hour(ts)

    base = {"HB_WEST": 22.0, "HB_NORTH": 27.0, "HB_SOUTH": 29.0}[location]

    morning_peak = 9.0 * math.exp(-(((hour - 7.5) / 1.5) ** 2))
    evening_peak = 20.0 * math.exp(-(((hour - 18.0) / 2.0) ** 2))
    if ts.weekday() >= 5:
        morning_peak *= 0.5
        evening_peak *= 0.6

    price = base + morning_peak + evening_peak
    price *= 1 + 0.20 * (_unit_noise("price-wobble", location, ts.isoformat()) - 0.5)

    # Rare scarcity spikes during evening peak hours.
    if 16 <= hour <= 20 and _unit_noise("price-spike", location, ts.date()) > 0.85:
        price *= 4.0

    return round(price, 2)


def generate_forecast(path: str = "forecast.csv") -> int:
    rows = []
    for meter in METERS:
        for ts in _hourly_range(meter["start"], meter["end"]):
            rows.append(
                {
                    "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "location": meter["location"],
                    "usage_mw": usage_mw(meter["meter_id"], meter["location"], ts),
                }
            )
    rows.sort(key=lambda r: (r["timestamp"], r["location"]))
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp", "location", "usage_mw"])
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def generate_prices(path: str = "prices.csv") -> int:
    rows = []
    for ts in _hourly_range(PRICE_START, PRICE_END):
        for location in PRICE_LOCATIONS:
            rows.append(
                {
                    "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "location": location,
                    "price_per_mwh": price_per_mwh(location, ts),
                }
            )
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp", "location", "price_per_mwh"])
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


if __name__ == "__main__":
    n_forecast = generate_forecast()
    n_prices = generate_prices()
    print(f"forecast.csv: {n_forecast} rows")
    print(f"prices.csv: {n_prices} rows")
