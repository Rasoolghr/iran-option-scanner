import requests
import json
BASE = "https://market.chartix.ir"
headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
}
tests = [
    ("اهرم", "BRS0010747"),
    ("خودرو", "BRS0010395"),
    ("شستا", "BRS0010496"),
    ("وبملت", "BRS0010596"),
]
for name, ticker in tests:
    url = f"{BASE}/symbol/info/saham/{ticker}"
    print("\n" + "=" * 60)
    print("SYMBOL:", name)
    print("TICKER:", ticker)
    print("URL:", url)
    try:
        r = requests.get(url, headers=headers, timeout=30)
        print("STATUS:", r.status_code)
        print("TYPE:", r.headers.get("content-type"))
        if r.status_code == 200:
            data = r.json()
            print("\nRESPONSE:")
            print(json.dumps(data, ensure_ascii=False, indent=2)[:10000])
        else:
            print("\nERROR:")
            print(r.text[:3000])
    except Exception as e:
        print("ERROR:", type(e).__name__, e)