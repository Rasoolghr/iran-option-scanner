import requests
import re
import jdatetime
import json
import time
from datetime import datetime, timedelta


# =========================================================
# SETTINGS
# =========================================================

BASE = "https://market.chartix.ir"

DATAFEED_BASE = "https://datafeed.chartix.ir/api/v1"

MIN_VOLUME = 50
MIN_OPTION_PRICE = 10
MAX_DISTANCE_PERCENT = 10
ATM_PERCENT = 3
TOP_N = 5

CANDLE_COUNT = 300

session = requests.Session()

session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/140.0 Safari/537.36"
    ),
    "Accept": "*/*",
})


# =========================================================
# GET ALL SYMBOLS
# =========================================================

def get_all_symbols():

    url = f"{BASE}/symbol/all"

    r = session.get(
        url,
        timeout=30
    )

    r.raise_for_status()

    return r.json()["data"]["symbols"]


# =========================================================
# GET SYMBOL INFO
# =========================================================

def get_info(ticker):

    url = f"{BASE}/symbol/info/saham/{ticker}"

    try:

        r = session.get(
            url,
            timeout=30
        )

        if r.status_code != 200:
            return None

        return r.json()

    except Exception as e:

        print(
            "INFO ERROR:",
            ticker,
            e
        )

        return None


# =========================================================
# JALALI DATE
# =========================================================

def today_jalali():

    return jdatetime.date.today().strftime(
        "%Y/%m/%d"
    )


# =========================================================
# ACTIVE EXPIRY
# =========================================================

def is_active_expiry(expiry):

    try:

        expiry_date = (
            jdatetime.datetime
            .strptime(
                expiry,
                "%Y/%m/%d"
            )
            .date()
        )

        return expiry_date >= jdatetime.date.today()

    except:

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
# PARSE OPTION
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

    # پروژه:
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
# UNDERLYING
# =========================================================

def underlying_name(option_name):

    mapping = {

        "خودرو": "خودرو",
        "هرم": "اهرم",
        "ستا": "شستا",
        "ملت": "وبملت"

    }

    for key, value in mapping.items():

        if option_name.startswith(
            "ط" + key
        ):

            return value

        if option_name.startswith(
            "ض" + key
        ):

            return value

    return None


# =========================================================
# PRICE
# =========================================================

def get_price(info):

    if not info:
        return None

    try:

        return float(
            info.get("price")
        )

    except:

        return None


# =========================================================
# VOLUME
# =========================================================

def get_volume(info):

    if not info:
        return 0

    for box in info.get(
        "boxes",
        []
    ):

        title = str(
            box.get(
                "title",
                ""
            )
        )

        if "حجم معاملات" in title:

            value = box.get(
                "value"
            )

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
# OPTION CALCULATION
# =========================================================

def calculate_option(
    option_price,
    underlying_price,
    strike,
    option_type
):

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

    time_value = (
        option_price - intrinsic
    )

    if option_price <= 0:
        return None

    if time_value <= 0:
        return None

    tv_percent = (
        time_value
        / option_price
    ) * 100

    distance = (
        abs(
            underlying_price - strike
        )
        / underlying_price
    ) * 100

    if distance <= ATM_PERCENT:

        moneyness = "ATM"

    elif option_type == "CALL":

        moneyness = (
            "ITM"
            if underlying_price > strike
            else "OTM"
        )

    else:

        moneyness = (
            "ITM"
            if underlying_price < strike
            else "OTM"
        )

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

    if moneyness == "ATM":

        score += 40

    elif moneyness == "ITM":

        score += 30

    else:

        score += 15

    if distance <= 2:

        score += 25

    elif distance <= 5:

        score += 18

    elif distance <= 8:

        score += 10

    if volume >= 1000:

        score += 20

    elif volume >= 500:

        score += 15

    elif volume >= 100:

        score += 10

    elif volume >= 50:

        score += 5

    if tv_percent >= 70:

        score += 15

    elif tv_percent >= 50:

        score += 10

    elif tv_percent >= 30:

        score += 5

    return score


# =========================================================
# UNDERLYING PRICE
# =========================================================

def get_underlying_price(
    symbols,
    underlying
):

    symbol = find_symbol(
        symbols,
        underlying
    )

    if not symbol:
        return None

    info = get_info(
        symbol["ticker"]
    )

    return get_price(info)


# =========================================================
# SCAN OPTIONS
# =========================================================

def scan_options(symbols):

    options = []

    for symbol in symbols:

        name = symbol.get(
            "name",
            ""
        )

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

        options.append({
            **symbol,
            **parsed
        })

    print(
        "اختیارهای فعال پیدا شده:",
        len(options)
    )

    underlying_names = [

        "خودرو",
        "اهرم",
        "شستا",
        "وبملت"

    ]

    underlying_prices = {}

    print()
    print("قیمت پایه‌ها:")

    for name in underlying_names:

        price = get_underlying_price(
            symbols,
            name
        )

        underlying_prices[name] = price

        print(
            f"  {name}: {price}"
        )

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

        info = get_info(
            option["ticker"]
        )

        if not info:
            continue

        option_price = get_price(
            info
        )

        if option_price is None:
            continue

        if option_price < MIN_OPTION_PRICE:
            continue

        volume = get_volume(
            info
        )

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

        candidates.append({

            "name": name,
            "ticker": option["ticker"],
            "underlying": underlying,
            "underlying_price": underlying_price,
            "strike": option["strike"],
            "price": option_price,
            "volume": volume,
            "expiry": option["expiry"],
            "type": option["type"],
            "intrinsic": calc["intrinsic"],
            "time_value": calc["time_value"],
            "tv_percent": calc["tv_percent"],
            "distance": calc["distance"],
            "moneyness": calc["moneyness"],
            "score": score

        })

    return candidates


# =========================================================
# PRINT OPTIONS
# =========================================================

def print_options(candidates):

    calls = [
        x for x in candidates
        if x["type"] == "CALL"
    ]

    puts = [
        x for x in candidates
        if x["type"] == "PUT"
    ]

    key_func = lambda x: (
        x["score"],
        x["volume"],
        -x["distance"]
    )

    calls.sort(
        key=key_func,
        reverse=True
    )

    puts.sort(
        key=key_func,
        reverse=True
    )

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

    return calls, puts


# =========================================================
# GET CHARTIX DATAFEED SERVER
# =========================================================

def get_datafeed_server():

    print()
    print("=" * 70)
    print("CHARTIX DATAFEED SERVER")
    print("=" * 70)

    url = (
        "https://info.chartix.ir"
        "/api/v1/get-server"
    )

    try:

        r = session.get(
            url,
            timeout=20
        )

        print(
            "STATUS:",
            r.status_code
        )

        print(
            "CONTENT TYPE:",
            r.headers.get(
                "content-type",
                ""
            )
        )

        print(
            "RESPONSE:"
        )

        print(
            r.text[:3000]
        )

        if r.status_code != 200:

            return None

        try:

            data = r.json()

            print()
            print(
                "JSON:"
            )

            print(
                json.dumps(
                    data,
                    ensure_ascii=False,
                    indent=2
                )[:5000]
            )

            return data

        except:

            return r.text

    except Exception as e:

        print(
            "SERVER ERROR:",
            repr(e)
        )

        return None


# =========================================================
# TEST SYMBOL API
# =========================================================

def test_datafeed_symbol(ticker):

    print()
    print(
        "-" * 70
    )

    print(
        "DATAFEED SYMBOL:",
        ticker
    )

    url = (
        f"{DATAFEED_BASE}/symbols"
        f"?symbol={ticker}"
    )

    try:

        r = session.get(
            url,
            timeout=20
        )

        print(
            "URL:",
            url
        )

        print(
            "STATUS:",
            r.status_code
        )

        print(
            "RESPONSE:"
        )

        print(
            r.text[:3000]
        )

        if r.status_code == 200:

            try:

                return r.json()

            except:

                return None

    except Exception as e:

        print(
            "SYMBOL ERROR:",
            repr(e)
        )

    return None


# =========================================================
# GET 5 MINUTE HISTORY
# =========================================================

def get_history(
    ticker,
    countback=CANDLE_COUNT
):

    print()
    print(
        "-" * 70
    )

    print(
        "5 MINUTE HISTORY:",
        ticker
    )

    now = int(
        time.time()
    )

    # حدود 7 روز
    from_time = int(
        (
            datetime.utcnow()
            - timedelta(days=7)
        ).timestamp()
    )

    to_time = now

    resolution = "5"

    # id فعلاً یک شناسه ساده
    # برای تست History
    socket_id = str(
        int(
            time.time() * 1000
        )
    )

    params = {

        "symbol": ticker,

        "resolution":
            resolution,

        "from":
            from_time,

        "to":
            to_time,

        "countback":
            countback,

        "id":
            socket_id,

        "adj":
            "0"

    }

    url = (
        f"{DATAFEED_BASE}/history"
    )

    print(
        "URL:",
        url
    )

    print(
        "PARAMS:"
    )

    print(
        json.dumps(
            params,
            ensure_ascii=False,
            indent=2
        )
    )

    try:

        r = session.get(
            url,
            params=params,
            timeout=30
        )

        print()
        print(
            "STATUS:",
            r.status_code
        )

        print(
            "FINAL URL:",
            r.url
        )

        print()
        print(
            "RAW RESPONSE:"
        )

        print(
            r.text[:5000]
        )

        if r.status_code != 200:

            return None

        try:

            data = r.json()

            print()
            print(
                "JSON STRUCTURE:"
            )

            if isinstance(
                data,
                dict
            ):

                print(
                    list(
                        data.keys()
                    )
                )

            elif isinstance(
                data,
                list
            ):

                print(
                    "LIST LENGTH:",
                    len(data)
                )

            return data

        except Exception as e:

            print(
                "JSON PARSE ERROR:",
                repr(e)
            )

    except Exception as e:

        print(
            "HISTORY ERROR:",
            repr(e)
        )

    return None


# =========================================================
# PARSE HISTORY
# =========================================================

def inspect_history(data):

    if not data:

        print(
            "هیچ دیتای کندلی دریافت نشد."
        )

        return

    print()
    print(
        "=" * 70
    )
    print(
        "HISTORY STRUCTURE"
    )
    print(
        "=" * 70
    )

    if isinstance(
        data,
        dict
    ):

        for key, value in data.items():

            print()
            print(
                "KEY:",
                key
            )

            if isinstance(
                value,
                list
            ):

                print(
                    "TYPE: LIST"
                )

                print(
                    "LENGTH:",
                    len(value)
                )

                if value:

                    print(
                        "FIRST:"
                    )

                    print(
                        json.dumps(
                            value[0],
                            ensure_ascii=False,
                            indent=2
                        )[:2000]
                    )

                    print(
                        "LAST:"
                    )

                    print(
                        json.dumps(
                            value[-1],
                            ensure_ascii=False,
                            indent=2
                        )[:2000]
                    )

            else:

                print(
                    "TYPE:",
                    type(value).__name__
                )

                print(
                    str(value)[:2000]
                )

    elif isinstance(
        data,
        list
    ):

        print(
            "LIST LENGTH:",
            len(data)
        )

        for item in data[:3]:

            print(
                json.dumps(
                    item,
                    ensure_ascii=False,
                    indent=2
                )[:2000]
            )


# =========================================================
# TEST SELECTED SYMBOLS
# =========================================================

def test_history_symbols(symbols):

    print()
    print("=" * 70)
    print(
        "5-MINUTE CANDLE TEST"
    )
    print("=" * 70)

    names = [

        "وبملت",
        "خودرو",
        "شستا",
        "اهرم",
        "طملت8075",
        "طستا8061"

    ]

    for name in names:

        symbol = find_symbol(
            symbols,
            name
        )

        if not symbol:

            print()
            print(
                name,
                "NOT FOUND"
            )

            continue

        ticker = symbol.get(
            "ticker"
        )

        print()
        print(
            "===================================="
        )

        print(
            name,
            "=>",
            ticker
        )

        # symbol info from datafeed

        test_datafeed_symbol(
            ticker
        )

        # history

        data = get_history(
            ticker
        )

        inspect_history(
            data
        )


# =========================================================
# MAIN
# =========================================================

def main():

    print()
    print("=" * 70)
    print(
        "IRAN OPTIONS SCANNER"
    )
    print("=" * 70)

    print(
        "تاریخ امروز:",
        today_jalali()
    )

    # -----------------------------------------------------
    # SYMBOLS
    # -----------------------------------------------------

    try:

        symbols = get_all_symbols()

    except Exception as e:

        print(
            "ERROR GETTING SYMBOLS:",
            repr(e)
        )

        return

    print(
        "تعداد کل نمادها:",
        len(symbols)
    )

    # -----------------------------------------------------
    # OPTION SCAN
    # -----------------------------------------------------

    candidates = scan_options(
        symbols
    )

    print()
    print(
        "قراردادهای قابل بررسی:",
        len(candidates)
    )

    calls, puts = print_options(
        candidates
    )

    # -----------------------------------------------------
    # DATAFEED SERVER
    # -----------------------------------------------------

    get_datafeed_server()

    # -----------------------------------------------------
    # REAL 5 MINUTE HISTORY
    # -----------------------------------------------------

    test_history_symbols(
        symbols
    )

    # -----------------------------------------------------
    # SUMMARY
    # -----------------------------------------------------

    print()
    print("=" * 70)
    print(
        "FINAL SUMMARY"
    )
    print("=" * 70)

    print(
        "قراردادهای نهایی:",
        len(
            calls[:TOP_N]
        )
        +
        len(
            puts[:TOP_N]
        )
    )

    print(
        "CALL:",
        len(
            calls[:TOP_N]
        )
    )

    print(
        "PUT:",
        len(
            puts[:TOP_N]
        )
    )

    print()
    print("=" * 70)
    print(
        "END"
    )
    print("=" * 70)


if __name__ == "__main__":

    main()