SYMBOLS = ["BTCUSDT", "ETHUSDT"]

TIMEFRAME = "1m"          # 1m, 5m, 1h
HISTORY_DAYS = 365

INITIAL_BALANCE = 10_000.0

BINANCE_REST_URL = "https://api.binance.com"
BINANCE_WS_URL = "wss://stream.binance.com:9443/stream"

MAX_CANDLES = HISTORY_DAYS * 1440  # for 1m
