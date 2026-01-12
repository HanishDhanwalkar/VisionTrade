import sys
import time
import signal
from pathlib import Path
from typing import Dict, Any

# Ensure freqtrade path is correct
sys.path.append(str(Path(__file__).parent.parent / "freqtrade"))

from freqtrade.worker import Worker
from freqtrade.enums import RunMode, State
from freqtrade.loggers import setup_logging
from freqtrade.persistence import Trade

# 1. Setup Logging
setup_logging(config={"verbosity": 0})

# 2. Configuration
config: Dict[str, Any] = {
    "max_open_trades": 3,
    "stake_currency": "USDT",
    "stake_amount": 30,
    "fiat_display_currency": "USD",
    "tradable_balance_ratio": 0.99,
    "dry_run": True,
    "dry_run_wallet": 1000,
    "exchange": {
        "name": "binance",
        "key": "",
        "secret": "",
        "pair_whitelist": ["BTC/USDT"],
        "pair_blacklist": []
    },
    "pairlists": [{"method": "StaticPairList"}],
    "timeframe": "1m",
    "db_url": "sqlite:///tradesv3.dryrun.sqlite",
    "runmode": RunMode.DRY_RUN,
    "api_server": {
        "enabled": True,
        "listen_ip_address": "127.0.0.1",
        "listen_port": 8080,
        "verbosity": "error",
        "jwt_secret_key": "jwtSlimShady",
        "CORS_origins": [],
        "username": "freqtrader",
        "password": "SlimShady"
    },
    # Required to prevent KeyError 'cancel_open_orders_on_exit' during cleanup
    "cancel_open_orders_on_exit": False,
    "unfilledtimeout": {
        "entry": 10,
        "exit": 30,
        "unit": "minutes"
    },
    "order_types": {
        "entry": "limit",
        "exit": "limit",
        "emergency_exit": "market",
        "force_entry": "market",
        "force_exit": "market",
        "stoploss": "market",
        "stoploss_on_exchange": False
    },
    "entry_pricing": {"price_side": "same", "use_order_book": True},
    "exit_pricing": {"price_side": "same", "use_order_book": True},
}

config["user_data_dir"] = Path(__file__).parent  / "user_data"
folder = Path(f"{config['user_data_dir']}/data")
exchange_name = config.get("exchange", {}).get("name", "").lower()
data_dir = folder.joinpath(exchange_name)
config["data_dir"] = data_dir

config["strategy"] = "SampleStrategy"
config["strategy_path"] = str(Path(__file__).parent / "strategies")

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

def close_all_trades_and_exit(worker: Worker):
    """
    Closes all open trades and shuts down the bot safely.
    """
    print("\n[!] Shutdown signal received. Closing all trades...")
    try:
        # Access the internal bot instance
        bot = worker.freqtrade
        
        # Get all currently open trades from the DB
        open_trades = Trade.get_open_trades()
        
        if not open_trades:
            print("No open trades to close.")
        else:
            for trade in open_trades:
                print(f"Force exiting trade for {trade.pair}...")
                # Triggers a market sell for the trade
                bot.handle_exit_signal(trade, "emergency_exit")
        
        worker.exit()
        print("Cleanup complete. Bot stopped.")
    except Exception as e:
        print(f"Error during shutdown: {e}")
    finally:
        sys.exit(0)

if __name__ == "__main__":
    try:
        # Initialize the Worker (This creates the FreqtradeBot and ApiServer)
        worker = Worker(args={}, config=config)
        
        # Connect Ctrl+C (SIGINT) to our cleanup function
        signal.signal(signal.SIGINT, lambda sig, frame: close_all_trades_and_exit(worker))

        print(f"Bot started. UI: http://{config['api_server']['listen_ip_address']}:{config['api_server']['listen_port']}")
        
        # The .run() method in worker.py handles the loop and state management internally
        worker.run()
            
    except Exception as e:
        print(f"Critical error during startup: {e}")
        sys.exit(1)