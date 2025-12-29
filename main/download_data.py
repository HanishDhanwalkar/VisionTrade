import logging
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "freqtrade"))

from freqtrade.configuration import Configuration, TimeRange
from freqtrade.resolvers import ExchangeResolver
from freqtrade.data.history import refresh_backtest_ohlcv_data
from freqtrade.enums import TradingMode

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

config = Configuration.from_files([str(Path(__file__).parent.parent / "config.json")])


def download_data(
    pairs: list,
    timeframes: list,
    timerange: str,
    days_to_download: int = 30
):
    """
    Download historical data programmatically.
    
    Args:
        config_path: Path to config.json file. If None, uses default path relative to workspace root.
        pairs: List of pairs to download (e.g., ["BTC/USDT"]). If None, uses config pair_whitelist.
        timeframes: List of timeframes (e.g., ["5m"]). If None, uses config timeframe.
        timerange: Optional timerange string (e.g., "20241101-20241229"). If None, uses days_to_download.
        days_to_download: Number of days to fetch if timerange is None.
    """

    
    
    print(f"Exchange: {config['exchange']['name']}")
    print(f"Data directory: {config['datadir']}")
    
    # Use provided pairs or fall back to config pair_whitelist
    if pairs is None:
        pairs = config.get("exchange", {}).get("pair_whitelist", ["BTC/USDT"])
    
    # Use provided timeframes or fall back to config timeframe
    if timeframes is None:
        timeframe = config.get("timeframe", "5m")
        timeframes = [timeframe]
    
    print(f"\nStarting download for {pairs} on {timeframes}...")
    
    # Convert timerange string to TimeRange object if provided
    timerange_obj = None
    if timerange:
        timerange_obj = TimeRange.parse_timerange(timerange)
        print(f"Timerange: {timerange}")
    
    # Load exchange
    exchange = None
    try:
        exchange = ExchangeResolver.load_exchange(
            config, 
            validate=False
        )
        
        # Execute the download logic
        # This is the same function the CLI 'download-data' command uses
        refresh_backtest_ohlcv_data(
            exchange=exchange,
            pairs=pairs,
            timeframes=timeframes,
            datadir=config['datadir'],      # Usually user_data/data/binance
            timerange=timerange_obj,        # TimeRange object or None to use 'new_pairs_days'
            new_pairs_days=days_to_download if timerange_obj is None else 0,
            erase=False,                    # Set to True if you want to overwrite existing data
            data_format=config.get('dataformat_ohlcv', 'json'),
            trading_mode=TradingMode.SPOT,
            prepend=False
        )
        
        print(f"\nDownload complete! Data saved to: {config['datadir']}")
    finally:
        # Properly close the exchange connection to avoid warnings
        if exchange:
            exchange.close()


if __name__ == "__main__":
    download_data(
        pairs=[
            "BTC/USDT", 
            "ETH/USDT", 
            "BAT/USDT"
        ],
        timeframes=["5m"],
        timerange="20241101-20241229"
    )
    
    # Example 3: Download for specific number of days
    # download_data(
    #     pairs=["BTC/USDT"],
    #     timeframes=["5m"],
    #     days_to_download=60  # Download last 60 days
    # )