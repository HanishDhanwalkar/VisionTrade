"""
Standalone script to download market data programmatically using freqtrade codebase.
No freqtrade installation required - uses the local freqtrade codebase.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Dict, List

# Add freqtrade to path
sys.path.append(str(Path(__file__).parent.parent / "freqtrade"))

from freqtrade.configuration import TimeRange
from freqtrade.data.history import refresh_backtest_ohlcv_data
from freqtrade.enums import RunMode
from freqtrade.resolvers import ExchangeResolver
from freqtrade.loggers import setup_logging

# ANSI color codes for better output
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
GREY = "\033[90m"
RESET = "\033[0m"
BOLD = "\033[1m"


logger = setup_logging(
    config={
        "verbosity": 0
})

def download_market_data(
    exchange_name: str = "binance",
    pairs: List[str] = ["BTC/USDT"],
    timeframes: List[str] = ["5m"],
    datadir: Path | None = None,
    timerange: str | None = None,
    days: int | None = None,
    data_format: str = "json",
    trading_mode: str = "spot",
    erase: bool = False,
    new_pairs_days: int = 30,
    user_data_dir: Path | None = None,
) -> Dict[str, Any]:
    """
    Download market data for specified pairs and timeframes.
    
    Args:
        exchange_name: Exchange name (e.g., "binance", "kraken", "coinbasepro")
        pairs: List of trading pairs (e.g., ["BTC/USDT", "ETH/USDT"])
        timeframes: List of timeframes (e.g., ["5m", "1h", "1d"])
        datadir: Directory to save data (defaults to user_data/data/{exchange_name})
        timerange: Timerange string (e.g., "20240101-20241231" or "20240101-")
        days: Number of days to download (alternative to timerange)
        data_format: Data format ("json", "feather", "hdf5", "parquet")
        trading_mode: Trading mode ("spot" or "futures")
        erase: Whether to erase existing data before downloading
        new_pairs_days: Days of data to download for new pairs
        user_data_dir: User data directory (defaults to examples/user_data)
    
    Returns:
        Dictionary with download results and statistics
    """

    if user_data_dir is None:
        user_data_dir = Path(__file__).parent / "user_data"
    if datadir is None:
        datadir = user_data_dir / "data" / exchange_name.lower()
    
    datadir.mkdir(parents=True, exist_ok=True)
    
    config: Dict[str, Any] = {
        "exchange": {"name": exchange_name},
        "datadir": datadir,
        "user_data_dir": user_data_dir,
        "dataformat_ohlcv": data_format,
        "trading_mode": trading_mode,
        "runmode": RunMode.BACKTEST,
        "stake_currency": "",  # Not needed
        "dry_run": True,  # Required by exchange initialization
    }
    
    # Parse timerange
    parsed_timerange = None
    if timerange:
        parsed_timerange = TimeRange.parse_timerange(timerange)
    elif days:
        time_since = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
        parsed_timerange = TimeRange.parse_timerange(f"{time_since}-")
    
    print(f"{BOLD}Market Data Download Configuration{RESET}")
    print(f"  Exchange:        {GREEN}{exchange_name}{RESET}")
    print(f"  Pairs:           {GREEN}{', '.join(pairs)}{RESET}")
    print(f"  Timeframes:      {GREEN}{', '.join(timeframes)}{RESET}")
    print(f"  Data directory:  {GREY}{datadir}{RESET}")
    print(f"  Data format:     {GREEN}{data_format}{RESET}")
    print(f"  Trading mode:    {GREEN}{trading_mode}{RESET}")
    
    if parsed_timerange:
        print(f"  Timerange:       {GREEN}{parsed_timerange}{RESET}")
    elif days:
        print(f"  Days:            {GREEN}{days} days{RESET}")
    else:
        print(f"  Timerange:       {YELLOW}All available data{RESET}")
        
    print(f"  Erase existing:  {GREEN if erase else YELLOW}{erase}{RESET}")
    
    try:
        exchange = ExchangeResolver.load_exchange(config, validate=False)
        
        available_markets = list(exchange.get_markets(tradable_only=True, active_only=True).keys())
        valid_pairs = [p for p in pairs if p in available_markets]
        invalid_pairs = [p for p in pairs if p not in available_markets]
        
        if invalid_pairs:
            print(f"{YELLOW}Warning: The following pairs are not available on {exchange_name}:{RESET}")
            for pair in invalid_pairs:
                print(f"  {RED}✗ {pair}{RESET}")
            print()
        
        if not valid_pairs:
            raise ValueError(f"No valid pairs found. Available pairs: {available_markets[:10]}...")
        
        # Download data
        pairs_not_available = refresh_backtest_ohlcv_data(
            exchange=exchange,
            pairs=valid_pairs,
            timeframes=timeframes,
            datadir=datadir,
            trading_mode=trading_mode,
            timerange=parsed_timerange,
            new_pairs_days=new_pairs_days,
            erase=erase,
            data_format=data_format,
            prepend=False,
            candle_types=None,
            no_parallel_download=False,
        )
        
        if pairs_not_available:
            print(f"{YELLOW}Pairs not available or failed:{RESET}")
            for pair_error in pairs_not_available:
                print(f"  {RED}✗ {pair_error}{RESET}")
            print()
        
        # Check downloaded files
        downloaded_pairs = []
        for pair in valid_pairs:
            pair_file_base = pair.replace("/", "_")
            found_files = []
            for tf in timeframes:
                # Check for data files (format depends on data_format)
                if data_format == "json":
                    file_pattern = f"{pair_file_base}-{tf}.json"
                elif data_format == "feather":
                    file_pattern = f"{pair_file_base}-{tf}.feather"
                elif data_format == "hdf5":
                    file_pattern = f"{pair_file_base}-{tf}.h5"
                elif data_format == "parquet":
                    file_pattern = f"{pair_file_base}-{tf}.parquet"
                else:
                    file_pattern = f"{pair_file_base}-{tf}.*"
                
                matching_files = list(datadir.glob(file_pattern))
                if matching_files:
                    found_files.append(tf)
                    file_size = matching_files[0].stat().st_size / 1024  # KB
                    print(f"  {GREEN}✓{RESET} {pair} {tf:>6} - {file_size:.1f} KB")
            
            if found_files:
                downloaded_pairs.append(pair)
        
        print(f"\n{GREEN}✓ Successfully downloaded data for {len(downloaded_pairs)}/{len(valid_pairs)} pair(s){RESET}")
        print(f"{GREY}Data saved to: {datadir}{RESET}")
        print(f"{'='*60}\n")
        
        exchange.close()
        
        return {
            "success": True,
            "downloaded_pairs": downloaded_pairs,
            "pairs_not_available": pairs_not_available,
            "datadir": str(datadir),
            "exchange": exchange_name,
        }
        
    except Exception as e:
        error_msg = f"{RED}Error downloading data: {str(e)}{RESET}"
        print(f"\n{error_msg}\n")
        return {
            "success": False,
            "error": str(e),
            "datadir": str(datadir),
            "exchange": exchange_name,
        }


if __name__ == "__main__":
    EXCHANGE = "binance"
    
    # Trading pairs to download
    PAIRS = [
        "BTC/USDT",
        "ETH/USDT",
        # Add more pairs as needed
        # "BNB/USDT",
        # "SOL/USDT",
    ]
    
    # Timeframes to download
    TIMEFRAMES = [
        "1m"
        # "5m",
        # "15m",
        # "1h",
        # "4h",
        # "1d",
        # Add more timeframes as needed
        # "1m", "3m", "30m", "2h", "6h", "12h", "3d", "1w"
    ]
    
    # Data download options
    TIMERANGE = None  # e.g., "20240101-20241231" or "20240101-" (from date to now)
    DAYS = 730  # Alternative: download last N days (e.g., 365 for 1 year)
    # If both TIMERANGE and DAYS are None, downloads all available data
    # NEW_PAIRS_DAYS = 30  # Days of data to download for new pairs
    
    
    # Data storage options
    DATA_FORMAT = "json"  # Options: "json", "feather", "hdf5", "parquet"
    TRADING_MODE = "spot"  # Options: "spot" or "futures"
    ERASE_EXISTING = False  # Set to True to delete existing data before downloading
    
    # ============================================================================
    # Run the download
    # ============================================================================
    
    result = download_market_data(
        exchange_name=EXCHANGE,
        pairs=PAIRS,
        timeframes=TIMEFRAMES,
        timerange=TIMERANGE,
        days=DAYS,
        data_format=DATA_FORMAT,
        trading_mode=TRADING_MODE,
        erase=ERASE_EXISTING,
        # new_pairs_days=NEW_PAIRS_DAYS,
    )
    
    if result["success"]:
        print(f"{GREEN}{BOLD}✓ Data download completed successfully!{RESET}")
        sys.exit(0)
    else:
        print(f"{RED}{BOLD}✗ Data download failed!{RESET}")
        sys.exit(1)

