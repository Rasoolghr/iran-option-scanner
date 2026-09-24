import requests
import re

BASE = "https://market.chartix.ir"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

session = requests.Session()
session.headers.update(HEADERS)

# =============================
# SETTINGS
# =============================

MIN_VOLUME = 50
MIN_OPTION_PRICE = 10
MAX_DISTANCE_PERCENT = 10
ATM_PERCENT = 3
TOP_N = 5


# =============================
# GET ALL SYMBOLS
# =============================

def get_all_symbols():

    r = session.get(
        f"{BASE}/symbol/all",
        timeout=30
    )

    r.raise_for_status()

    return r.json()["data"]["symbols"]


# =============================
# GET SYMBOL INFO
# =============================

def get_info(ticker):

    try:

        r = session.get(
            f"{BASE}/symbol/info/saham/{ticker}",
            timeout=30
        )

        if r.status_code != 200:
            return None

        return r.json()

    except Exception:

        return None


# =============================
# PARSE OPTION
# =============================

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


# =============================
# FIND UNDERLYING
# =============================

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


# =============================
# GET VOLUME
# =============================

def get_volume(data):

    volume = 0

    for box in data.get("boxes", []):

        title = box.get("title", "")
        value = box.get("value", "")

        if "حجم معاملات" in title:

            try:

                volume = float(
                    str(value)
                    .replace(",", "")
                    .replace("٬", "")
                )

            except Exception:

                volume = 0

    return volume


# =============================
# SCORE
# =============================

def calculate_score(
    distance,
    volume,
    tv_percent
):

    score = 0

    # -------------------------
    # Distance from ATM
    # -------------------------

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

    # -------------------------
    # Volume
    # -------------------------

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

    # -------------------------
    # Time Value
    # -------------------------

    if tv_percent >= 80:

        score += 20

    elif tv_percent >= 60:

        score += 18

    elif tv_percent >= 40:

        score += 15

    elif tv_percent >= 20:

        score += 10

    else:

        score += 5

    return score


# =============================
# MAIN
# =============================

def main():

    print("در حال دریافت نمادها...")

    symbols = get_all_symbols()

    options = []

    # =========================
    # FIND OPTIONS
    # =========================

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

        underlying = get_underlying_name(
            name
        )

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
        "اختیارهای پیدا شده:",
        len(options)
    )

    # =========================
    # GET OPTION DATA
    # =========================

    results = []

    for i, op in enumerate(options, 1):

        print(
            f"\rدریافت اطلاعات {i}/{len(options)}",
            end="",
            flush=True
        )

        data = get_info(
            op["ticker"]
        )

        if not data:

            continue

        try:

            price = float(
                data.get("price") or 0
            )

        except Exception:

            price = 0

        volume = get_volume(data)

        # ---------------------
        # BASIC FILTER
        # ---------------------

        if price < MIN_OPTION_PRICE:

            continue

        if volume < MIN_VOLUME:

            continue

        results.append({

            "name": op["name"],

            "type": op["type"],

            "strike": op["strike"],

            "expiry": op["expiry"],

            "underlying": op["underlying"],

            "option_price": price,

            "volume": volume

        })

    print("\n")

    # =========================
    # UNDERLYING PRICES
    # =========================

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

        data = get_info(
            s["ticker"]
        )

        if not data:

            continue

        try:

            underlying_prices[name] = float(
                data.get("price") or 0
            )

        except Exception:

            pass

    print("قیمت پایه‌ها:")

    for name, price in underlying_prices.items():

        print(
            f"  {name}: {price:.0f}"
        )

    # =========================
    # CALCULATE OPTION METRICS
    # =========================

    final = []

    for x in results:

        underlying_price = underlying_prices.get(
            x["underlying"]
        )

        if not underlying_price:

            continue

        strike = x["strike"]

        option_price = x["option_price"]

        # ---------------------
        # INTRINSIC VALUE
        # ---------------------

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

        # ---------------------
        # TIME VALUE
        # ---------------------

        time_value = (
            option_price - intrinsic
        )

        if time_value <= 0:

            continue

        tv_percent = (
            time_value / option_price
        ) * 100

        # ---------------------
        # DISTANCE
        # ---------------------

        distance_percent = (

            abs(
                underlying_price - strike
            )
            / underlying_price

        ) * 100

        if distance_percent > MAX_DISTANCE_PERCENT:

            continue

        # ---------------------
        # MONEYNESS
        # ---------------------

        if distance_percent <= ATM_PERCENT:

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

        # ---------------------
        # SCORE
        # ---------------------

        score = calculate_score(

            distance_percent,

            x["volume"],

            tv_percent

        )

        x["underlying_price"] = underlying_price

        x["intrinsic"] = intrinsic

        x["time_value"] = time_value

        x["tv_percent"] = tv_percent

        x["distance_percent"] = distance_percent

        x["moneyness"] = moneyness

        x["score"] = score

        final.append(x)

    # =========================
    # CALL / PUT
    # =========================

    calls = [

        x for x in final

        if x["type"] == "CALL"

    ]

    puts = [

        x for x in final

        if x["type"] == "PUT"

    ]

    # =========================
    # SORT
    # =========================

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

    # =========================
    # PRINT TABLE
    # =========================

    def print_table(title, data):

        print("=" * 125)

        print(
            f"                 {title}"
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

            f"{'وضعیت':<8}"

            f"{'Score':<7}"

            f"{'سررسید':<12}"

        )

        print("-" * 125)

        for x in data[:TOP_N]:

            print(

                f"{x['name']:<12}"

                f"{x['underlying_price']:<9.0f}"

                f"{x['strike']:<8}"

                f"{x['option_price']:<8.0f}"

                f"{x['distance_percent']:<9.2f}"

                f"{x['tv_percent']:<8.1f}"

                f"{x['volume']:<10.0f}"

                f"{x['moneyness']:<8}"

                f"{x['score']:<7}"

                f"{x['expiry']:<12}"

            )

    # =========================
    # OUTPUT
    # =========================

    print_table(
        "TOP CALL",
        calls
    )

    print()

    print_table(
        "TOP PUT",
        puts
    )

    print()

    print("=" * 125)

    print(
        "قراردادهای قابل معامله پس از فیلتر:",
        len(results)
    )

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

    print("=" * 125)


# =============================
# RUN
# =============================

if __name__ == "__main__":

    main()