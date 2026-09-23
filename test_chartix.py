import requests
import re
JS_URL = "https://chartix.ir/_nuxt/BlP3i0K2.js"
r = requests.get(
    JS_URL,
    headers={"User-Agent": "Mozilla/5.0"},
    timeout=60
)
js = r.text
patterns = [
    "market.chartix.ir",
    "/quote/",
    "/price/",
    "/market/",
    "/ticker/",
    "/trade/",
    "/ohlc/",
    "/history/"
]
for p in patterns:
    print("\n================", p, "================")
    positions = [m.start() for m in re.finditer(re.escape(p), js)]
    print("COUNT:", len(positions))
    for pos in positions[:5]:
        print("\n---")
        print(js[max(0,pos-300):pos+500])