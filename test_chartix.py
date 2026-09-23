import requests
import json
url = "https://market.chartix.ir/symbol/info/saham/BRS0010747"
d = requests.get(
    url,
    headers={"User-Agent": "Mozilla/5.0"},
    timeout=30
).json()
print("STATUS:", 200)
print("\n=== BOXES ===")
for x in d.get("boxes", []):
    print(x.get("title"), "=>", x.get("value"))
print("\n=== MOST KEYS ===")
most = d.get("most", [])
print("COUNT:", len(most))
if most:
    print("FIRST:")
    print(json.dumps(most[0], ensure_ascii=False, indent=2))