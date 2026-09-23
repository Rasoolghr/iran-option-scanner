
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
    "Accept": "application/json,text/plain,text/csv,text/html,*/*",
    "Referer": "https://www.tsetmc.com/",
    "Origin": "https://www.tsetmc.com",
}

TESTS = [
    (
        "CDN",
        "https://cdn.tsetmc.com/api/Instrument/GetInstrumentSearch/%D8%A7%D9%87%D8%B1%D9%85",
    ),
    (
        "OPTION_GATEWAY",
        "https://webgw.tse.ir/InstrumentProvider/api/v1/MarketWatch/MarketWatchOption/fa",
    ),
]

for name, url in TESTS:
    print(f"\n=== {name} ===")
    print("URL:", url)

    try:
        r = requests.get(
            url,
            headers=HEADERS,
            timeout=(10, 30)
        )

        print("HTTP STATUS:", r.status_code)
        print("CONTENT LENGTH:", len(r.content))
        print("RESPONSE:", r.text[:1500])

        if r.ok:
            print("RESULT: PASS")
        else:
            print("RESULT: HTTP FAILURE")

    except requests.exceptions.RequestException as e:
        print("RESULT: NETWORK FAILURE")
        print("ERROR:", repr(e))


print("\nTest completed.")