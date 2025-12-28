import asyncio
import json
from datetime import datetime, timezone, timedelta

import pandas as pd
import requests
import websockets
from fastapi import FastAPI, WebSocket, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

# ---------------- CONFIG ---------------- #

BINANCE_WS = "wss://stream.binance.com:9443/ws"
BINANCE_REST = "https://api.binance.com"

SYMBOL = "BTCUSDT"
TIMEFRAME = "1m"   # 1m, 5m, 1h
DAYS = 1

INTERVAL_MS = {
    "1m": 60_000,
    "5m": 300_000,
    "1h": 3_600_000,
}

# ---------------- APP ---------------- #

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

clients: set[WebSocket] = set()

# ---------------- HELPERS ---------------- #

def floor_time(ts: pd.Timestamp, tf: str):
    if tf.endswith("m"):
        return ts.floor(f"{tf[:-1]}min")
    if tf.endswith("h"):
        return ts.floor(f"{tf[:-1]}H")
    raise ValueError(tf)

def save_csv(df: pd.DataFrame):
    df.sort_index().to_csv(f"{SYMBOL}.csv")

def load_csv_to_candles(file_bytes: bytes):
    from io import BytesIO

    df = pd.read_csv(BytesIO(file_bytes))

    # handle index-based CSV
    if "time" not in df.columns:
        df.reset_index(inplace=True)
        df.rename(columns={df.columns[0]: "time"}, inplace=True)

    # normalize time
    if not isinstance(df["time"].iloc[0], (int, float)):
        df["time"] = pd.to_datetime(df["time"]).astype("int64") // 1_000_000_000

    candles = df[["time", "open", "high", "low", "close", "volume"]]
    return candles.to_dict("records")


async def broadcast(candle: dict):
    dead = set()
    for ws in clients:
        try:
            await ws.send_text(json.dumps(candle))
        except:
            dead.add(ws)
    clients.difference_update(dead)

# ---------------- DATA ---------------- #

def fetch_historical():
    end = datetime.now(tz=timezone.utc)
    start = end - timedelta(days=DAYS)

    start_ms = int(start.timestamp() * 1000)
    candles = []

    while True:
        r = requests.get(
            f"{BINANCE_REST}/api/v3/klines",
            params={
                "symbol": SYMBOL,
                "interval": TIMEFRAME,
                "startTime": start_ms,
                "limit": 1000,
            },
            timeout=10,
        )
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

        start_ms = data[-1][0] + INTERVAL_MS[TIMEFRAME]

    return candles

# ---------------- STREAM ---------------- #

async def stream_trades():
    uri = f"{BINANCE_WS}/{SYMBOL.lower()}@trade"

    df = pd.DataFrame(
        fetch_historical()
    ).set_index("time")

    last_candle = df.index[-1]

    async with websockets.connect(uri) as ws:
        async for msg in ws:
            t = json.loads(msg)
            price = float(t["p"])
            qty = float(t["q"])

            trade_time = pd.to_datetime(
                t["T"], unit="ms", utc=True
            ).tz_convert(None)

            candle_time = int(
                floor_time(trade_time, TIMEFRAME).timestamp()
            )

            if candle_time in df.index:
                row = df.loc[candle_time]
                df.loc[candle_time, "high"] = max(row.high, price)
                df.loc[candle_time, "low"] = min(row.low, price)
                df.loc[candle_time, "close"] = price
                df.loc[candle_time, "volume"] += qty
            else:
                df.loc[candle_time] = {
                    "open": price,
                    "high": price,
                    "low": price,
                    "close": price,
                    "volume": qty,
                }

            candle = {
                "time": candle_time,
                **df.loc[candle_time].to_dict(),
            }

            await broadcast(candle)

            # candle closed
            if candle_time != last_candle:
                save_csv(df)
                last_candle = candle_time

# ---------------- ENDPOINTS ---------------- # 

@app.post("/load-csv")
async def load_csv(file: UploadFile = File(...)):
    content = await file.read()
    candles = load_csv_to_candles(content)
    return candles

# ---------------- WS ---------------- #

@app.websocket("/ws/candles")
async def candle_ws(ws: WebSocket):
    await ws.accept()
    clients.add(ws)
    try:
        while True:
            await ws.receive_text()
    except:
        clients.remove(ws)

# ---------------- START ---------------- #

@app.on_event("startup")
async def startup():
    asyncio.create_task(stream_trades())
