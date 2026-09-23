import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
    "Accept": "application/json,text/plain,text/csv,text/html,*/*",
    "Referer": "https://www.tsetmc.com/",
    "Origin": "https://www.tsetmc.com",
}

URLS = [
    "https://cdn.tsetmc.com/api/Instrument/GetInstrumentSearch/%D8%A7%D9%87%D8%B1%D9%85",
    "https://cdn10.tsetmc.com/api/Instrument/GetInstrumentSearch/%D8%A7%D9%87%D8%B1%D9%85",
]

for url in URLS:
    print("\n==============================")
    print("URL:", url)

    try:
        r = requests.get(
            url,
            headers=HEADERS,
            timeout=(10, 20)
        )

        print("STATUS:", r.status_code)
        print("LENGTH:", len(r.content))
        print("DATA:", r.text[:2000])

    except Exception as e:
        print("ERROR:", repr(e))

print("\nTEST FINISHED")