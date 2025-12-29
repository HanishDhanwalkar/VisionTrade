import asyncio, json
import websockets

BINANCE_WS = "wss://stream.binance.com:9443/ws"

async def subscribe(pair):
    uri = f"{BINANCE_WS}/{pair.lower()}@trade"
    async with websockets.connect(uri) as ws:
        while True:
            msg = await ws.recv()
            data = json.loads(msg)
            price = float(data["p"])
            # store or print
            print(pair, price)

async def main():
    await asyncio.gather(
        subscribe("BTCUSDT"),
        subscribe("ETHUSDT")
    )

if __name__ == "__main__":
    asyncio.run(main())
