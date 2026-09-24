import requests
import re

BASE = "https://market.chartix.ir"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

session = requests.Session()
session.headers.update(HEADERS)

# ============================================================
# تنظیمات
# ============================================================

MAX_DISTANCE_PERCENT = 10      # حداکثر فاصله Strike از پایه
MIN_VOLUME = 50                # حداقل حجم معامله
MIN_OPTION_PRICE = 1           # حداقل قیمت اختیار
TOP_N = 3                      # سه قرارداد برتر CALL و PUT


# ============================================================
# دریافت تمام نمادها
# ============================================================

def get_all_symbols():

    r = session.get(
        f"{BASE}/symbol/all",
        timeout=30
    )

    r.raise_for_status()

    return r.json()["data"]["symbols"]


# ============================================================
# اطلاعات نماد
# ============================================================

def get_info(ticker):

    r = session.get(
        f"{BASE}/symbol/info/saham/{ticker}",
        timeout=30
    )

    if r.status_code != 200:
        return None

    return r.json()


# ============================================================
# استخراج Strike و سررسید
# ============================================================

def parse_option(description, name):

    m = re.search(
        r"-(\d+)-(\d{4}/\d{2}/\d{2})",
        description or ""
    )

    if not m:
        return None

    strike = int(m.group(1))
    expiry = m.group(2)

    if name.startswith("ط"):
        option_type = "CALL"

    elif name.startswith("ض"):
        option_type = "PUT"

    else:
        return None

    return {
        "strike": strike,
        "expiry": expiry,
        "type": option_type
    }


# ============================================================
# تشخیص سهم پایه
# ============================================================

def get_underlying_name(option_name):

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


# ============================================================
# حجم معاملات
# ============================================================

def get_volume(data):

    volume = 0

    for box in data.get("boxes", []):

        title = box.get("title", "")
        value = box.get("value", "")

        if "حجم معاملات" in title:

            try:
                volume = float(
                    str(value).replace(",", "")
                )
            except:
                volume = 0

    return volume


# ============================================================
# محاسبه امتیاز
# ============================================================

def calculate_score(x):

    score = 0

    distance = x["distance_percent"]
    volume = x["volume"]
    tv = x["time_value_percent"]

    # --------------------------------------------------------
    # نزدیکی به ATM
    # --------------------------------------------------------

    if distance <= 2:
        score += 45

    elif distance <= 3:
        score += 40

    elif distance <= 5:
        score += 30

    elif distance <= 7:
        score += 20

    elif distance <= 10:
        score += 10

    # --------------------------------------------------------
    # حجم معاملات
    # --------------------------------------------------------

    if volume >= 2000:
        score += 35

    elif volume >= 1000:
        score += 30

    elif volume >= 500:
        score += 25

    elif volume >= 200:
        score += 20

    elif volume >= 100:
        score += 15

    elif volume >= 50:
        score += 10

    # --------------------------------------------------------
    # Time Value
    # --------------------------------------------------------

    if tv >= 80:
        score += 20

    elif tv >= 60:
        score += 18

    elif tv >= 40:
        score += 15

    elif tv >= 20:
        score += 10

    else:
        score += 5

    return score


# ============================================================
# MAIN
# ============================================================

def main():

    print("در حال دریافت نمادها...")

    symbols = get_all_symbols()

    options = []

    # --------------------------------------------------------
    # پیدا کردن قراردادها
    # --------------------------------------------------------

    for s in symbols:

        name = s.get("name", "")
        description = s.get("description", "")
        ticker = s.get("ticker", "")

        if not (
            name.startswith("ط")
            or name.startswith("ض")
        ):
            continue

        parsed = parse_option(
            description,
            name
        )

        if not parsed:
            continue

        underlying = get_underlying_name(name)

        if not underlying:
            continue

        options.append({
            "name": name,
            "ticker": ticker,
            "underlying": underlying,
            **parsed
        })

    print(
        "تعداد اختیارهای پیدا شده:",
        len(options)
    )

    # --------------------------------------------------------
    # دریافت اطلاعات قراردادها
    # --------------------------------------------------------

    results = []

    for i, op in enumerate(options, 1):

        print(
            f"\rدریافت اطلاعات {i}/{len(options)}",
            end="",
            flush=True
        )

        try:

            data = get_info(op["ticker"])

            if not data:
                continue

            price = float(
                data.get("price") or 0
            )

            volume = get_volume(data)

            if price < MIN_OPTION_PRICE:
                continue

            # قرارداد بدون معامله حذف شود
            if volume < MIN_VOLUME:
                continue

            results.append({
                "name": op["name"],
                "type": op["type"],
                "strike": op["strike"],
                "expiry": op["expiry"],
                "option_price": price,
                "volume": volume,
                "underlying": op["underlying"]
            })

        except Exception:
            continue

    print("\n")

    # ========================================================
    # قیمت سهم های پایه
    # ========================================================

    underlying_prices = {}

    for s in symbols:

        name = s.get("name", "")

        if name not in [
            "خودرو",
            "اهرم",
            "شستا",
            "وبملت"
        ]:
            continue

        try:

            data = get_info(
                s.get("ticker", "")
            )

            if data:

                price = float(
                    data.get("price") or 0
                )

                if price > 0:
                    underlying_prices[name] = price

        except:
            pass

    print("قیمت پایه‌ها:")

    for name, price in underlying_prices.items():

        print(
            f"  {name}: {price:.0f}"
        )

    print()

    # ========================================================
    # محاسبات
    # ========================================================

    final = []

    for x in results:

        underlying_price = underlying_prices.get(
            x["underlying"]
        )

        if not underlying_price:
            continue

        strike = x["strike"]
        option_price = x["option_price"]

        # ----------------------------------------------------
        # ارزش ذاتی
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Time Value
        # ----------------------------------------------------

        time_value = option_price - intrinsic

        if time_value <= 0:
            continue

        tv_percent = (
            time_value / option_price
        ) * 100

        # ----------------------------------------------------
        # فاصله از ATM
        # ----------------------------------------------------

        distance = (
            abs(strike - underlying_price)
            / underlying_price
        ) * 100

        if distance > MAX_DISTANCE_PERCENT:
            continue

        # ----------------------------------------------------
        # Moneyness
        # ----------------------------------------------------

        if distance <= 3:

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

        # ----------------------------------------------------
        # ذخیره
        # ----------------------------------------------------

        x["underlying_price"] = underlying_price
        x["intrinsic"] = intrinsic
        x["time_value"] = time_value
        x["time_value_percent"] = tv_percent
        x["distance_percent"] = distance
        x["moneyness"] = moneyness

        # ----------------------------------------------------
        # امتیاز
        # ----------------------------------------------------

        x["score"] = calculate_score(x)

        final.append(x)

    # ========================================================
    # جدا کردن CALL و PUT
    # ========================================================

    calls = [
        x for x in final
        if x["type"] == "CALL"
    ]

    puts = [
        x for x in final
        if x["type"] == "PUT"
    ]

    # ========================================================
    # مرتب سازی
    # ========================================================

    calls.sort(
        key=lambda x: (
            x["score"],
            x["volume"],
            -x["distance_percent"]
        ),
        reverse=True
    )

    puts.sort(
        key=lambda x: (
            x["score"],
            x["volume"],
            -x["distance_percent"]
        ),
        reverse=True
    )

    # ========================================================
    # TOP CALL
    # ========================================================

    print("=" * 125)

    print("                 TOP 3 CALL")

    print("=" * 125)

    print(
        f"{'نماد':<13}"
        f"{'پایه':<9}"
        f"{'Strike':<9}"
        f"{'قیمت':<9}"
        f"{'فاصله%':<9}"
        f"{'TV%':<8}"
        f"{'حجم':<10}"
        f"{'وضعیت':<9}"
        f"{'Score':<7}"
        f"{'سررسید':<12}"
    )

    print("-" * 125)

    for x in calls[:TOP_N]:

        print(
            f"{x['name']:<13}"
            f"{x['underlying_price']:<9.0f}"
            f"{x['strike']:<9}"
            f"{x['option_price']:<9.0f}"
            f"{x['distance_percent']:<9.2f}"
            f"{x['time_value_percent']:<8.1f}"
            f"{x['volume']:<10.0f}"
            f"{x['moneyness']:<9}"
            f"{x['score']:<7}"
            f"{x['expiry']:<12}"
        )

    # ========================================================
    # TOP PUT
    # ========================================================

    print("\n")

    print("=" * 125)

    print("                 TOP 3 PUT")

    print("=" * 125)

    print(
        f"{'نماد':<13}"
        f"{'پایه':<9}"
        f"{'Strike':<9}"
        f"{'قیمت':<9}"
        f"{'فاصله%':<9}"
        f"{'TV%':<8}"
        f"{'حجم':<10}"
        f"{'وضعیت':<9}"
        f"{'Score':<7}"
        f"{'سررسید':<12}"
    )

    print("-" * 125)

    for x in puts[:TOP_N]:

        print(
            f"{x['name']:<13}"
            f"{x['underlying_price']:<9.0f}"
            f"{x['strike']:<9}"
            f"{x['option_price']:<9.0f}"
            f"{x['distance_percent']:<9.2f}"
            f"{x['time_value_percent']:<8.1f}"
            f"{x['volume']:<10.0f}"
            f"{x['moneyness']:<9}"
            f"{x['score']:<7}"
            f"{x['expiry']:<12}"
        )

    # ========================================================
    # آمار نهایی
    # ========================================================

    print("\n")

    print("=" * 125)

    print(
        "قراردادهای دارای Time Value:",
        len(final)
    )

    print(
        "CALL:",
        len(calls),
        "| PUT:",
        len(puts)
    )

    print(
        "قراردادهای قابل معامله پس از فیلتر حجم:",
        len(results)
    )

    print("=" * 125)


if __name__ == "__main__":
    main()