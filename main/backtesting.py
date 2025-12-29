import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "freqtrade"))

from freqtrade.configuration import Configuration
from freqtrade.optimize.backtesting import Backtesting
from freqtrade.data.btanalysis import load_backtest_stats


config = Configuration.from_files(["user_data/config.json"])

# Set required configuration values
config["timeframe"] = config.get("timeframe", "5m")

config["strategy"] = "SampleStrategy"
config["strategy_path"] = str(Path(__file__).parent)

# Ensure data format is set (defaults to json if not in config)
if "dataformat_ohlcv" not in config:
    config["dataformat_ohlcv"] = "json"

# Set export directory and filename for results
if not config.get("exportdirectory"):
    config["exportdirectory"] = config["user_data_dir"] / "backtest_results"

# Ensure export directory exists
config["exportdirectory"].mkdir(parents=True, exist_ok=True)

# Set export format (trades, signals, or none)
config["export"] = config.get("export", "trades")

def run_backtest(timerange: str):
    config["timerange"] = timerange
    print(f"Using timerange: {timerange}")
        
    print(f"Starting backtest with strategy: {config['strategy']}")
    print(f"Timeframe: {config['timeframe']}")
    print(f"Export directory: {config['exportdirectory']}")
    
    # Initialize and run backtesting
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
        
        strategy_name = config["strategy"]
        
        if strategy_name in stats.get("strategy", {}):
            strategy_stats = stats["strategy"][strategy_name]
            
            print("="*50)
            print("BACKTEST RESULTS")
            print("="*50)
            
            # Basic statistics
            print(f"\nStrategy: {strategy_name}")
            total_trades = strategy_stats.get('total_trades', 0)
            wins = strategy_stats.get('wins', 0)
            print(f"Total trades: {total_trades}")
            if total_trades > 0:
                win_rate = (wins / total_trades) * 100
                print(f"Win rate: {win_rate:.2f}%")
            else:
                print(f"Win rate: 0.00%")
            print(f"Total profit: {strategy_stats.get('profit_total', 0):.2f}%")
            print(f"Total profit (abs): {strategy_stats.get('profit_total_abs', 0):.4f} {config.get('stake_currency', 'USDT')}")
            
            # ROI and drawdown
            print(f"\nMax drawdown: {strategy_stats.get('max_drawdown', 0):.2f}%")
            print(f"Max drawdown (abs): {strategy_stats.get('max_drawdown_abs', 0):.4f} {config.get('stake_currency', 'USDT')}")
            
            if strategy_stats.get('drawdown_start'):
                print(f"Drawdown start: {strategy_stats.get('drawdown_start')}")
            if strategy_stats.get('drawdown_end'):
                print(f"Drawdown end: {strategy_stats.get('drawdown_end')}")
            
            # Market change
            print(f"\nMarket change: {strategy_stats.get('market_change', 0):.2f}%")
            
            # Results per pair
            results_per_pair = strategy_stats.get('results_per_pair')
            if results_per_pair:
                print("\nResults per pair:")
                # Handle both list and dict formats
                if isinstance(results_per_pair, list):
                    for pair_stats in results_per_pair:
                        pair_key = pair_stats.get('key', 'Unknown')
                        pair_trades = pair_stats.get('total_trades', pair_stats.get('trades', 0))
                        # Handle case where trades might be a list
                        if isinstance(pair_trades, list):
                            pair_trades = len(pair_trades)
                        profit_total = pair_stats.get('profit_total', 0)
                        print(f"  {pair_key}: {profit_total:.2f}% ({pair_trades} trades)")
                elif isinstance(results_per_pair, dict):
                    for pair, pair_stats in results_per_pair.items():
                        pair_trades = pair_stats.get('total_trades', pair_stats.get('trades', 0))
                        # Handle case where trades might be a list
                        if isinstance(pair_trades, list):
                            pair_trades = len(pair_trades)
                        print(f"  {pair}: {pair_stats.get('profit_total', 0):.2f}% ({pair_trades} trades)")
            
            # Pairlist
            if strategy_stats.get('pairlist'):
                print(f"\nPairs tested: {', '.join(strategy_stats['pairlist'])}")
            
            # Timerange
            if strategy_stats.get('backtest_start'):
                print(f"\nBacktest period:")
                print(f"  Start: {strategy_stats.get('backtest_start')}")
                print(f"  End: {strategy_stats.get('backtest_end')}")
            
        else:
            print(f"Warning: Strategy '{strategy_name}' not found in results.")
            print(f"Available strategies: {list(stats.get('strategy', {}).keys())}")
        
        # Strategy comparison (if multiple strategies)
        if stats.get("strategy_comparison"):
            print("\n" + "="*50)
            print("STRATEGY COMPARISON")
            print("="*50)
            for comp in stats["strategy_comparison"]:
                print(f"\n{comp.get('key', 'Unknown')}:")
                print(f"  Profit: {comp.get('profit_total', 0):.2f}%")
                comp_trades = comp.get('total_trades', comp.get('trades', 0))
                # Handle case where trades might be a list
                if isinstance(comp_trades, list):
                    comp_trades = len(comp_trades)
                comp_wins = comp.get('wins', 0)
                print(f"  Trades: {comp_trades}")
                if comp_trades > 0:
                    comp_win_rate = (comp_wins / comp_trades) * 100
                    print(f"  Win rate: {comp_win_rate:.2f}%")
                else:
                    print(f"  Win rate: 0.00%")
        
        return stats
        
    except Exception as e:
        print(f"\nError during backtesting: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        # Cleanup
        Backtesting.cleanup()


if __name__ == "__main__":
    stats = run_backtest(
        timerange="20241101-20241229"  # Specific date range
    )
    
    # print(stats)
    
    # You can also access the stats programmatically
    strategy_name = "SampleStrategy"
    if strategy_name in stats.get("strategy", {}):
        profit = stats["strategy"][strategy_name]["profit_total"]
        print(f"Total profit: {profit}%")

