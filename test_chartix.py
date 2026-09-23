import requests
BASE = "https://chartix.ir/_nuxt/"
FILE = "CIO5fLUd.js"
url = BASE + FILE
r = requests.get(
    url,
    headers={"User-Agent": "Mozilla/5.0"},
    timeout=60
)
print("STATUS:", r.status_code)
print("SIZE:", len(r.text))
js = r.text
for key in [
    "market.chartix.ir",
    "symbol/",
    "candles",
    "quote",
    "volume",
    "openInterest",
    "lastPrice"
]:
    print("\n==========", key, "==========")
    pos = js.find(key)
    if pos >= 0:
        print(js[max(0, pos-1000):pos+2000])
    else:
        print("NOT FOUND")