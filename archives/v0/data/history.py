import requests
import time
from config.settings import BINANCE_REST_URL, TIMEFRAME, HISTORY_DAYS

INTERVAL_MAP = {
    "1m": 60_000,
    "5m": 300_000,
    "1h": 3_600_000,
}

def fetch_historical(symbol):
    limit = 1000
    interval_ms = INTERVAL_MAP[TIMEFRAME]
    end_time = int(time.time() * 1000)
    start_time = end_time - HISTORY_DAYS * 24 * 60 * 60 * 1000

    candles = []

    while start_time < end_time:
        params = {
            "symbol": symbol,
            "interval": TIMEFRAME,
            "startTime": start_time,
            "limit": limit,
        }
        r = requests.get(f"{BINANCE_REST_URL}/api/v3/klines", params=params)
        r.raise_for_status()

        data = r.json()
        if not data:
            break

        for k in data:
            candles.append({
                "time": k[0] // 1000,
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5]),
            })

        start_time = data[-1][0] + interval_ms

    return candles
