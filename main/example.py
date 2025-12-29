import logging
import sys
from pathlib import Path
import json
from copy import deepcopy
import math

from typing import Any, Dict
import pandas as pd

sys.path.append(str(Path(__file__).parent.parent / "freqtrade"))

# from freqtrade.configuration import Configuration
# config = Configuration.from_files(["user_data/config.json"])

from freqtrade.configuration import TimeRange
from freqtrade.data.history import load_data, load_pair_history
from freqtrade.enums import CandleType, RunMode

from freqtrade.data.dataprovider import DataProvider
from freqtrade.resolvers import StrategyResolver

from freqtrade.optimize.backtesting import Backtesting
from freqtrade.data.btanalysis import load_backtest_stats

from freqtrade.plot.plotting import (
    generate_candlestick_graph,
    store_plot_file,
    generate_plot_filename
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
# ANSI color codes
GREEN = "\033[32m"
RED = "\033[31m"
GREY = "\033[90m"
RESET = "\033[0m"

config: Dict[str, Any] = {}

config["timeframe"] = "5m"
# Set timerange to None to load all available data, or specify a range that matches your data
# timerange = "20241101-20241229"
timerange = None  # Load all available data
config["timerange"] = TimeRange.parse_timerange(timerange) if timerange else None

config["exchange"] = {"name": "binance"}
config["user_data_dir"] = Path.cwd() / "user_data"

# data dir
folder = Path(f"{config['user_data_dir']}/data")
exchange_name = config.get("exchange", {}).get("name", "").lower()
data_dir = folder.joinpath(exchange_name)
config["data_dir"] = data_dir

pairs = [
    "BTC/USDT"
]
config["pairs"] = pairs

# print(json.dumps(
#     config,
#     indent=4, 
#     default=str)
# )


# ================= 1. LOAD DATA ==================================

# ##########################
# candles = load_pair_history(
#     datadir=config.get("datadir", data_dir),
#     timeframe=config["timeframe"],
#     pair=pair,
#     data_format="json",  # Make sure to update this to your data
#     candle_type=CandleType.SPOT,
# )

# # Confirm success
# print(f"Loaded {len(candles)} rows of data for {pair} from {data_location}")
# print(candles.head())
# ########################## 

datadir = config.get("datadir", data_dir)
logging.info(f"Data directory: {GREY}{datadir}{RESET} | Directory exists: {GREEN}SUCCESS{RESET}" if datadir.exists() else f"Data directory: {GREY}{datadir}{RESET} | Directory exists: {RED}FAIL{RESET}")

data = load_data(
    datadir = config.get("datadir", data_dir),
    timeframe = config.get("timeframe", "5m"),
    pairs = config.get("pairs", ["BTC/USDT"]),
    timerange = config.get("timerange"),
    data_format = "json",
    fill_up_missing = True,
    
    startup_candles = 0,
    candle_type = CandleType.SPOT,
)

logging.info(f"Loaded {GREEN}{len(data)}{RESET} | pairs of data from {datadir}")

if not data:
    print(f"No data found for {pairs}")
    logging.error(f"{RED}No data found for {pairs}{RESET}")

for pair, df in data.items():
    print(f"\n{pair}: {len(df)} rows")
    if not df.empty:
        print(f"  Date range: {df['date'].min()} to {df['date'].max()}")
        print(f"First 5 rows:")
        print(df.head())
    else:
        print(f"  No data found for {pair}")


# ===================== 2. Strategies ================================== 
config["strategy"] = "SampleStrategy"
config["strategy_path"] = str(Path(__file__).parent)
logging.info(f"Loading strategy: {GREEN}{config['strategy']}{RESET} from {GREY}{config['strategy_path']}{RESET}")

strategy = StrategyResolver.load_strategy(config)
strategy.dp = DataProvider(config, None, None)
strategy.ft_bot_start()

# Generate buy/sell signals using strategy
for key in data.keys():
    logging.info(f"Analyzing {key}")
    df = strategy.analyze_ticker(data[key], {"pair": key})
    # print(df.tail())
    # print(df.describe())

    # Report results
    print(f"Generated {df['enter_long'].sum()} entry signals")
    res_data = df.set_index("date", drop=False)
    print(res_data.tail())

# ==================== 3. Backtesting ==================================
# Store original config before modifications (required for storing backtest results)
config["original_config"] = deepcopy(config)

config["dataformat_ohlcv"] = "json"
config["dataformat_trades"] = "json"  # Required for backtesting
config["exportdirectory"] = config["user_data_dir"] / "backtest_results"
if not config["exportdirectory"].exists():
    config["exportdirectory"].mkdir(parents=True, exist_ok=True)

config["export"] = config.get("export", "trades")
# Set runmode for backtesting (required by exchange initialization)
config["runmode"] = RunMode.BACKTEST

# Set datadir for backtesting
config["datadir"] = data_dir

# Required configuration fields for backtesting
config["stake_currency"] = config.get("stake_currency", "USDT")
config["stake_amount"] = config.get("stake_amount", 30)
config["dry_run_wallet"] = config.get("dry_run_wallet", 1000)
config["max_open_trades"] = config.get("max_open_trades", 3)

# Set pairlists - StaticPairList will use exchange.pair_whitelist
if "pairlists" not in config:
    config["pairlists"] = [{"method": "StaticPairList"}]
    
# Ensure exchange has pair_whitelist set
if "pair_whitelist" not in config.get("exchange", {}):
    config["exchange"]["pair_whitelist"] = pairs # type: ignore
    
# Required pricing configuration
if "entry_pricing" not in config:
    config["entry_pricing"] = {
        "price_side": "same",
        "use_order_book": True,
        "order_book_top": 1,
        "price_last_balance": 0.0,
        "check_depth_of_market": {
            "enabled": False,
            "bids_to_ask_delta": 1
        }
    }
if "exit_pricing" not in config:
    config["exit_pricing"] = {
        "price_side": "same",
        "use_order_book": True,
        "order_book_top": 1
    }

logging.info(f"Starting backtest with strategy: {GREEN}{config['strategy']}{RESET}")
logging.info(f"Timeframe:  {config['timeframe']}")
logging.info(f"Export directory: {GREY}{config['exportdirectory']}{RESET}")

def clean_config_for_json(cfg):
    """Recursively clean config to replace infinity values and Path objects for JSON serialization"""
    cleaned = {}
    for key, value in cfg.items():
        if isinstance(value, dict):
            cleaned[key] = clean_config_for_json(value)
        elif isinstance(value, Path):
            # Convert Path objects to strings
            cleaned[key] = str(value)
        elif isinstance(value, (float, int)):
            if math.isinf(value):
                # Replace inf with -1 (represents unlimited for max_open_trades)
                cleaned[key] = -1
            elif math.isnan(value):
                # Replace nan with None
                cleaned[key] = None
            else:
                cleaned[key] = value
        else:
            cleaned[key] = value
    return cleaned

# This should be set after all config modifications but before Backtesting initialization
config["original_config"] = clean_config_for_json(deepcopy(config))

try:
    backtesting = Backtesting(config)
    backtesting.start()
    
    print("\n" + "="*50)
    print("Backtest completed successfully!")
    print("="*50 + "\n")
    
    # Load backtest results
    stats = load_backtest_stats(
        config["exportdirectory"],
        config.get("exportfilename")
    )
    
    # with open("stats.txt", "w") as f:
    #     json.dump(stats, f, indent=4)
    
except Exception as e:
    print(f"\nError during backtesting: {e}")
    import traceback
    traceback.print_exc()
    raise
finally:
    # Cleanup
    Backtesting.cleanup()
    
# print(stats)

# ================ 4. Plot visualization ===============================
logging.info("Generating plot...")
pairs = config.get("pairs", [])
pair = pairs[0]

print(f"Plotting {pair}...")

# Create indicators dict (customize based on your strategy)
indicators = {
    "main": strategy.plot_config.get("main_plot", {}),
    "subplots": strategy.plot_config.get("subplots", {})
}

trades_df = pd.DataFrame(data=stats["strategy"][config['strategy']]["trades"])

# Generate the candlestick graph
fig = generate_candlestick_graph(
    pair=pair,
    data=res_data, # type: ignore
    trades=trades_df,  # Include trades from backtest
    indicators1=indicators.get("main", {}),
    indicators2=indicators.get("subplots", {})
)

# Save the plot
plot_filename = generate_plot_filename(pair, config["timeframe"])
plot_path = config["exportdirectory"] / plot_filename

store_plot_file(
    fig=fig,
    filename=plot_filename,
    directory=config["exportdirectory"],
    auto_open=True
)

logging.info(f"Plot saved to: {plot_path}")