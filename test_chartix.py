import requests
import re
from urllib.parse import urljoin
PAGE = "https://chartix.ir/market/saham-option"
s = requests.Session()
s.headers["User-Agent"] = "Mozilla/5.0"
r = s.get(PAGE, timeout=30)
print("STATUS:", r.status_code)
scripts = re.findall(
    r'<script[^>]+src=["\']([^"\']+)["\']',
    r.text,
    re.I
)
apis = set()
for src in scripts:
    try:
        js = s.get(
            urljoin(r.url, src),
            timeout=20
        ).text
        # فقط مسیرهایی که واقعاً /api/ دارند
        matches = re.findall(
            r'["\'`](/api/[^"\'`\\\s]{1,200})["\'`]',
            js,
            re.I
        )
        for x in matches:
            apis.add(x)
    except:
        pass
print("\n===== API PATHS =====")
# فقط APIهایی که احتمال ارتباط با بازار دارند
important = []
for x in sorted(apis):
    low = x.lower()
    if any(k in low for k in [
        "symbol",
        "market",
        "option",
        "quote",
        "price",
        "trade",
        "order",
        "history",
        "candle",
        "ohlc",
        "chart",
        "data",
        "ticker",
        "portfolio"
    ]):
        important.append(x)
for i, x in enumerate(important, 1):
    print(i, x)
print("\nTOTAL IMPORTANT:", len(important))