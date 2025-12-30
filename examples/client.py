import requests


url = "http://localhost:8080/"
res = requests.get(
    url = url + "balance",
)

print(f"Health: {res.text}")

