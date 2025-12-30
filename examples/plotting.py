from typing import Any, Dict

import plotly.graph_objects as go
from plotly.subplots import make_subplots

import talib.abstract as ta
import pandas as pd
import json
import os

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "freqtrade"))

from freqtrade.configuration import TimeRange
from freqtrade.data.btanalysis import load_backtest_stats
from freqtrade.plot.plotting import generate_candlestick_graph


config: Dict[str, Any] = {}

config["timeframe"] = "5m"
timerange = None  # Load all available data
config["timerange"] = TimeRange.parse_timerange(timerange) if timerange else None

config["exchange"] = {"name": "binance"}
config["user_data_dir"] = Path(__file__).parent  / "user_data"

strategy = 'SampleStrategy'
backtest_dir = config["user_data_dir"] / "backtest_results"

data_dir = config["user_data_dir"] / "data" / config["exchange"]["name"]

stats = load_backtest_stats(backtest_dir)

trades = stats['strategy'][strategy]['trades']
all_trades_df = pd.DataFrame(trades)

print(all_trades_df.head())

unique_pairs = all_trades_df['pair'].unique()

for pair in unique_pairs:
    filename_pair = pair.replace('/', '_')
    filename = f"{filename_pair}-5m.json"
    filepath = data_dir / filename
    
    if not os.path.exists(filepath):
        print(f"Skipping {pair}: File {filename} not found.")
        continue

    with open(filepath, 'r') as f:
        ohlcv_data = json.load(f)
    
    df = pd.DataFrame(ohlcv_data, columns=['date', 'open', 'high', 'low', 'close', 'volume'])
    df['date'] = pd.to_datetime(df['date'], unit='ms', utc=True)
    df = df.set_index('date')

    # 6. Add Indicators
    df['rsi'] = ta.Function('RSI')(df)
    df['ema'] = ta.Function('EMA')(df, timeperiod=20)

    # 7. Filter trades for ONLY this pair and map to markers
    pair_trades = all_trades_df[all_trades_df['pair'] == pair]
    df['entry_markers'] = float('nan')
    df['exit_markers'] = float('nan')
    
    df.reset_index(inplace=True)
    
    # 8. Generate and Show Plot
    fig = generate_candlestick_graph(
        pair=pair,
        data=df,
        trades=pair_trades,
        indicators1=['ema'], 
        indicators2=['rsi']
    )
    fig.show()