# Working code for: real-time candlestick chart. No cache, matplotlib-mplfinance charts. Not scalble

import asyncio
import json
from datetime import datetime, timedelta, timezone

import websockets
import requests
import pandas as pd

import matplotlib.pyplot as plt
import mplfinance as mpf


BINANCE_WS = "wss://stream.binance.com:9443/ws"
BINANCE_REST_URL = "https://api.binance.com"

plt.ion()


# ---------------- TIME UTILITIES ---------------- #

INTERVAL_MAP = {
    "1m": 60_000,
    "5m": 300_000,
    "1h": 3_600_000,
}

# ----------------- HELPERS ---------------------- #
def save_csv(df: pd.DataFrame, symbol):
    df.sort_index(inplace=True)
    df.to_csv(f"{symbol}.csv")


def floor_time(ts: pd.Timestamp, timeframe: str) -> pd.Timestamp:
    if timeframe.endswith("m"):
        return ts.floor(f"{int(timeframe[:-1])}T")
    if timeframe.endswith("h"):
        return ts.floor(f"{int(timeframe[:-1])}H")
    raise ValueError(f"Unsupported timeframe: {timeframe}")


def ms_to_str(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


# ---------------- DATA ---------------- #

def update_candle(df, trade_time, price, qty, timeframe):
    candle_time = floor_time(trade_time, timeframe)

    if candle_time in df.index:
        row = df.loc[candle_time]
        df.loc[candle_time, "high"] = max(row["high"], price)
        df.loc[candle_time, "low"] = min(row["low"], price)
        df.loc[candle_time, "close"] = price
        df.loc[candle_time, "volume"] += qty
    else:
        df.loc[candle_time] = [price, price, price, price, qty]


def fetch_historical(symbol, timeframe="1m", days=1):
    limit = 1000
    interval_ms = INTERVAL_MAP[timeframe]

    end_dt = datetime.now(tz=timezone.utc)
    start_dt = end_dt - timedelta(days=int(days))

    start_time_ms = int(start_dt.timestamp() * 1000)
    end_time_ms = int(end_dt.timestamp() * 1000)

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
                "time": ms_to_str(k[0]),
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5]),
            })

        start_time_ms = data[-1][0] + interval_ms

    return candles


# ---------------- REALTIME ---------------- #

async def stream_and_plot(symbol, df, timeframe):
    uri = f"{BINANCE_WS}/{symbol.lower()}@trade"

    fig, ax = plt.subplots(figsize=(10, 6))
    last_draw = datetime.now()
    last_saved_candle = df.index[-1]  # 👈 track candle close

    async with websockets.connect(uri) as ws:
        async for msg in ws:
            data = json.loads(msg)

            trade_time = pd.to_datetime(
                data["T"], unit="ms", utc=True
            ).tz_convert(None)

            price = float(data["p"])
            qty = float(data["q"])

            update_candle(df, trade_time, price, qty, timeframe)

            # ---------------- SAVE CSV ON CANDLE CLOSE ----------------
            current_last_candle = df.index[-1]

            if current_last_candle != last_saved_candle:
                save_csv(df, symbol)
                last_saved_candle = current_last_candle

            # ---------------- THROTTLED REDRAW ----------------
            if (datetime.now() - last_draw).total_seconds() < 1:
                continue

            last_draw = datetime.now()

            ax.clear()
            mpf.plot(
                df.tail(200),
                type="candle",
                ax=ax,
                style="yahoo",
                volume=False,
                show_nontrading=True,
            )

            plt.pause(0.01)


def show_realtime_candlestick(symbol, timeframe="1m", days=1):
    if timeframe not in INTERVAL_MAP:
        raise ValueError(f"Invalid timeframe: {timeframe}")

    data = fetch_historical(symbol, timeframe, days)

    df = pd.DataFrame(data)
    df.set_index("time", inplace=True)
    df.index = pd.to_datetime(df.index, format="%Y-%m-%d %H:%M:%S")

    asyncio.run(stream_and_plot(symbol, df, timeframe))


# ---------------- RUN ---------------- #

if __name__ == "__main__":
    show_realtime_candlestick("BTCUSDT", timeframe="1m", days=1)
