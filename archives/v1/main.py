import asyncio
import json
from datetime import datetime, timezone
import websockets


BINANCE_WS = "wss://stream.binance.com:9443/ws"

def ms_to_str(ms: int) -> str:
    """Epoch milliseconds → YYYY-MM-DD HH:MM:SS (UTC)"""
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


async def subscribe(pair):
    uri = f"{BINANCE_WS}/{pair.lower()}@trade"

    async with websockets.connect(uri) as ws:
        async for msg in ws:
            data = json.loads(msg)

            record = {
                "symbol": pair,
                "time": ms_to_str(data["T"]),
                "price": float(data["p"]),
                "quantity": float(data["q"]),
            }

            # store or print
            print(record)


async def main():
    await asyncio.gather(
        subscribe("BTCUSDT"),
        subscribe("ETHUSDT"),
    )


if __name__ == "__main__":
    asyncio.run(main())
