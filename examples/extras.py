import datetime

ts = 1764369300000

timestamp = ts /1000 #1339521878.04

value = datetime.datetime.fromtimestamp(timestamp)
print(value.strftime('%Y-%m-%d %H:%M:%S'))   