import csv
from datetime import datetime, timedelta, timezone


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


def price_all_meters(forecast_csv: str) -> float:
    with open(forecast_csv) as f:
        rows = list(csv.DictReader(f))

    # grab first location - this is flawed assumption
    location = rows[0]["location"]

    # sum up volumes across all meters
    summed_volumes: dict[datetime, float] = {}
    for row in rows:
        ts = parse_timestamp(row["timestamp"])
        summed_volumes[ts] = summed_volumes.get(ts, 0.0) + float(row["usage_mw"])

    total_cost = 0.0
    for timestamp in summed_volumes:
        total_cost += summed_volumes[timestamp] * price(timestamp, location)

    return total_cost


if __name__ == "__main__":
    print(price_all_meters("forecast.csv"))
