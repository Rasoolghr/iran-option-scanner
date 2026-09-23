import requests
import json
url = "https://market.chartix.ir/symbol/info/saham/BRS0010747"
r = requests.get(
    url,
    headers={"User-Agent": "Mozilla/5.0"},
    timeout=30
)
data = r.json()
print("STATUS:", r.status_code)
print("\nKEYS:")
print(list(data.keys()))
print("\nNESTED DATA:")
for k, v in data.items():
    if isinstance(v, dict):
        print(k, "=>", list(v.keys()))