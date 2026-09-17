import csv
from datetime import datetime, timedelta, timezone

from forecast import generate_forecast

METERS_CSV = "meters.csv"


def parse_timestamp(raw: str) -> datetime:
    return datetime.strptime(raw, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def price(timestamp: datetime, location: str) -> float:
    prices = fetch_energy_market_data(location, timestamp, timestamp + timedelta(hours=1))

    return prices[timestamp]


def fetch_energy_market_data(
    location: str, start_time: datetime, end_time: datetime
) -> dict[datetime, float]:
    timeseries = {}
    with open("prices.csv") as f:
        for row in csv.DictReader(f):
            ts = parse_timestamp(row["timestamp"])
            if row["location"] == location and start_time <= ts < end_time:
                timeseries[ts] = float(row["price_per_mwh"])

    return timeseries


def load_meter(meter_id: int) -> dict:
    with open(METERS_CSV) as f:
        for row in csv.DictReader(f):
            if int(row["meter_id"]) == meter_id:
                return row

    raise ValueError(f"no meter with id {meter_id}")


def meter_ids() -> list[int]:
    with open(METERS_CSV) as f:
        return [int(row["meter_id"]) for row in csv.DictReader(f)]


def price_meter(meter_id: int) -> float:
    """Price of energy ($/MWh) for a single meter over its whole time range."""
    meter = load_meter(meter_id)
    location = meter["location"]

    forecast = generate_forecast(
        meter_id=meter_id,
        location=location,
        start=parse_timestamp(meter["start_date"]),
        end=parse_timestamp(meter["end_date"]),
    )

    total_cost = 0.0
    total_volume = 0.0
    for row in forecast:
        total_cost += row["usage_mw"] * price(row["timestamp"], location)
        total_volume += row["usage_mw"]

    return total_cost / total_volume


if __name__ == "__main__":
    print([{"meter_id": mid, "price_per_mwh": price_meter(mid)} for mid in meter_ids()])
