import sqlite3
import pandas as pd


conn = sqlite3.connect('tradesv3.sqlite')

# Get table names
tables = pd.read_sql_query("SELECT name FROM sqlite_master WHERE type='table';", conn)
print("--- Table List ---")
print(tables)

# Get the first 5 rows of the 'trades' table
# This is where Pandas shines—it formats the output like a spreadsheet
trades_df = pd.read_sql_query("SELECT * FROM trades;", conn)
print("\n--- Trades Preview ---")
print(trades_df)
# print(trades_df.head())

conn.close()