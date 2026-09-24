import requests
import re
import time
from datetime import datetime

BASE = "https://market.chartix.ir"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

session = requests.Session()
session.headers.update(HEADERS)


# ============================================================
# تنظیمات اسکنر
# ============================================================

# حداکثر فاصله Strike از قیمت پایه برای ورود به اسکن
MAX_DISTANCE_PERCENT = 15

# محدوده ترجیحی برای ATM
ATM_PERCENT = 3

# حداقل حجم برای امتیازدهی
MIN_VOLUME = 10

# حداقل قیمت اختیار
MIN_OPTION_PRICE = 1

# تعداد خروجی نهایی
TOP_RESULTS = 20


# ============================================================
# دریافت نمادها
# ============================================================

def get_all_symbols():
    r = session.get(
        f"{BASE}/symbol/all",
        timeout=30
    )
    r.raise_for_status()
    return r.json()["data"]["symbols"]


# ============================================================
# دریافت اطلاعات نماد
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
# تشخیص مشخصات اختیار
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
# محاسبه فاصله Strike از قیمت پایه
# ============================================================

def strike_distance_percent(underlying, strike):

    if underlying <= 0:
        return 999

    return abs(strike - underlying) / underlying * 100


# ============================================================
# امتیازدهی
# ============================================================

def calculate_score(x):

    score = 0

    distance = x["distance_percent"]
    volume = x["volume"]
    tv_percent = x["time_value_percent"]

    # --------------------------------------------------------
    # فاصله از ATM
    # --------------------------------------------------------

    if distance <= 3:
        score += 40

    elif distance <= 5:
        score += 30

    elif distance <= 8:
        score += 20

    elif distance <= 12:
        score += 10

    # --------------------------------------------------------
    # نقدشوندگی
    # --------------------------------------------------------

    if volume >= 1000:
        score += 30

    elif volume >= 500:
        score += 25

    elif volume >= 200:
        score += 20

    elif volume >= 100:
        score += 15

    elif volume >= 50:
        score += 10

    elif volume >= MIN_VOLUME:
        score += 5

    # --------------------------------------------------------
    # Time Value
    # --------------------------------------------------------

    if tv_percent >= 50:
        score += 20

    elif tv_percent >= 30:
        score += 15

    elif tv_percent >= 15:
        score += 10

    elif tv_percent > 0:
        score += 5

    return score


# ============================================================
# MAIN
# ============================================================

def main():

    print("در حال دریافت نمادها...")

    symbols = get_all_symbols()

    options = []

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
            "description": description,
            "underlying": underlying,
            **parsed
        })

    print(
        "تعداد اختیارهای پیدا شده:",
        len(options)
    )


    # ========================================================
    # دریافت اطلاعات اختیارها
    # ========================================================

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

            option_price = float(
                d.get("price") or 0
            )

            volume = 0

            for box in d.get("boxes", []):

                title = box.get("title", "")
                value = box.get("value", "")

                if "حجم معاملات" in title:

                    try:

                        volume = float(
                            str(value)
                            .replace(",", "")
                        )

                    except:
                        volume = 0

            if option_price < MIN_OPTION_PRICE:
                continue

            results.append({

                "name": op["name"],
                "type": op["type"],
                "strike": op["strike"],
                "expiry": op["expiry"],
                "option_price": option_price,
                "volume": volume,
                "underlying": op["underlying"]

            })

        except Exception:
            continue

    print("\n")


    # ========================================================
    # قیمت سهم‌های پایه
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

            d = get_info(s["ticker"])

            if d:

                underlying_prices[name] = float(
                    d.get("price") or 0
                )

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
        # Intrinsic
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

        if option_price > 0:

            tv_percent = (
                time_value /
                option_price
            ) * 100

        else:

            tv_percent = 0

        # ----------------------------------------------------
        # فاصله Strike
        # ----------------------------------------------------

        distance = strike_distance_percent(
            underlying_price,
            strike
        )

        # قراردادهای خیلی دور حذف شوند

        if distance > MAX_DISTANCE_PERCENT:
            continue

        # ----------------------------------------------------
        # Moneyness
        # ----------------------------------------------------

        if distance <= ATM_PERCENT:

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
        # اطلاعات نهایی
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
    # مرتب‌سازی
    # ========================================================

    final.sort(
        key=lambda x: (
            x["score"],
            x["volume"],
            x["time_value_percent"]
        ),
        reverse=True
    )


    # ========================================================
    # خروجی CALL
    # ========================================================

    calls = [
        x for x in final
        if x["type"] == "CALL"
    ]

    puts = [
        x for x in final
        if x["type"] == "PUT"
    ]


    print("=" * 125)

    print(
        "              TOP CALL CONTRACTS"
    )

    print("=" * 125)

    print(
        f"{'نماد':<12}"
        f"{'پایه':<9}"
        f"{'Strike':<8}"
        f"{'قیمت':<8}"
        f"{'فاصله%':<9}"
        f"{'TV%':<8}"
        f"{'حجم':<10}"
        f"{'Moneyness':<10}"
        f"{'Score':<7}"
        f"{'سررسید':<12}"
    )

    print("-" * 125)

    for x in calls[:TOP_RESULTS]:

        print(
            f"{x['name']:<12}"
            f"{x['underlying_price']:<9.0f}"
            f"{x['strike']:<8}"
            f"{x['option_price']:<8.0f}"
            f"{x['distance_percent']:<9.2f}"
            f"{x['time_value_percent']:<8.1f}"
            f"{x['volume']:<10.0f}"
            f"{x['moneyness']:<10}"
            f"{x['score']:<7}"
            f"{x['expiry']:<12}"
        )


    # ========================================================
    # خروجی PUT
    # ========================================================

    print("\n")

    print("=" * 125)

    print(
        "              TOP PUT CONTRACTS"
    )

    print("=" * 125)

    print(
        f"{'نماد':<12}"
        f"{'پایه':<9}"
        f"{'Strike':<8}"
        f"{'قیمت':<8}"
        f"{'فاصله%':<9}"
        f"{'TV%':<8}"
        f"{'حجم':<10}"
        f"{'Moneyness':<10}"
        f"{'Score':<7}"
        f"{'سررسید':<12}"
    )

    print("-" * 125)

    for x in puts[:TOP_RESULTS]:

        print(
            f"{x['name']:<12}"
            f"{x['underlying_price']:<9.0f}"
            f"{x['strike']:<8}"
            f"{x['option_price']:<8.0f}"
            f"{x['distance_percent']:<9.2f}"
            f"{x['time_value_percent']:<8.1f}"
            f"{x['volume']:<10.0f}"
            f"{x['moneyness']:<10}"
            f"{x['score']:<7}"
            f"{x['expiry']:<12}"
        )


    print("\n")
    print("=" * 125)

    print(
        "تعداد قراردادهای نهایی:",
        len(final)
    )

    print(
        "CALL:",
        len(calls),
        "| PUT:",
        len(puts)
    )

    print("=" * 125)


if __name__ == "__main__":
    main()