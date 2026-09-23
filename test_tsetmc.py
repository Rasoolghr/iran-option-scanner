import requests

URL = "https://webgw.tse.ir/InstrumentProvider/api/v1/MarketWatch/MarketWatchOption/fa"

headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
}

try:
    r = requests.get(URL, headers=headers, timeout=20)

    print("HTTP STATUS:", r.status_code)
    print("CONTENT LENGTH:", len(r.text))
    print("RESPONSE:")
    print(r.text[:5000])

    r.raise_for_status()

except Exception as e:
    print("ERROR:", repr(e))
    raise
