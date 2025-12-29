
# import pandas as pd
# import plotly.express as px

# import sys
# from pathlib import Path

# sys.path.append(str(Path(__file__).parent.parent / "freqtrade"))

# from freqtrade.configuration import Configuration
# from freqtrade.data.btanalysis import load_backtest_stats


# strategy = 'SampleStrategy'
# config = Configuration.from_files(["user_data/config.json"])
# backtest_dir = config["user_data_dir"] / "backtest_results"

# stats = load_backtest_stats(backtest_dir)
# strategy_stats = stats["strategy"][strategy]

# df = pd.DataFrame(columns=["dates", "equity"], data=strategy_stats["daily_profit"])
# df["equity_daily"] = df["equity"].cumsum()

# fig = px.line(df, x="dates", y="equity_daily")
# fig.show()


# Add this to the end of your example.py

