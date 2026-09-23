import requests
import re
from urllib.parse import urljoin
URL = "https://chartix.ir/market/saham-option"
s = requests.Session()
s.headers["User-Agent"] = "Mozilla/5.0"
r = s.get(URL, timeout=30)
print("STATUS:", r.status_code)
html = r.text
scripts = re.findall(
    r'<script[^>]+src=["\']([^"\']+)["\']',
    html,
    re.I
)
found = set()
for src in scripts:
    try:
        js = s.get(urljoin(r.url, src), timeout=20).text
        # فقط endpointهایی که احتمالاً داده‌ای هستند
        patterns = [
            r'["\']([^"\']*/api/[^"\']+)["\']',
            r'["\']([^"\']*(?:quote|quotes|ohlc|candle|candles|history|ticker|tickers|market-data|marketdata)[^"\']*)["\']',
            r'["\'](wss?://[^"\']+)["\']',
            r'https?://[^"\'\s<>]+',
        ]
        for pattern in patterns:
            for x in re.findall(pattern, js, re.I):
                x = x.strip()
                # حذف موارد واضحاً نامرتبط
                low = x.lower()
                if any(k in low for k in [
                    "/api/",
                    "quote",
                    "ohlc",
                    "candle",
                    "history",
                    "ticker",
                    "market-data",
                    "marketdata",
                    "wss://",
                    "ws://"
                ]):
                    found.add(x)
    except:
        pass
print("\n===== POSSIBLE DATA API =====")
results = sorted(found)
print("TOTAL:", len(results))
for i, x in enumerate(results[:30], 1):
    print(i, x)