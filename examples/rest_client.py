import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "freqtrade" / "ft_client"))

from freqtrade_client.ft_rest_client import FtRestClient


client = FtRestClient(
    serverurl="http://127.0.0.1:8080", 
    username="freqtrader", 
    password="SlimShady"
)

# Test basic ping (no auth required)
print("Ping:", client.ping())

# Test health endpoint
try:
    print("Health:", client.health())
except Exception as e:
    print(f"Health endpoint error: {e}")

# If you need authenticated endpoints, you'll need to login first
try:
    # This will require proper authentication
    print("Count:", client.count())
except Exception as e:
    print(f"Count endpoint error (expected if auth is needed): {e}")