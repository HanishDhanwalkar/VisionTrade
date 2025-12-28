import pandas as pd

from data import fetch_historical

import matplotlib.pyplot as plt
import mplfinance as mpf

def show_candlestick(symbol, timeframe="1h", days=1):
    data = fetch_historical(symbol, timeframe=timeframe, days=days)
    
    df = pd.DataFrame(data)
    df.set_index('time', inplace=True)
    df.index = pd.to_datetime(df.index, format='%Y-%m-%d %H:%M:%S')
    
    
    df.to_csv(f"{symbol}.csv")

    mpf.plot(df, type='candle', volume=True, style='yahoo')
    plt.show()

if __name__ == "__main__":
    show_candlestick("BTCUSDT")