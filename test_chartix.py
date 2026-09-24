import requests
import re
import jdatetime
from datetime import datetime

BASE = "https://market.chartix.ir"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

session = requests.Session()
session.headers.update(HEADERS)

# =========================
# تنظیمات اسکنر
# =========================

MIN_VOLUME = 50
MIN_OPTION_PRICE = 10

# حداکثر فاصله قیمت پایه تا Strike
MAX_DISTANCE_PERCENT = 10

# محدوده ATM
ATM_PERCENT = 3

TOP_N = 5


# =========================
# دریافت همه نمادها
# =========================

def get_all_symbols():

    r = session.get(
        f"{BASE}/symbol/all",
        timeout=30
    )

    r.raise_for_status()

    return r.json()["data"]["symbols"]


# =========================
# اطلاعات نماد
# =========================

def get_info(ticker):

    r = session.get(
        f"{BASE}/symbol/info/saham/{ticker}",
        timeout=30
    )

    if r.status_code != 200:
        return None

    return r.json()


# =========================
# تشخیص CALL / PUT
# =========================

def parse_option(description, name):

    m = re.search(
        r"-(\d+)-(\d{4}/\d{2}/\d{2})",
        description or ""
    )

    if not m:
        return None

    strike = int(m.group(1))
    expiry = m.group(2)

    # در بورس ایران:
    # ط = اختیار خرید
    # ض = اختیار فروش

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


# =========================
# تشخیص دارایی پایه
# =========================

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


# =========================
# تاریخ امروز شمسی
# =========================

def today_jalali():

    today = jdatetime.date.today()

    return today.strftime("%Y/%m/%d")


# =========================
# بررسی فعال بودن قرارداد
# =========================

def is_active_expiry(expiry):

    try:

        expiry_date = jdatetime.datetime.strptime(
            expiry,
            "%Y/%m/%d"
        ).date()

        today = jdatetime.date.today()

        return expiry_date >= today

    except Exception:

        return False


# =========================
# محاسبه فاصله
# =========================

def calculate_moneyness(option_type, underlying, strike):

    distance = abs(
        underlying - strike
    ) / underlying * 100

    if distance <= ATM_PERCENT:

        status = "ATM"

    elif option_type == "CALL":

        if underlying > strike:
            status = "ITM"
        else:
            status = "OTM"

    else:

        if underlying < strike:
            status = "ITM"
        else:
            status = "OTM"

    return distance, status


# =========================
# امتیازدهی
# =========================

def calculate_score(
    option_type,
    distance,
    status,
    volume,
    time_value_percent
):

    score = 0

    # وضعیت قرارداد
    if status == "ATM":
        score += 40

    elif status == "ITM":
        score += 30

    elif status == "OTM":
        score += 15

    # فاصله کمتر = بهتر
    if distance <= 2:
        score += 25

    elif distance <= 5:
        score += 18

    elif distance <= 8:
        score += 10

    # حجم
    if volume >= 1000:
        score += 20

    elif volume >= 500:
        score += 15

    elif volume >= 100:
        score += 10

    elif volume >= 50:
        score += 5

    # Time Value
    if time_value_percent >= 70:
        score += 15

    elif time_value_percent >= 50:
        score += 10

    elif time_value_percent >= 30:
        score += 5

    return score


# =========================
# MAIN
# =========================

def main():

    print("=" * 110)
    print("        IRAN OPTIONS SCANNER")
    print("=" * 110)

    print(
        "تاریخ امروز:",
        today_jalali()
    )

    print("\nدر حال دریافت نمادها...")

    symbols = get_all_symbols()

    options = []

    # -------------------------
    # پیدا کردن اختیارها
    # -------------------------

    for s in symbols:

        name = s.get("name", "")
        description = s.get("description", "")
        ticker = s.get("ticker", "")

        if not (
            name.startswith("ط")
            or
            name.startswith("ض")
        ):
            continue

        parsed = parse_option(
            description,
            name
        )

        if not parsed:
            continue

        # حذف قرارداد منقضی
        if not is_active_expiry(
            parsed["expiry"]
        ):
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
        "\nاختیارهای فعال پیدا شده:",
        len(options)
    )

    # -------------------------
    # دریافت اطلاعات قراردادها
    # -------------------------

    results = []

    for i, op in enumerate(options, 1):

        print(
            f"\rدریافت اطلاعات {i}/{len(options)}",
            end="",
            flush=True
        )

        try:

            d = get_info(
                op["ticker"]
            )

            if not d:
                continue

            option_price = float(
                d.get("price") or 0
            )

            volume = 0

            for box in d.get(
                "boxes",
                []
            ):

                title = box.get(
                    "title",
                    ""
                )

                value = box.get(
                    "value",
                    ""
                )

                if "حجم معاملات" in title:

                    try:

                        volume = float(
                            str(value)
                            .replace(",", "")
                        )

                    except:

                        volume = 0

            # حذف قراردادهای بدون قیمت
            if option_price < MIN_OPTION_PRICE:
                continue

            # حذف قراردادهای کم حجم
            if volume < MIN_VOLUME:
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

    print(
        "قراردادهای قابل بررسی:",
        len(results)
    )

    # -------------------------
    # قیمت دارایی‌های پایه
    # -------------------------

    underlying_prices = {}

    targets = [
        "خودرو",
        "اهرم",
        "شستا",
        "وبملت"
    ]

    for s in symbols:

        name = s.get(
            "name",
            ""
        )

        if name not in targets:
            continue

        try:

            d = get_info(
                s["ticker"]
            )

            if d:

                price = float(
                    d.get("price") or 0
                )

                if price > 0:

                    underlying_prices[
                        name
                    ] = price

        except:

            pass

    print("قیمت پایه‌ها:")

    for name, price in underlying_prices.items():

        print(
            f"  {name}: {price:.0f}"
        )

    # -------------------------
    # محاسبات نهایی
    # -------------------------

    final = []

    for x in results:

        underlying_price = (
            underlying_prices.get(
                x["underlying"]
            )
        )

        if not underlying_price:
            continue

        strike = x["strike"]

        option_price = x[
            "option_price"
        ]

        # Intrinsic
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

        # Time Value
        time_value = (
            option_price - intrinsic
        )

        # اگر قیمت قرارداد از ارزش ذاتی کمتر
        # باشد، داده برای سیگنال مناسب نیست
        if time_value <= 0:
            continue

        time_value_percent = (
            time_value / option_price
        ) * 100

        distance, moneyness = (
            calculate_moneyness(
                x["type"],
                underlying_price,
                strike
            )
        )

        # حذف قراردادهای خیلی دور
        if distance > MAX_DISTANCE_PERCENT:
            continue

        score = calculate_score(
            x["type"],
            distance,
            moneyness,
            x["volume"],
            time_value_percent
        )

        x["underlying_price"] = (
            underlying_price
        )

        x["intrinsic"] = intrinsic

        x["time_value"] = (
            time_value
        )

        x["time_value_percent"] = (
            time_value_percent
        )

        x["distance"] = distance

        x["moneyness"] = (
            moneyness
        )

        x["score"] = score

        final.append(x)

    # =========================
    # تفکیک CALL و PUT
    # =========================

    calls = [
        x for x in final
        if x["type"] == "CALL"
    ]

    puts = [
        x for x in final
        if x["type"] == "PUT"
    ]

    # مرتب‌سازی
    calls.sort(
        key=lambda x: (
            x["score"],
            x["volume"],
            -x["distance"]
        ),
        reverse=True
    )

    puts.sort(
        key=lambda x: (
            x["score"],
            x["volume"],
            -x["distance"]
        ),
        reverse=True
    )

    calls = calls[:TOP_N]
    puts = puts[:TOP_N]

    # =========================
    # چاپ CALL
    # =========================

    print("\n")
    print("=" * 110)
    print("                 TOP CALL — اختیار خرید (ط)")
    print("=" * 110)

    print(
        f"{'نماد':<14}"
        f"{'پایه':<10}"
        f"{'Strike':<9}"
        f"{'قیمت':<9}"
        f"{'فاصله%':<9}"
        f"{'TV%':<8}"
        f"{'حجم':<10}"
        f"{'وضعیت':<8}"
        f"{'Score':<7}"
        f"{'سررسید':<12}"
    )

    print("-" * 110)

    for x in calls:

        print(

            f"{x['name']:<14}"

            f"{x['underlying_price']:<10.0f}"

            f"{x['strike']:<9}"

            f"{x['option_price']:<9.0f}"

            f"{x['distance']:<9.2f}"

            f"{x['time_value_percent']:<8.1f}"

            f"{x['volume']:<10.0f}"

            f"{x['moneyness']:<8}"

            f"{x['score']:<7}"

            f"{x['expiry']:<12}"

        )

    # =========================
    # چاپ PUT
    # =========================

    print("\n")
    print("=" * 110)
    print("                 TOP PUT — اختیار فروش (ض)")
    print("=" * 110)

    print(
        f"{'نماد':<14}"
        f"{'پایه':<10}"
        f"{'Strike':<9}"
        f"{'قیمت':<9}"
        f"{'فاصله%':<9}"
        f"{'TV%':<8}"
        f"{'حجم':<10}"
        f"{'وضعیت':<8}"
        f"{'Score':<7}"
        f"{'سررسید':<12}"
    )

    print("-" * 110)

    for x in puts:

        print(

            f"{x['name']:<14}"

            f"{x['underlying_price']:<10.0f}"

            f"{x['strike']:<9}"

            f"{x['option_price']:<9.0f}"

            f"{x['distance']:<9.2f}"

            f"{x['time_value_percent']:<8.1f}"

            f"{x['volume']:<10.0f}"

            f"{x['moneyness']:<8}"

            f"{x['score']:<7}"

            f"{x['expiry']:<12}"

        )

    # =========================
    # خلاصه
    # =========================

    print("\n")
    print("=" * 110)

    print(
        "قراردادهای نهایی:",
        len(final)
    )

    print(
        "CALL:",
        len(calls)
    )

    print(
        "PUT:",
        len(puts)
    )

    print("=" * 110)


if __name__ == "__main__":

    main()