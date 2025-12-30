import sys
from pathlib import Path
from typing import Dict, Any

sys.path.append(str(Path(__file__).parent.parent / "freqtrade"))

from freqtrade.configuration import TimeRange
from freqtrade.enums import RunMode

config: Dict[str, Any] = {}

config["timeframe"] = "5m"
timerange = None
config["timerange"] = TimeRange.parse_timerange(timerange) if timerange else None

config["exchange"] = {"name": "binance"}
config["user_data_dir"] = Path(__file__).parent / "user_data"

folder = Path(f"{config['user_data_dir']}/data")
exchange_name = config.get("exchange", {}).get("name", "").lower()
data_dir = folder.joinpath(exchange_name)
config["data_dir"] = data_dir

pairs = ["BTC/USDT"]
config["pairs"] = pairs
config['api_server'] = {
    "enabled": True,
    "listen_ip_address": "127.0.0.1",
    "listen_port": 8080,
    "verbosity": "error",
    "jwt_secret_key": "jwtSlimShady",
    "CORS_origins": [],
    "username": "freqtrader",
    "password": "SlimShady"
}

config["runmode"] = RunMode.WEBSERVER
config["dry_run"] = True
config["stake_currency"] = config.get("stake_currency", "USDT")
config["stake_amount"] = config.get("stake_amount", 30)
config["dry_run_wallet"] = config.get("dry_run_wallet", 1000)
config["max_open_trades"] = config.get("max_open_trades", 3)

if "pairlists" not in config:
    config["pairlists"] = [{"method": "StaticPairList"}]
    
if "pair_whitelist" not in config.get("exchange", {}):
    config["exchange"]["pair_whitelist"] = pairs # type: ignore

if "entry_pricing" not in config:
    config["entry_pricing"] = {
        "price_side": "same",
        "use_order_book": True,
        "order_book_top": 1,
        "price_last_balance": 0.0,
        "check_depth_of_market": {"enabled": False, "bids_to_ask_delta": 1}
    }
    
if "exit_pricing" not in config:
    config["exit_pricing"] = {
        "price_side": "same",
        "use_order_book": True,
        "order_book_top": 1
    }
    
config["strategy"] = "SampleStrategy"
config["strategy_path"] = str(Path(__file__).parent / "strategies")
config["db_url"] = "sqlite:///tradesv3.sqlite"
config["datadir"] = data_dir

if __name__ == "__main__":
    from freqtrade.worker import Worker
    from freqtrade.rpc.api_server.webserver import ApiServer
    
    # This internally creates the ApiServer and attaches the RPC handler.
    worker = Worker(args=None, config=config)
    
    try:
        print(f"API server is running on http://{config['api_server']['listen_ip_address']}:{config['api_server']['listen_port']}")
        print("Press Ctrl+C to stop")
        
        # Keep the process running while the background thread works
        import time
        while True:
            time.sleep(1)
            
    except (KeyboardInterrupt, SystemExit):
        print("Shutting down...")
        worker.exit()