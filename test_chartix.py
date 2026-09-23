import requests
import json
url = "https://market.chartix.ir/symbol/info/saham/BRS0010747"
r = requests.get(
    url,
    headers={"User-Agent": "Mozilla/5.0"},
    timeout=30
)
d = r.json()
print("STATUS:", r.status_code)
for key in [
    "name",
    "price",
    "priceFormatted",
    "change",
    "changePercent",
    "priceUpdatedAt",
    "boxes",
    "most",
]:
    print(f"\n===== {key} =====")
    print(json.dumps(d.get(key), ensure_ascii=False, indent=2))