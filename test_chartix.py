import requests
import re
from urllib.parse import urljoin
URL = "https://chartix.ir/market/saham-option"
s = requests.Session()
s.headers["User-Agent"] = "Mozilla/5.0"
try:
    r = s.get(URL, timeout=30)
    print("STATUS:", r.status_code)
    print("PAGE:", r.url)
    html = r.text
    scripts = re.findall(
        r'<script[^>]+src=["\']([^"\']+)["\']',
        html,
        re.I
    )
    found = set()
    for src in scripts:
        try:
            jsurl = urljoin(r.url, src)
            x = s.get(jsurl, timeout=20)
            if x.status_code != 200:
                continue
            js = x.text
            # URLهای کامل
            urls = re.findall(
                r'https?://[^"\'\s<>\\]+|wss?://[^"\'\s<>\\]+',
                js
            )
            for u in urls:
                if any(k in u.lower() for k in [
                    "api", "option", "market", "quote",
                    "symbol", "ohlc", "candle", "history",
                    "socket", "websocket"
                ]):
                    found.add(u)
            # مسیرهای API
            paths = re.findall(
                r'["\'](/[^"\']{1,200})["\']',
                js
            )
            for p in paths:
                if any(k in p.lower() for k in [
                    "/api", "option", "market", "quote",
                    "symbol", "ohlc", "candle", "history",
                    "socket", "websocket"
                ]):
                    found.add(p)
        except:
            pass
    print("\n===== RESULTS =====")
    results = sorted(found)
    print("TOTAL:", len(results))
    for i, item in enumerate(results[:20], 1):
        print(i, item)
    if len(results) > 20:
        print("\n... MORE RESULTS HIDDEN ...")
except Exception as e:
    print("ERROR:", type(e).__name__, e)