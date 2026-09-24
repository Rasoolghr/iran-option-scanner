import requests
import re
import jdatetime
import json

BASE = "https://market.chartix.ir"
HEADERS = {"User-Agent": "Mozilla/5.0"}

MIN_VOLUME = 50
MIN_OPTION_PRICE = 10
MAX_DISTANCE_PERCENT = 10
ATM_PERCENT = 3
TOP_N = 5

session = requests.Session()
session.headers.update(HEADERS)


# ============================================================
# CHARTIX
# ============================================================

def get_all_symbols():
    r = session.get(
        f"{BASE}/symbol/all",
        timeout=30
    )
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


# ============================================================
# DATE
# ============================================================

def today_jalali():
    today = jdatetime.date.today()
    return today.strftime("%Y/%m/%d")


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


# ============================================================
# OPTION PARSER
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

    option_type = None

    # طبق دیتای پروژه:
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


# ============================================================
# UNDERLYING
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
# VOLUME
# ============================================================

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

            break

    return volume


# ============================================================
# FIND SYMBOL
# ============================================================

def find_symbol(symbols, name):

    for s in symbols:

        if s.get("name") == name:
            return s

    return None


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("IRAN OPTIONS SCANNER")
    print("=" * 70)

    print("تاریخ امروز:", today_jalali())

    # --------------------------------------------------------
    # GET SYMBOLS
    # --------------------------------------------------------

    print("\nدر حال دریافت لیست نمادها...")

    symbols = get_all_symbols()

    print("تعداد کل نمادها:", len(symbols))

    # --------------------------------------------------------
    # FIND OPTIONS
    # --------------------------------------------------------

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

        # فقط سررسیدهای فعال
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
        "اختیارهای فعال پیدا شده:",
        len(options)
    )

    # --------------------------------------------------------
    # GET OPTION DATA
    # --------------------------------------------------------

    results = []

    print("\nدریافت اطلاعات قراردادها...")

    for i, op in enumerate(options, 1):

        print(
            f"\r{i}/{len(options)}",
            end="",
            flush=True
        )

        try:

            data = get_info(
                op["ticker"]
            )

            if not data:
                continue

            option_price = float(
                data.get("price") or 0
            )

            volume = get_volume(data)

            if option_price < MIN_OPTION_PRICE:
                continue

            if volume < MIN_VOLUME:
                continue

            results.append({
                **op,
                "option_price": option_price,
                "volume": volume
            })

        except Exception:
            continue

    print("\n")

    print(
        "قراردادهای قابل بررسی:",
        len(results)
    )

    # --------------------------------------------------------
    # UNDERLYING PRICES
    # --------------------------------------------------------

    underlying_names = [
        "خودرو",
        "اهرم",
        "شستا",
        "وبملت"
    ]

    underlying_prices = {}

    print("قیمت پایه‌ها:")

    for name in underlying_names:

        try:

            s = find_symbol(
                symbols,
                name
            )

            if not s:
                continue

            data = get_info(
                s["ticker"]
            )

            if data:

                price = float(
                    data.get("price") or 0
                )

                if price > 0:

                    underlying_prices[name] = price

                    print(
                        f"  {name}: {price:g}"
                    )

        except Exception:
            continue

    # --------------------------------------------------------
    # CALCULATE OPTION METRICS
    # --------------------------------------------------------

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
        option_price = x["option_price"]

        # ----------------------------------------------------
        # INTRINSIC VALUE
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
        # TIME VALUE
        # ----------------------------------------------------

        time_value = (
            option_price - intrinsic
        )

        if time_value <= 0:
            continue

        time_value_percent = (
            time_value / option_price
        ) * 100

        # ----------------------------------------------------
        # DISTANCE FROM STRIKE
        # ----------------------------------------------------

        distance_percent = (
            abs(
                underlying_price - strike
            )
            / underlying_price
        ) * 100

        if distance_percent > MAX_DISTANCE_PERCENT:
            continue

        # ----------------------------------------------------
        # MONEYNESS
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # SCORE
        # ----------------------------------------------------

        score = 0

        # Moneyness
        if moneyness == "ATM":
            score += 40

        elif moneyness == "ITM":
            score += 30

        else:
            score += 15

        # Distance
        if distance_percent <= 2:
            score += 25

        elif distance_percent <= 5:
            score += 18

        elif distance_percent <= 8:
            score += 10

        # Volume
        if volume := x["volume"]:

            if volume >= 1000:
                score += 20

            elif volume >= 500:
                score += 15

            elif volume >= 100:
                score += 10

            elif volume >= 50:
                score += 5

        # Time value
        if time_value_percent >= 70:
            score += 15

        elif time_value_percent >= 50:
            score += 10

        elif time_value_percent >= 30:
            score += 5

        x["underlying_price"] = underlying_price
        x["intrinsic"] = intrinsic
        x["time_value"] = time_value
        x["time_value_percent"] = time_value_percent
        x["distance_percent"] = distance_percent
        x["moneyness"] = moneyness
        x["score"] = score

        final.append(x)

    # --------------------------------------------------------
    # SORT
    # --------------------------------------------------------

    final.sort(
        key=lambda x: (
            x["score"],
            x["volume"],
            -x["distance_percent"]
        ),
        reverse=True
    )

    calls = [
        x for x in final
        if x["type"] == "CALL"
    ]

    puts = [
        x for x in final
        if x["type"] == "PUT"
    ]

    # --------------------------------------------------------
    # PRINT TOP CALL
    # --------------------------------------------------------

    print("\n")
    print("=" * 70)
    print("TOP CALL — اختیار خرید (ض)")
    print("=" * 70)

    if not calls:

        print("مورد مناسبی پیدا نشد.")

    else:

        for x in calls[:TOP_N]:

            print(
                f'{x["name"]:<15}'
                f' پایه={x["underlying"]:<6}'
                f' پایه={x["underlying_price"]:g} '
                f'Strike={x["strike"]} '
                f'Price={x["option_price"]:g} '
                f'Vol={x["volume"]:g} '
                f'TV={x["time_value_percent"]:.1f}% '
                f'{x["moneyness"]:<4} '
                f'Score={x["score"]} '
                f'Exp={x["expiry"]}'
            )

    # --------------------------------------------------------
    # PRINT TOP PUT
    # --------------------------------------------------------

    print("\n")
    print("=" * 70)
    print("TOP PUT — اختیار فروش (ط)")
    print("=" * 70)

    if not puts:

        print("مورد مناسبی پیدا نشد.")

    else:

        for x in puts[:TOP_N]:

            print(
                f'{x["name"]:<15}'
                f' پایه={x["underlying"]:<6}'
                f' پایه={x["underlying_price"]:g} '
                f'Strike={x["strike"]} '
                f'Price={x["option_price"]:g} '
                f'Vol={x["volume"]:g} '
                f'TV={x["time_value_percent"]:.1f}% '
                f'{x["moneyness"]:<4} '
                f'Score={x["score"]} '
                f'Exp={x["expiry"]}'
            )

    # --------------------------------------------------------
    # 5-MINUTE DATA DEBUG
    # --------------------------------------------------------

    print("\n")
    print("=" * 70)
    print("5-MINUTE DATA TEST")
    print("=" * 70)

    debug_symbols = [
        "طملت8075",
        "وبملت"
    ]

    for debug_name in debug_symbols:

        print("\n" + "-" * 60)
        print("بررسی:", debug_name)

        try:

            debug_symbol = find_symbol(
                symbols,
                debug_name
            )

            if not debug_symbol:

                print("نماد پیدا نشد")
                continue

            print(
                "NAME   :",
                debug_symbol.get("name")
            )

            print(
                "TICKER :",
                debug_symbol.get("ticker")
            )

            print(
                "DESC   :",
                debug_symbol.get("description")
            )

            debug_data = get_info(
                debug_symbol["ticker"]
            )

            if not debug_data:

                print("اطلاعات دریافت نشد")
                continue

            print("\nTOP LEVEL KEYS:")
            print(
                list(
                    debug_data.keys()
                )
            )

            # ------------------------------------------------
            # SEARCH POSSIBLE CHART DATA
            # ------------------------------------------------

            possible_keys = [
                "chart",
                "charts",
                "candle",
                "candles",
                "ohlc",
                "history",
                "histories",
                "time",
                "timestamp",
                "data"
            ]

            found = False

            for key, value in debug_data.items():

                key_lower = str(
                    key
                ).lower()

                if any(
                    word in key_lower
                    for word in possible_keys
                ):

                    found = True

                    print(
                        "\nKEY:",
                        key
                    )

                    print(
                        "TYPE:",
                        type(value).__name__
                    )

                    try:

                        output = json.dumps(
                            value,
                            ensure_ascii=False,
                            indent=2
                        )

                    except Exception:

                        output = str(value)

                    if len(output) > 5000:

                        output = (
                            output[:5000]
                            + "\n..."
                        )

                    print(output)

            if not found:

                print(
                    "\nکلید واضحی برای "
                    "Chart/Candle پیدا نشد."
                )

        except Exception as e:

            print(
                "DEBUG ERROR:",
                repr(e)
            )

    # --------------------------------------------------------
    # FINAL SUMMARY
    # --------------------------------------------------------

    print("\n")
    print("=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)

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

    print("=" * 70)


if __name__ == "__main__":
    main()