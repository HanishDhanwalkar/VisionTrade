import asyncio
import json
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from typing import Dict, Set

import websockets
from fastapi import FastAPI, WebSocket, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import aiohttp

# ---------------- CONFIG ---------------- #

BINANCE_WS = "wss://stream.binance.com:9443/ws"
BINANCE_REST = "https://api.binance.com"

SYMBOL = "BTCUSDT"
TIMEFRAME = "1m"
DAYS = 1

INTERVAL_MS = {
    "1m": 60_000,
    "5m": 300_000,
    "1h": 3_600_000,
}

# Optimization settings
BROADCAST_INTERVAL = 0.1  # seconds - batch updates every 100ms
MAX_CANDLES_IN_MEMORY = 10000  # limit memory usage

# ---------------- APP ---------------- #

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- IN-MEMORY DATA STRUCTURES ---------------- #

class CandleStore:
    """Fast in-memory candle storage with O(1) lookups"""
    
    def __init__(self):
        self.candles: Dict[int, dict] = {}  # time -> candle
        self.sorted_times = []
        self.dirty = False
        
    def update(self, time: int, price: float, qty: float):
        """Update existing candle or create new one"""
        if time in self.candles:
            c = self.candles[time]
            c['high'] = max(c['high'], price)
            c['low'] = min(c['low'], price)
            c['close'] = price
            c['volume'] += qty
        else:
            self.candles[time] = {
                'open': price,
                'high': price,
                'low': price,
                'close': price,
                'volume': qty
            }
            self.sorted_times.append(time)
            self.dirty = True
            
            # Memory management - keep only recent candles
            if len(self.sorted_times) > MAX_CANDLES_IN_MEMORY:
                old_time = self.sorted_times.pop(0)
                del self.candles[old_time]
    
    def get(self, time: int) -> dict:
        """Get candle with time included"""
        candle = self.candles.get(time)
        if candle:
            return {'time': time, **candle}
        return None
    
    def get_latest(self) -> dict:
        """Get most recent candle"""
        if self.sorted_times:
            return self.get(self.sorted_times[-1])
        return None
    
    def get_all(self) -> list:
        """Get all candles sorted by time"""
        if self.dirty:
            self.sorted_times.sort()
            self.dirty = False
        return [self.get(t) for t in self.sorted_times]


candle_store = CandleStore()
clients: Set[WebSocket] = set()

# Trade ledger
trades = []

# Pending broadcast queue
pending_update = None
broadcast_lock = asyncio.Lock()

# ---------------- HELPERS ---------------- #

def floor_time_ms(ts_ms: int, tf: str) -> int:
    """Floor timestamp to timeframe boundary (returns seconds since epoch)"""
    # ts_ms is already in milliseconds from Binance
    ts_seconds = ts_ms // 1000
    
    if tf == "1m":
        return (ts_seconds // 60) * 60
    elif tf == "5m":
        return (ts_seconds // 300) * 300
    elif tf == "1h":
        return (ts_seconds // 3600) * 3600
    
    return ts_seconds

# ---------------- DATA FETCHING ---------------- #

async def fetch_historical():
    """Fetch historical data using async requests"""
    end = datetime.now(tz=timezone.utc)
    start = end - timedelta(days=DAYS)
    
    start_ms = int(start.timestamp() * 1000)
    all_candles = []
    
    async with aiohttp.ClientSession() as session:
        while True:
            async with session.get(
                f"{BINANCE_REST}/api/v3/klines",
                params={
                    "symbol": SYMBOL,
                    "interval": TIMEFRAME,
                    "startTime": start_ms,
                    "limit": 1000,
                },
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                data = await resp.json()
                
                if not data:
                    break
                
                for k in data:
                    # k[0] is open time in milliseconds
                    candle_time = k[0] // 1000  # Convert to seconds for consistency
                    
                    candle_store.update(
                        candle_time,
                        float(k[4]),  # close price
                        float(k[5])   # volume
                    )
                    # Set OHLC properly for historical
                    candle_store.candles[candle_time].update({
                        'open': float(k[1]),
                        'high': float(k[2]),
                        'low': float(k[3]),
                    })
                
                start_ms = data[-1][0] + INTERVAL_MS[TIMEFRAME]
    
    print(f"Loaded {len(candle_store.candles)} historical candles")
    print(f"First candle time: {list(candle_store.sorted_times)[:3] if candle_store.sorted_times else 'none'}")
    print(f"Last candle time: {list(candle_store.sorted_times)[-3:] if candle_store.sorted_times else 'none'}")
    
    return candle_store.get_all()

# ---------------- BROADCAST OPTIMIZATION ---------------- #

async def broadcast_worker():
    """Batched broadcasting - sends updates every BROADCAST_INTERVAL"""
    global pending_update
    
    while True:
        await asyncio.sleep(BROADCAST_INTERVAL)
        
        async with broadcast_lock:
            if pending_update and clients:
                # Create message once
                msg = json.dumps(pending_update)
                
                # Broadcast to all clients
                dead = set()
                for ws in clients:
                    try:
                        await ws.send_text(msg)
                    except:
                        dead.add(ws)
                
                # Clean up dead connections
                clients.difference_update(dead)
                
                pending_update = None

# ---------------- STREAM TRADES ---------------- #

async def stream_trades():
    """Stream trades from Binance and update candles"""
    global pending_update
    
    uri = f"{BINANCE_WS}/{SYMBOL.lower()}@trade"
    
    # Load historical data first
    await fetch_historical()
    
    last_candle_time = None
    trade_count = 0
    
    print(f"Starting live trade stream from Binance...")
    
    async with websockets.connect(uri) as ws:
        async for msg in ws:
            t = json.loads(msg)
            
            price = float(t["p"])
            qty = float(t["q"])
            trade_time_ms = t["T"]  # Trade time in milliseconds
            
            # Calculate candle time (in seconds)
            candle_time = floor_time_ms(trade_time_ms, TIMEFRAME)
            
            # Debug first few trades
            trade_count += 1
            if trade_count <= 3:
                print(f"Trade #{trade_count}: trade_time_ms={trade_time_ms}, candle_time={candle_time}, price={price}")
            
            # Update candle store (fast in-memory operation)
            candle_store.update(candle_time, price, qty)
            
            # Prepare update for broadcast (will be sent in batch)
            async with broadcast_lock:
                pending_update = candle_store.get(candle_time)
            
            # Detect candle close (optional: trigger cleanup/save)
            if last_candle_time and candle_time != last_candle_time:
                print(f"New candle formed at {candle_time}")
            
            last_candle_time = candle_time

# ---------------- ENDPOINTS ---------------- #

@app.get("/candles")
async def get_candles():
    """Get all historical candles"""
    return candle_store.get_all()

@app.get("/candles/latest")
async def get_latest_candle():
    """Get latest candle only"""
    candle = candle_store.get_latest()
    if not candle:
        raise HTTPException(status_code=404, detail="No candles available")
    return candle

@app.post("/trade")
async def place_trade(trade_data: dict):
    """Place a paper trade"""
    symbol = trade_data.get("symbol")
    side = trade_data.get("side", "").lower()
    price = trade_data.get("price")
    quantity = trade_data.get("quantity")
    
    if side not in {"buy", "sell"}:
        return {"success": False, "error": "side must be 'buy' or 'sell'"}
    
    trade = {
        "symbol": symbol,
        "side": side,
        "price": price,
        "quantity": quantity,
        "timestamp": int(datetime.now(tz=timezone.utc).timestamp())
    }
    
    trades.append(trade)
    
    return {"success": True, "trade": trade}

@app.get("/trades")
async def get_trades():
    """Get all trades"""
    return trades

# ---------------- WEBSOCKET ---------------- #

@app.websocket("/ws/candles")
async def candle_ws(ws: WebSocket):
    """WebSocket endpoint for real-time candle updates"""
    await ws.accept()
    clients.add(ws)
    
    # Send current state immediately
    try:
        all_candles = candle_store.get_all()
        await ws.send_text(json.dumps({
            "type": "snapshot",
            "data": all_candles[-1000:]  # Last 1000 candles
        }))
    except:
        clients.discard(ws)
        return
    
    # Keep connection alive
    try:
        while True:
            await ws.receive_text()
    except:
        clients.discard(ws)

# ---------------- STARTUP ---------------- #

@app.on_event("startup")
async def startup():
    """Start background tasks"""
    asyncio.create_task(stream_trades())
    asyncio.create_task(broadcast_worker())

@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown"""
    for ws in list(clients):
        await ws.close()
    clients.clear()