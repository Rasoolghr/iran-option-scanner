import requests
import re
from urllib.parse import urljoin
PAGE = "https://chartix.ir/market/saham-option"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/140.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
session = requests.Session()
session.headers.update(HEADERS)
print("=" * 70)
print("CHARTIX API DISCOVERY")
print("=" * 70)
# ---------------------------------------------------------
# 1. دریافت صفحه اصلی اختیار
# ---------------------------------------------------------
try:
    r = session.get(PAGE, timeout=20)
    print("\nPAGE STATUS:", r.status_code)
    print("FINAL URL:", r.url)
    print("CONTENT TYPE:", r.headers.get("content-type"))
    print("PAGE SIZE:", len(r.content))
    html = r.text
except Exception as e:
    print("PAGE ERROR:", type(e).__name__, e)
    raise SystemExit(1)
# ---------------------------------------------------------
# 2. پیدا کردن JavaScript ها
# ---------------------------------------------------------
scripts = re.findall(
    r'<script[^>]+src=["\']([^"\']+)["\']',
    html,
    flags=re.I
)
print("\nJS FILES FOUND:", len(scripts))
js_urls = []
for src in scripts:
    url = urljoin(PAGE, src)
    if url not in js_urls:
        js_urls.append(url)
for url in js_urls:
    print("JS:", url)
# ---------------------------------------------------------
# 3. الگوهای مهم API
# ---------------------------------------------------------
patterns = [
    r'https?://[^"\'\s]+',
    r'["\'](/[^"\']*(?:api|option|market|symbol|quote|ohlc)[^"\']*)["\']',
    r'["\']([^"\']*(?:api|option|market|symbol|quote|ohlc)[^"\']*)["\']',
]
keywords = [
    "api",
    "option",
    "options",
    "market",
    "symbol",
    "quote",
    "ohlc",
    "candle",
    "history",
    "price",
    "volume",
]
# ---------------------------------------------------------
# 4. دانلود JS ها و جستجوی Endpoint
# ---------------------------------------------------------
found = set()
for i, js_url in enumerate(js_urls, 1):
    print("\n" + "=" * 70)
    print(f"JS {i}/{len(js_urls)}")
    print(js_url)
    try:
        jr = session.get(js_url, timeout=20)
        print("STATUS:", jr.status_code)
        print("SIZE:", len(jr.content))
        if jr.status_code != 200:
            continue
        js = jr.text
        # URL های کامل
        for pattern in patterns:
            try:
                matches = re.findall(pattern, js, flags=re.I)
            except Exception:
                continue
            for item in matches:
                if isinstance(item, tuple):
                    item = item[0]
                item = item.strip()
                if len(item) < 5:
                    continue
                low = item.lower()
                if any(k in low for k in keywords):
                    if item not in found:
                        found.add(item)
                        print("\nFOUND:", item)
    except Exception as e:
        print("JS ERROR:", type(e).__name__, e)
# ---------------------------------------------------------
# 5. جستجوی مستقیم داخل HTML
# ---------------------------------------------------------
print("\n" + "=" * 70)
print("SEARCHING HTML")
print("=" * 70)
for keyword in keywords:
    positions = [
        m.start()
        for m in re.finditer(
            re.escape(keyword),
            html,
            flags=re.I
        )
    ]
    if positions:
        print(
            f"\nKEYWORD '{keyword}' "
            f"FOUND {len(positions)} TIMES"
        )
        # حداکثر 5 نمونه از اطراف عبارت
        for pos in positions[:5]:
            start = max(0, pos - 150)
            end = min(len(html), pos + 300)
            snippet = html[start:end]
            print("-" * 50)
            print(snippet)
# ---------------------------------------------------------
# 6. خلاصه
# ---------------------------------------------------------
print("\n" + "=" * 70)
print("DISCOVERY FINISHED")
print("=" * 70)
print("TOTAL POSSIBLE ENDPOINTS:", len(found))
for x in sorted(found):
    print(x)
print("\nIf endpoints were found, send me this entire output.")