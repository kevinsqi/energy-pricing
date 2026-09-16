import csv
from datetime import datetime, timedelta, timezone

from forecast import generate_forecast


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


def price_all_meters(meters_csv: str) -> list[dict]:
    with open(meters_csv) as f:
        meters = list(csv.DictReader(f))

    # pull the hourly usage forecast for every meter
    rows = []
    for meter in meters:
        rows.extend(
            generate_forecast(
                meter_id=int(meter["meter_id"]),
                location=meter["location"],
                start=parse_timestamp(meter["start_date"]),
                end=parse_timestamp(meter["end_date"]),
            )
        )

    results = []
    for meter in meters:
        meter_id = int(meter["meter_id"])
        location = meter["location"]

        # sum up this meter's volumes by hour
        summed_volumes: dict[datetime, float] = {}
        for row in rows:
            if row["meter_id"] != meter_id:
                continue
            ts = row["timestamp"]
            summed_volumes[ts] = summed_volumes.get(ts, 0.0) + row["usage_mw"]

        total_cost = 0.0
        total_volume = 0.0
        for timestamp in summed_volumes:
            total_cost += summed_volumes[timestamp] * price(timestamp, location)
            total_volume += summed_volumes[timestamp]

        results.append({"meter_id": meter_id, "price_per_mwh": total_cost / total_volume})

    return results


if __name__ == "__main__":
    print(price_all_meters("meters.csv"))
