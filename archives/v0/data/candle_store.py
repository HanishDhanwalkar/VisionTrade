from collections import defaultdict, deque

class CandleStore:
    def __init__(self, maxlen=500_000):
        self.candles = defaultdict(lambda: deque(maxlen=maxlen))

    def load_history(self, symbol, candles):
        self.candles[symbol].clear()
        for c in candles:
            self.candles[symbol].append(c)

    def update_candle(self, symbol, candle):
        if self.candles[symbol] and self.candles[symbol][-1]["time"] == candle["time"]:
            self.candles[symbol][-1] = candle
        else:
            self.candles[symbol].append(candle)

    def get_candles(self, symbol):
        return list(self.candles[symbol])

    def last_price(self, symbol):
        if not self.candles[symbol]:
            return None
        return self.candles[symbol][-1]["close"]
