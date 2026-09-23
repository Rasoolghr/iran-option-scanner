import requests

URL = "https://cdn.tsetmc.com/api/Instrument/GetInstrumentSearch/خودرو"

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0 Safari/537.36"
    )
}

try:
    r = requests.get(URL, headers=headers, timeout=20)

    print("HTTP STATUS:", r.status_code)
    print("RESPONSE:")
    print(r.text[:2000])

    r.raise_for_status()

except Exception as e:
    print("ERROR:", repr(e))
    raise
