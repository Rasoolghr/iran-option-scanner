import requests
import re
import jdatetime
import json
from urllib.parse import urljoin


# =========================================================
# SETTINGS
# =========================================================

BASE = "https://market.chartix.ir"
MAX_BASE = "https://max.chartix.ir"

MIN_VOLUME = 50
MIN_OPTION_PRICE = 10
MAX_DISTANCE_PERCENT = 10
ATM_PERCENT = 3
TOP_N = 5

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
# FIND UNDERLYING PRICE
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
# NEW:
# DISCOVER MAX FRONTEND
# =========================================================

def discover_max_frontend():

    print()
    print("=" * 70)
    print("CHARTIX MAX FRONTEND DISCOVERY")
    print("=" * 70)

    url = (
        f"{MAX_BASE}/dashboard"
        f"?chart=BRS0031"
        f"&type=watch-list"
    )

    print(
        "MAX URL:",
        url
    )

    try:

        r = session.get(
            url,
            timeout=30
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

        if r.status_code != 200:

            print(
                "MAX page failed."
            )

            return []

        html = r.text

        print(
            "HTML SIZE:",
            len(html)
        )

        # -------------------------------------------------
        # Find JS files
        # -------------------------------------------------

        scripts = re.findall(
            r'<script[^>]+src=["\']([^"\']+)["\']',
            html,
            flags=re.I
        )

        # modulepreload / preload
        links = re.findall(
            r'<link[^>]+href=["\']([^"\']+)["\']',
            html,
            flags=re.I
        )

        js_urls = []

        for src in scripts:

            js_urls.append(
                urljoin(
                    MAX_BASE,
                    src
                )
            )

        for href in links:

            if (
                ".js" in href
                or "javascript" in href.lower()
            ):

                js_urls.append(
                    urljoin(
                        MAX_BASE,
                        href
                    )
                )

        # remove duplicates

        js_urls = list(
            dict.fromkeys(
                js_urls
            )
        )

        print()
        print(
            "JS FILES FOUND:",
            len(js_urls)
        )

        for js in js_urls[:50]:

            print(
                js
            )

        return js_urls

    except Exception as e:

        print(
            "MAX DISCOVERY ERROR:",
            repr(e)
        )

        return []


# =========================================================
# SEARCH JAVASCRIPT FOR API ENDPOINTS
# =========================================================

def inspect_javascript(js_urls):

    print()
    print("=" * 70)
    print("SEARCHING CHARTIX JAVASCRIPT FOR CANDLE API")
    print("=" * 70)

    keywords = [

        "candle",
        "candles",
        "ohlc",
        "history",
        "historical",
        "timeframe",
        "interval",
        "chartData",
        "priceHistory",
        "/api/",
        "api/",
        "websocket",
        "socket"

    ]

    found_count = 0

    for index, js_url in enumerate(
        js_urls[:50],
        start=1
    ):

        try:

            r = session.get(
                js_url,
                timeout=30
            )

            if r.status_code != 200:
                continue

            text = r.text

            print()
            print(
                f"[JS {index}] "
                f"{len(text)} bytes"
            )

            # -------------------------------------------------
            # Extract URLs
            # -------------------------------------------------

            urls = re.findall(
                r'https?://[^"\']+',
                text
            )

            interesting_urls = []

            for u in urls:

                ul = u.lower()

                if any(
                    k.lower() in ul
                    for k in keywords
                ):

                    interesting_urls.append(
                        u[:500]
                    )

            if interesting_urls:

                print(
                    "POSSIBLE URLS:"
                )

                for u in list(
                    dict.fromkeys(
                        interesting_urls
                    )
                )[:30]:

                    print(
                        " ",
                        u
                    )

                    found_count += 1

            # -------------------------------------------------
            # Extract quoted API-like paths
            # -------------------------------------------------

            paths = re.findall(
                r'["\']([^"\']{1,300})["\']',
                text
            )

            interesting_paths = []

            for p in paths:

                pl = p.lower()

                if (
                    any(
                        k.lower() in pl
                        for k in keywords
                    )
                    and (
                        "/" in p
                        or "api" in pl
                    )
                ):

                    interesting_paths.append(
                        p
                    )

            if interesting_paths:

                print(
                    "POSSIBLE API PATHS:"
                )

                unique_paths = list(
                    dict.fromkeys(
                        interesting_paths
                    )
                )

                for p in unique_paths[:80]:

                    print(
                        " ",
                        p[:500]
                    )

                    found_count += 1

        except Exception as e:

            print(
                "JS ERROR:",
                js_url,
                repr(e)
            )

    print()
    print(
        "DISCOVERY HITS:",
        found_count
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
    # OPTIONS
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
    # DISCOVER REAL CHART API
    # -----------------------------------------------------

    js_urls = discover_max_frontend()

    if js_urls:

        inspect_javascript(
            js_urls
        )

    # -----------------------------------------------------
    # SUMMARY
    # -----------------------------------------------------

    print()
    print("=" * 70)
    print("FINAL SUMMARY")
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
    print("END")
    print("=" * 70)


if __name__ == "__main__":

    main()