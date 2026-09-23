import requests
import json
URL = "https://chartix.ir/api/symbols/search"
params = {
    "q": "خودرو"
}
headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json"
}
try:
    r = requests.get(
        URL,
        params=params,
        headers=headers,
        timeout=30
    )
    print("STATUS:", r.status_code)
    print("URL:", r.url)
    print("TYPE:", r.headers.get("content-type"))
    data = r.json()
    print("\n===== RESPONSE =====")
    print(json.dumps(data, ensure_ascii=False, indent=2)[:12000])
except Exception as e:
    print("ERROR:", type(e).__name__, e)