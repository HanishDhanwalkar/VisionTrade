from fastapi import WebSocket
import json

clients = set()

async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    clients.add(ws)
    try:
        while True:
            await ws.receive_text()
    finally:
        clients.remove(ws)

async def broadcast(symbol, candle):
    msg = json.dumps({"type": "candle", "symbol": symbol, "data": candle})
    for c in clients:
        await c.send_text(msg)
