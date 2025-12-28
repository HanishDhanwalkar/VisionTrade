import requests
from datetime import datetime, timedelta, timezone

BINANCE_REST_URL = "https://api.binance.com"

INTERVAL_MAP = {
    "1m": 60_000,
    "5m": 300_000,
    "1h": 3_600_000,
}


def ms_to_str(ms: int) -> str:
    """Convert epoch milliseconds → human-readable UTC string"""
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def fetch_historical(symbol, timeframe="1m", days=1):
    limit = 1000
    interval_ms = INTERVAL_MAP[timeframe]

    # --- Time boundaries (UTC, correct for Binance) ---
    end_dt = datetime.now(tz=timezone.utc)
    start_dt = end_dt - timedelta(days=int(days))

    end_time_ms = int(end_dt.timestamp() * 1000)
    start_time_ms = int(start_dt.timestamp() * 1000)

    print(f"Fetching from {start_dt.strftime('%Y-%m-%d %H:%M:%S')} UTC "
          f"to {end_dt.strftime('%Y-%m-%d %H:%M:%S')} UTC")

    candles = []

    while start_time_ms < end_time_ms:
        params = {
            "symbol": symbol,
            "interval": timeframe,
            "startTime": start_time_ms,
            "limit": limit,
        }

        r = requests.get(
            f"{BINANCE_REST_URL}/api/v3/klines",
            params=params,
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()

        if not data:
            break

        for k in data:
            candles.append({
                "time": ms_to_str(k[0]),   # 👈 human-readable
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5]),
            })

        # move forward exactly one candle
        start_time_ms = data[-1][0] + interval_ms

    return candles


if __name__ == "__main__":
    data = fetch_historical("BTCUSDT", timeframe="1m", days=1)
    print(data[:2])
