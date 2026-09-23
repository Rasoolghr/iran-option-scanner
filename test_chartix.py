import requests
import re
BASE = "https://chartix.ir"
PAGE = BASE + "/market/saham-option"
headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "*/*"
}
print("===== DOWNLOAD PAGE =====")
html = requests.get(
    PAGE,
    headers=headers,
    timeout=30
).text
# همه فایل‌های JS
scripts = re.findall(
    r'<script[^>]+src=["\']([^"\']+\.js[^"\']*)',
    html
)
print("JS FILES:", len(scripts))
seen = set()
for src in scripts:
    if src.startswith("http"):
        url = src
    elif src.startswith("/"):
        url = BASE + src
    else:
        url = BASE + "/" + src
    if url in seen:
        continue
    seen.add(url)
    print("\n================================")
    print("JS:", url)
    try:
        js = requests.get(
            url,
            headers=headers,
            timeout=30
        ).text
        print("SIZE:", len(js))
        # -------------------------------------------------
        # fetch / $fetch / useFetch / axios
        # -------------------------------------------------
        patterns = [
            r'\$fetch\s*\([^)]{0,500}',
            r'fetch\s*\([^)]{0,500}',
            r'useFetch\s*\([^)]{0,500}',
            r'axios\.[a-zA-Z]+\s*\([^)]{0,500}',
            r'axios\s*\([^)]{0,500}'
        ]
        found = set()
        for pattern in patterns:
            matches = re.findall(pattern, js, re.I | re.S)
            for m in matches:
                m = re.sub(r'\s+', ' ', m)
                # فقط موارد مرتبط با داده بازار
                low = m.lower()
                if any(word in low for word in [
                    "/api/",
                    "quote",
                    "price",
                    "market",
                    "trade",
                    "volume",
                    "chart",
                    "ohlc",
                    "candle",
                    "history",
                    "option",
                    "openinterest",
                    "open-interest",
                    "order"
                ]):
                    found.add(m[:800])
        for x in found:
            print("\nREQUEST:")
            print(x)
        # -------------------------------------------------
        # تمام رشته‌های /api/ با context
        # -------------------------------------------------
        print("\n===== API CONTEXT =====")
        for match in re.finditer(r'/api/', js, re.I):
            start = max(0, match.start() - 250)
            end = min(len(js), match.start() + 500)
            context = js[start:end]
            context = re.sub(r'\s+', ' ', context)
            print("\n---")
            print(context[:750])
    except Exception as e:
        print("ERROR:", type(e).__name__, e)