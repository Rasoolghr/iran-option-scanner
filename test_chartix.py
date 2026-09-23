import requests
import json
BASE = "https://market.chartix.ir"
headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json"
}
# قرارداد نمونه
ticker = "BRS0010747"
alias = "IRO9AHRM0531"
urls = [
    f"{BASE}/symbol/all",
    f"{BASE}/symbol/info/{ticker}/{alias}",
    f"{BASE}/symbol/info/{ticker}",
    f"{BASE}/symbol/info/{alias}",
]
for url in urls:
    print("\n================================")
    print("URL:", url)
    try:
        r = requests.get(
            url,
            headers=headers,
            timeout=30
        )
        print("STATUS:", r.status_code)
        print("TYPE:", r.headers.get("content-type"))
        print("RESPONSE:")
        print(r.text[:5000])
    except Exception as e:
        print("ERROR:", type(e).__name__, e)