import asyncio
from fastapi import FastAPI
from config.settings import SYMBOLS, INITIAL_BALANCE

from data.candle_store import CandleStore
from data.history import fetch_historical
from data.realtime import stream_candles

from portpolio.paper import PaperTradingEngine

from api.routes import router
from api.websockets import ws_endpoint, broadcast

app = FastAPI()

@app.on_event("startup")
async def startup():
    app.state.candle_store = CandleStore()
    app.state.trading = PaperTradingEngine(INITIAL_BALANCE)

    for s in SYMBOLS:
        candles = fetch_historical(s)
        app.state.candle_store.load_history(s, candles)

    asyncio.create_task(stream_candles(app.state.candle_store, broadcast))

app.include_router(router)

@app.websocket("/ws")
async def websocket(ws):
    await ws_endpoint(ws)
