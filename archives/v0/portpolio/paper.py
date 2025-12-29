

class PaperTradingEngine:
    def __init__(self, initial_balance):
        self.cash = initial_balance
        self.positions = {}
        self.trades = []

    def buy(self, symbol, price, qty):
        cost = price * qty
        if cost > self.cash:
            raise ValueError("Insufficient balance")

        pos = self.positions.get(symbol, {"qty": 0, "avg_price": 0})
        new_qty = pos["qty"] + qty
        new_avg = (pos["qty"] * pos["avg_price"] + cost) / new_qty

        self.positions[symbol] = {"qty": new_qty, "avg_price": new_avg}
        self.cash -= cost

        self.trades.append({"side": "BUY", "symbol": symbol, "price": price, "qty": qty})

    def sell(self, symbol, price, qty):
        pos = self.positions.get(symbol)
        if not pos or pos["qty"] < qty:
            raise ValueError("Insufficient position")

        self.cash += price * qty
        pos["qty"] -= qty

        if pos["qty"] == 0:
            del self.positions[symbol]

        self.trades.append({"side": "SELL", "symbol": symbol, "price": price, "qty": qty})

    def snapshot(self, prices):
        unrealized = 0.0
        for s, p in self.positions.items():
            unrealized += (prices[s] - p["avg_price"]) * p["qty"]

        return {
            "cash": self.cash,
            "positions": self.positions,
            "unrealized_pnl": unrealized,
            "total_equity": self.cash + unrealized,
        }
