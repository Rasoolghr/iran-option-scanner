import requests
import re
import jdatetime
import json


# =========================================================
# SETTINGS
# =========================================================

BASE = "https://market.chartix.ir"

MIN_VOLUME = 50
MIN_OPTION_PRICE = 10
MAX_DISTANCE_PERCENT = 10
ATM_PERCENT = 3
TOP_N = 5

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0"
})


# =========================================================
# GET ALL SYMBOLS
# =========================================================

def get_all_symbols():

    url = f"{BASE}/symbol/all"

    r = session.get(url, timeout=30)
    r.raise_for_status()

    data = r.json()

    return data["data"]["symbols"]


# =========================================================
# GET SYMBOL INFO
# =========================================================

def get_info(ticker):

    url = f"{BASE}/symbol/info/saham/{ticker}"

    try:
        r = session.get(url, timeout=30)

        if r.status_code != 200:
            return None

        return r.json()

    except Exception as e:

        print("INFO ERROR:", ticker, e)

        return None


# =========================================================
# TODAY JALALI
# =========================================================

def today_jalali():

    today = jdatetime.date.today()

    return today.strftime("%Y/%m/%d")


# =========================================================
# ACTIVE EXPIRY
# =========================================================

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


# =========================================================
# FIND SYMBOL
# =========================================================

def find_symbol(symbols, name):

    for s in symbols:

        if s.get("name") == name:
            return s

    return None


# =========================================================
# OPTION PARSER
# =========================================================

def parse_option(description, name):

    if not description:
        return None

    m = re.search(
        r"-(\d+)-(\d{4}/\d{2}/\d{2})",
        description
    )

    if not m:
        return None

    strike = int(m.group(1))

    expiry = m.group(2)

    option_type = None

    # طبق داده پروژه:
    # ط = PUT
    # ض = CALL

    if name.startswith("ط"):

        option_type = "PUT"

    elif name.startswith("ض"):

        option_type = "CALL"

    if not option_type:
        return None

    return {
        "strike": strike,
        "expiry": expiry,
        "type": option_type
    }


# =========================================================
# UNDERLYING MAPPING
# =========================================================

def underlying_name(option_name):

    mapping = {

        "خودرو": "خودرو",
        "هرم": "اهرم",
        "ستا": "شستا",
        "ملت": "وبملت"

    }

    for key, value in mapping.items():

        if option_name.startswith("ط" + key):
            return value

        if option_name.startswith("ض" + key):
            return value

    return None


# =========================================================
# GET VOLUME
# =========================================================

def get_volume(info):

    if not info:
        return 0

    boxes = info.get("boxes", [])

    for box in boxes:

        title = str(box.get("title", ""))

        if "حجم معاملات" in title:

            value = box.get("value")

            try:

                return float(
                    str(value)
                    .replace(",", "")
                    .replace("٬", "")
                )

            except:

                pass

    return 0


# =========================================================
# GET PRICE
# =========================================================

def get_price(info):

    if not info:
        return None

    value = info.get("price")

    try:

        return float(value)

    except:

        return None


# =========================================================
# GET UNDERLYING PRICE
# =========================================================

def get_underlying_price(symbols, underlying):

    symbol = find_symbol(symbols, underlying)

    if not symbol:
        return None

    ticker = symbol.get("ticker")

    info = get_info(ticker)

    if not info:
        return None

    return get_price(info)


# =========================================================
# CALCULATE OPTION DATA
# =========================================================

def calculate_option(option_price, underlying_price, strike, option_type):

    if option_type == "CALL":

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

    if option_price <= 0:
        return None

    if time_value <= 0:
        return None

    tv_percent = (
        time_value / option_price
    ) * 100

    distance = (
        abs(underlying_price - strike)
        / underlying_price
    ) * 100

    # Moneyness

    if distance <= ATM_PERCENT:

        moneyness = "ATM"

    else:

        if option_type == "CALL":

            if underlying_price > strike:
                moneyness = "ITM"
            else:
                moneyness = "OTM"

        else:

            if underlying_price < strike:
                moneyness = "ITM"
            else:
                moneyness = "OTM"

    return {

        "intrinsic": intrinsic,
        "time_value": time_value,
        "tv_percent": tv_percent,
        "distance": distance,
        "moneyness": moneyness

    }


# =========================================================
# SCORE
# =========================================================

def calculate_score(
    moneyness,
    distance,
    volume,
    tv_percent
):

    score = 0

    # Moneyness

    if moneyness == "ATM":

        score += 40

    elif moneyness == "ITM":

        score += 30

    else:

        score += 15

    # Distance

    if distance <= 2:

        score += 25

    elif distance <= 5:

        score += 18

    elif distance <= 8:

        score += 10

    # Volume

    if volume >= 1000:

        score += 20

    elif volume >= 500:

        score += 15

    elif volume >= 100:

        score += 10

    elif volume >= 50:

        score += 5

    # Time value

    if tv_percent >= 70:

        score += 15

    elif tv_percent >= 50:

        score += 10

    elif tv_percent >= 30:

        score += 5

    return score


# =========================================================
# TEST SYMBOL INFO
# =========================================================

def test_symbol_info(symbols, names):

    print()
    print("=" * 70)
    print("SYMBOL INFO TEST")
    print("=" * 70)

    for name in names:

        symbol = find_symbol(symbols, name)

        if not symbol:

            print(name, "NOT FOUND")
            continue

        ticker = symbol.get("ticker")

        info = get_info(ticker)

        print()
        print(name)
        print("Ticker:", ticker)

        if not info:

            print("INFO FAILED")
            continue

        print(
            "KEYS:",
            list(info.keys())
        )

        print(
            "Price:",
            info.get("price")
        )

        print(
            "Description:",
            info.get("description")
        )


# =========================================================
# TEST POSSIBLE CHART ENDPOINTS
# =========================================================

def test_chart_endpoints(symbols):

    print()
    print("=" * 70)
    print("CHARTIX CANDLE ENDPOINT TEST")
    print("=" * 70)

    symbol = find_symbol(
        symbols,
        "وبملت"
    )

    if not symbol:

        print("وبملت پیدا نشد")

        return

    ticker = symbol.get("ticker")

    print("Ticker:", ticker)

    endpoints = [

        f"/symbol/chart/{ticker}",
        f"/symbol/charts/{ticker}",
        f"/symbol/history/{ticker}",
        f"/symbol/candle/{ticker}",
        f"/symbol/candles/{ticker}",
        f"/symbol/ohlc/{ticker}",

        f"/chart/{ticker}",
        f"/charts/{ticker}",
        f"/history/{ticker}",
        f"/candles/{ticker}",
        f"/ohlc/{ticker}",

    ]

    for endpoint in endpoints:

        url = BASE + endpoint

        try:

            r = session.get(
                url,
                timeout=10
            )

            content_type = r.headers.get(
                "content-type",
                ""
            )

            print()
            print(
                f"{endpoint:<45} "
                f"STATUS={r.status_code} "
                f"TYPE={content_type}"
            )

            if r.status_code == 200:

                text = r.text[:2000]

                print("  RESPONSE:")
                print(text)

        except Exception as e:

            print()
            print(
                f"{endpoint:<45} "
                f"ERROR={e}"
            )


# =========================================================
# DISCOVER CHART/CANDLE KEYS IN INFO
# =========================================================

def inspect_chart_keys(symbols):

    print()
    print("=" * 70)
    print("CHART DATA KEY INSPECTION")
    print("=" * 70)

    targets = [
        "طملت8075",
        "وبملت"
    ]

    keywords = [
        "chart",
        "charts",
        "candle",
        "candles",
        "ohlc",
        "history",
        "historical",
        "series",
        "timeseries",
        "timeSeries",
        "priceHistory",
        "chartData",
        "data"
    ]

    for name in targets:

        symbol = find_symbol(
            symbols,
            name
        )

        if not symbol:

            print()
            print(name, "NOT FOUND")
            continue

        ticker = symbol.get("ticker")

        info = get_info(ticker)

        print()
        print(name)
        print("Ticker:", ticker)

        if not info:

            print("INFO FAILED")
            continue

        found = []

        for key, value in info.items():

            key_lower = str(key).lower()

            for keyword in keywords:

                if keyword.lower() in key_lower:

                    found.append(key)

                    break

        if found:

            print(
                "Possible chart keys:",
                found
            )

            for key in found:

                try:

                    print(
                        "\nKEY:",
                        key
                    )

                    print(
                        json.dumps(
                            info.get(key),
                            ensure_ascii=False,
                            indent=2
                        )[:3000]
                    )

                except:

                    print(
                        str(info.get(key))[:3000]
                    )

        else:

            print(
                "کلید واضحی برای Chart/Candle پیدا نشد."
            )


# =========================================================
# MAIN
# =========================================================

def main():

    print()
    print("=" * 70)
    print("IRAN OPTIONS SCANNER")
    print("=" * 70)

    print(
        "تاریخ امروز:",
        today_jalali()
    )

    # -----------------------------------------------------
    # GET SYMBOLS
    # -----------------------------------------------------

    try:

        symbols = get_all_symbols()

    except Exception as e:

        print(
            "ERROR GETTING SYMBOLS:",
            e
        )

        return

    print(
        "تعداد کل نمادها:",
        len(symbols)
    )

    # -----------------------------------------------------
    # FIND ACTIVE OPTIONS
    # -----------------------------------------------------

    options = []

    for symbol in symbols:

        name = symbol.get("name", "")

        description = symbol.get(
            "description",
            ""
        )

        parsed = parse_option(
            description,
            name
        )

        if not parsed:
            continue

        if not is_active_expiry(
            parsed["expiry"]
        ):
            continue

        symbol_data = {
            **symbol,
            **parsed
        }

        options.append(
            symbol_data
        )

    print(
        "اختیارهای فعال پیدا شده:",
        len(options)
    )

    # -----------------------------------------------------
    # UNDERLYING PRICES
    # -----------------------------------------------------

    underlyings = [
        "خودرو",
        "اهرم",
        "شستا",
        "وبملت"
    ]

    underlying_prices = {}

    print()
    print("قیمت پایه‌ها:")

    for underlying in underlyings:

        price = get_underlying_price(
            symbols,
            underlying
        )

        underlying_prices[
            underlying
        ] = price

        print(
            f"  {underlying}:",
            price
        )

    # -----------------------------------------------------
    # SCAN OPTIONS
    # -----------------------------------------------------

    candidates = []

    for option in options:

        name = option.get(
            "name",
            ""
        )

        underlying = underlying_name(
            name
        )

        if not underlying:
            continue

        underlying_price = (
            underlying_prices.get(
                underlying
            )
        )

        if not underlying_price:
            continue

        ticker = option.get(
            "ticker"
        )

        info = get_info(ticker)

        if not info:
            continue

        option_price = get_price(info)

        if option_price is None:
            continue

        if option_price < MIN_OPTION_PRICE:
            continue

        volume = get_volume(info)

        if volume < MIN_VOLUME:
            continue

        calc = calculate_option(
            option_price,
            underlying_price,
            option["strike"],
            option["type"]
        )

        if not calc:
            continue

        if calc["distance"] > MAX_DISTANCE_PERCENT:
            continue

        score = calculate_score(
            calc["moneyness"],
            calc["distance"],
            volume,
            calc["tv_percent"]
        )

        candidate = {

            "name": name,
            "ticker": ticker,

            "underlying": underlying,

            "underlying_price":
                underlying_price,

            "strike":
                option["strike"],

            "price":
                option_price,

            "volume":
                volume,

            "expiry":
                option["expiry"],

            "type":
                option["type"],

            "intrinsic":
                calc["intrinsic"],

            "time_value":
                calc["time_value"],

            "tv_percent":
                calc["tv_percent"],

            "distance":
                calc["distance"],

            "moneyness":
                calc["moneyness"],

            "score":
                score

        }

        candidates.append(
            candidate
        )

    print()
    print(
        "قراردادهای قابل بررسی:",
        len(candidates)
    )

    # -----------------------------------------------------
    # SORT
    # -----------------------------------------------------

    calls = [
        x for x in candidates
        if x["type"] == "CALL"
    ]

    puts = [
        x for x in candidates
        if x["type"] == "PUT"
    ]

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

    # -----------------------------------------------------
    # PRINT CALLS
    # -----------------------------------------------------

    print()
    print(
        "TOP CALL — اختیار خرید (ض)"
    )

    if not calls:

        print(
            "مورد مناسبی پیدا نشد."
        )

    else:

        for x in calls[:TOP_N]:

            print(
                f"{x['name']:<15}"
                f" پایه={x['underlying']:<6}"
                f" پایه={x['underlying_price']:<10}"
                f" Strike={x['strike']:<8}"
                f" Price={x['price']:<8}"
                f" Vol={x['volume']:<8}"
                f" TV={x['tv_percent']:.1f}% "
                f"{x['moneyness']:<4}"
                f" Score={x['score']:<4}"
                f" Exp={x['expiry']}"
            )

    # -----------------------------------------------------
    # PRINT PUTS
    # -----------------------------------------------------

    print()
    print(
        "TOP PUT — اختیار فروش (ط)"
    )

    if not puts:

        print(
            "مورد مناسبی پیدا نشد."
        )

    else:

        for x in puts[:TOP_N]:

            print(
                f"{x['name']:<15}"
                f" پایه={x['underlying']:<6}"
                f" پایه={x['underlying_price']:<10}"
                f" Strike={x['strike']:<8}"
                f" Price={x['price']:<8}"
                f" Vol={x['volume']:<8}"
                f" TV={x['tv_percent']:.1f}% "
                f"{x['moneyness']:<4}"
                f" Score={x['score']:<4}"
                f" Exp={x['expiry']}"
            )

    # -----------------------------------------------------
    # TEST CURRENT INFO
    # -----------------------------------------------------

    inspect_chart_keys(
        symbols
    )

    # -----------------------------------------------------
    # TEST CANDLE ENDPOINTS
    # -----------------------------------------------------

    test_chart_endpoints(
        symbols
    )

    # -----------------------------------------------------
    # FINAL SUMMARY
    # -----------------------------------------------------

    final = (
        calls[:TOP_N]
        +
        puts[:TOP_N]
    )

    print()
    print("=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)

    print(
        "قراردادهای نهایی:",
        len(final)
    )

    print(
        "CALL:",
        len(calls[:TOP_N])
    )

    print(
        "PUT:",
        len(puts[:TOP_N])
    )

    print()
    print("=" * 70)
    print("END")
    print("=" * 70)


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    main()