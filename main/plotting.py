from typing import Any, Dict
import pandas as pd
import plotly.express as px

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "freqtrade"))

from freqtrade.configuration import TimeRange
from freqtrade.data.btanalysis import load_backtest_stats


config: Dict[str, Any] = {}

config["timeframe"] = "5m"
timerange = None  # Load all available data
config["timerange"] = TimeRange.parse_timerange(timerange) if timerange else None

config["exchange"] = {"name": "binance"}
config["user_data_dir"] = Path(__file__).parent  / "user_data"

strategy = 'SampleStrategy'
backtest_dir = config["user_data_dir"] / "backtest_results"

stats = load_backtest_stats(backtest_dir)
strategy_stats = stats["strategy"][strategy]

df = pd.DataFrame(columns=["dates", "equity"], data=strategy_stats["daily_profit"])
df["equity_daily"] = df["equity"].cumsum()

fig = px.line(df, x="dates", y="equity_daily")
fig.show()
