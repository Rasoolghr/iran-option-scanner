import requests

BASES = [
    "https://api.chartix.ir",
    "https://api1.chartix.ir",
    "https://api2.chartix.ir",
    "https://api3.chartix.ir",
]

PATHS = [
    "/",
    "/swagger",
    "/swagger/index.html",
    "/swagger/v1/swagger.json",
    "/openapi.json",
    "/api",
]

headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json,text/plain,*/*",
}

for base in BASES:
    print("\n" + "=" * 60)
    print("BASE:", base)

    for path in PATHS:
        url = base + path

        try:
            r = requests.get(
                url,
                headers=headers,
                timeout=10,
                allow_redirects=True,
            )

            print(
                f"{path:30} "
                f"STATUS={r.status_code} "
                f"TYPE={r.headers.get('content-type')} "
                f"SIZE={len(r.content)}"
            )

            if r.status_code == 200:
                print("URL:", r.url)
                print("DATA:", r.text[:500])

        except Exception as e:
            print(f"{path:30} ERROR={type(e).__name__}: {e}")
