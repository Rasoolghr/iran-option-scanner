import requests
import re
import time
BASE = "https://market.chartix.ir"
HEADERS = {
    "User-Agent": "Mozilla/5.0"
}
session = requests.Session()
session.headers.update(HEADERS)
def get_all_symbols():
    r = session.get(f"{BASE}/symbol/all", timeout=30)
    r.raise_for_status()
    return r.json()["data"]["symbols"]
def get_info(ticker):
    r = session.get(
        f"{BASE}/symbol/info/saham/{ticker}",
        timeout=30
    )
    if r.status_code != 200:
        return None
    return r.json()
def parse_option(description, name):
    # مثال:
    # اختيارخ اهرم-15000-1405/01/26
    m = re.search(
        r"-(\d+)-(\d{4}/\d{2}/\d{2})",
        description or ""
    )
    if not m:
        return None
    strike = int(m.group(1))
    expiry = m.group(2)
    option_type = None
    if name.startswith("ط"):
        option_type = "CALL"
    elif name.startswith("ض"):
        option_type = "PUT"
    if not option_type:
        return None
    return {
        "strike": strike,
        "expiry": expiry,
        "type": option_type
    }
def get_underlying_name(option_name):
    # ضخود0145 -> خودرو
    # ضهرم0125 -> اهرم
    # ضستا0132 -> شستا
    # ضملت0123 -> وبملت
    mapping = {
        "خودرو": "خودرو",
        "هرم": "اهرم",
        "ستا": "شستا",
        "ملت": "وبملت"
    }
    for key, value in mapping.items():
        if key in option_name:
            return value
    return None
def main():
    print("در حال دریافت نمادها...")
    symbols = get_all_symbols()
    options = []
    for s in symbols:
        name = s.get("name", "")
        description = s.get("description", "")
        ticker = s.get("ticker", "")
        if not (name.startswith("ط") or name.startswith("ض")):
            continue
        parsed = parse_option(description, name)
        if not parsed:
            continue
        options.append({
            "name": name,
            "ticker": ticker,
            "description": description,
            **parsed
        })
    print("تعداد اختیارهای پیدا شده:", len(options))
    results = []
    for i, op in enumerate(options, 1):
        print(
            f"\rدریافت اطلاعات {i}/{len(options)}",
            end="",
            flush=True
        )
        try:
            d = get_info(op["ticker"])
            if not d:
                continue
            option_price = float(d.get("price") or 0)
            volume = 0
            for box in d.get("boxes", []):
                title = box.get("title", "")
                value = box.get("value", "")
                if "حجم معاملات" in title:
                    try:
                        volume = float(
                            str(value).replace(",", "")
                        )
                    except:
                        volume = 0
            underlying = get_underlying_name(op["name"])
            results.append({
                "name": op["name"],
                "type": op["type"],
                "strike": op["strike"],
                "expiry": op["expiry"],
                "option_price": option_price,
                "volume": volume,
                "underlying": underlying
            })
        except Exception:
            continue
    print("\n")
    # --------------------------------------------------
    # پیدا کردن قیمت سهم پایه
    # --------------------------------------------------
    underlying_prices = {}
    for s in symbols:
        name = s.get("name", "")
        if name in ["خودرو", "اهرم", "شستا", "وبملت"]:
            try:
                d = get_info(s["ticker"])
                if d:
                    underlying_prices[name] = float(
                        d.get("price") or 0
                    )
            except:
                pass
    # --------------------------------------------------
    # محاسبه Time Value
    # --------------------------------------------------
    final = []
    for x in results:
        underlying_price = underlying_prices.get(
            x["underlying"]
        )
        if not underlying_price:
            continue
        strike = x["strike"]
        option_price = x["option_price"]
        if x["type"] == "CALL":
            intrinsic = max(
                underlying_price - strike,
                0
            )
        else:
            intrinsic = max(
                strike - underlying_price,
                0
            )
        time_value = option_price - intrinsic
        if option_price > 0:
            time_value_percent = (
                time_value / option_price
            ) * 100
        else:
            time_value_percent = 0
        if time_value <= 0:
            continue
        if abs(underlying_price - strike) < 0.02 * underlying_price:
            moneyness = "ATM"
        elif (
            x["type"] == "CALL"
            and underlying_price > strike
        ) or (
            x["type"] == "PUT"
            and underlying_price < strike
        ):
            moneyness = "ITM"
        else:
            moneyness = "OTM"
        x["underlying_price"] = underlying_price
        x["intrinsic"] = intrinsic
        x["time_value"] = time_value
        x["time_value_percent"] = time_value_percent
        x["moneyness"] = moneyness
        final.append(x)
    # --------------------------------------------------
    # مرتب‌سازی بر اساس Time Value %
    # --------------------------------------------------
    final.sort(
        key=lambda x: x["time_value_percent"],
        reverse=True
    )
    print("=" * 110)
    print("        SCANNER — قراردادهای دارای TIME VALUE")
    print("=" * 110)
    print(
        f"{'نماد':<12}"
        f"{'نوع':<6}"
        f"{'پایه':<10}"
        f"{'Strike':<8}"
        f"{'قیمت':<10}"
        f"{'Intrinsic':<12}"
        f"{'TimeValue':<12}"
        f"{'TV%':<8}"
        f"{'Moneyness':<8}"
        f"{'Volume':<10}"
    )
    print("-" * 110)
    for x in final[:50]:
        print(
            f"{x['name']:<12}"
            f"{x['type']:<6}"
            f"{x['underlying_price']:<10.0f}"
            f"{x['strike']:<8}"
            f"{x['option_price']:<10.0f}"
            f"{x['intrinsic']:<12.0f}"
            f"{x['time_value']:<12.0f}"
            f"{x['time_value_percent']:<8.1f}"
            f"{x['moneyness']:<8}"
            f"{x['volume']:<10.0f}"
        )
    print("\nتعداد قراردادهای دارای Time Value مثبت:", len(final))
if __name__ == "__main__":
    main()