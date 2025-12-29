from fastapi import APIRouter
from config.settings import SYMBOLS


router = APIRouter()

@router.get("/candles/{symbol}")
def get_candles(symbol: str, app=None):
    if symbol not in SYMBOLS:
        return []
    return app.state.candle_store.get_candles(symbol)

@router.post("/trade")
def trade(order: dict, app=None):
    engine = app.state.trading
    price = app.state.candle_store.last_price(order["symbol"])

    if order["side"] == "BUY":
        engine.buy(order["symbol"], price, order["qty"])
    else:
        engine.sell(order["symbol"], price, order["qty"])

    return {"status": "ok"}
