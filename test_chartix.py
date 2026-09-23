import requests
import re
BASE = "https://chartix.ir"
TICKER = "BRS0010747"      # ضهرم0125
ALIAS = "IRO9AHRM0531"
headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "*/*",
}
# ---------------------------------------------------------
# 1) تست endpointهای احتمالی با ticker و alias
# ---------------------------------------------------------
paths = [
    f"/api/symbols/{TICKER}",
    f"/api/symbol/{TICKER}",
    f"/api/symbols/{ALIAS}",
    f"/api/symbol/{ALIAS}",
    f"/api/quotes/{TICKER}",
    f"/api/quote/{TICKER}",
    f"/api/market/{TICKER}",
    f"/api/markets/{TICKER}",
    f"/api/chart/{TICKER}",
    f"/api/charts/{TICKER}",
    f"/api/history/{TICKER}",
    f"/api/ohlc/{TICKER}",
    f"/api/candles/{TICKER}",
    f"/api/data/{TICKER}",
    f"/api/symbol-data/{TICKER}",
]
print("===== ENDPOINT TEST =====")
for path in paths:
    try:
        r = requests.get(
            BASE + path,
            headers=headers,
            timeout=10
        )
        print(
            path,
            "=>",
            r.status_code,
            r.headers.get("content-type", "")
        )
        # فقط پاسخ‌های غیر 404 را نمایش بده
        if r.status_code != 404:
            print(r.text[:1000])
    except Exception as e:
        print(path, "=> ERROR", type(e).__name__)
# ---------------------------------------------------------
# 2) دریافت صفحه نماد و پیدا کردن فایل‌های JS
# ---------------------------------------------------------
print("\n===== JS DISCOVERY =====")
try:
    r = requests.get(
        BASE + "/market/saham-option",
        headers=headers,
        timeout=30
    )
    print("PAGE STATUS:", r.status_code)
    html = r.text
    scripts = re.findall(
        r'<script[^>]+src=["\']([^"\']+\.js[^"\']*)',
        html
    )
    print("JS FILES:", len(scripts))
    for src in scripts:
        if src.startswith("/"):
            url = BASE + src
        elif src.startswith("http"):
            url = src
        else:
            url = BASE + "/" + src
        try:
            js = requests.get(
                url,
                headers=headers,
                timeout=20
            ).text
            # مسیرهای API که واقعاً داخل JS آمده‌اند
            matches = re.findall(
                r'["\'`]([^"\'`]*?/api/[^"\'`]+)["\'`]',
                js
            )
            for m in matches:
                if any(x in m.lower() for x in [
                    "quote",
                    "market",
                    "chart",
                    "history",
                    "ohlc",
                    "candle",
                    "price",
                    "trade",
                    "volume",
                    "option",
                    "openinterest",
                    "open-interest",
                    "symbol"
                ]):
                    print(m)
        except:
            pass
except Exception as e:
    print("JS ERROR:", type(e).__name__, e)