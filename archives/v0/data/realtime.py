import asyncio
import json
import websockets
from config.settings import BINANCE_WS_URL, SYMBOLS, TIMEFRAME

def build_stream_url():
    streams = [
        f"{s.lower()}@kline_{TIMEFRAME}" for s in SYMBOLS
    ]
    return f"{BINANCE_WS_URL}?streams={'/'.join(streams)}"

async def stream_candles(candle_store, broadcast):
    url = build_stream_url()
    async with websockets.connect(url) as ws:
        async for msg in ws:
            payload = json.loads(msg)
            k = payload["data"]["k"]

            candle = {
                "time": k["t"] // 1000,
                "open": float(k["o"]),
                "high": float(k["h"]),
                "low": float(k["l"]),
                "close": float(k["c"]),
                "volume": float(k["v"]),
            }

            symbol = k["s"]
            candle_store.update_candle(symbol, candle)
            await broadcast(symbol, candle)
