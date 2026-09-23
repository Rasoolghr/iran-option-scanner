import requests

URLS = [
    "https://brsapi.ir/bourse-api-option-webservice/",
    "https://api.brsapi.ir/",
    "https://brsapi.ir/api/",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "*/*",
}

print("====================================")
print("BRSAPI OPTION DISCOVERY TEST")
print("====================================")

for url in URLS:
    print("\n------------------------------------")
    print("URL:", url)

    try:
        r = requests.get(
            url,
            headers=HEADERS,
            timeout=(10, 20),
            allow_redirects=True
        )

        print("STATUS:", r.status_code)
        print("FINAL URL:", r.url)
        print("CONTENT TYPE:", r.headers.get("content-type"))
        print("LENGTH:", len(r.content))
        print("BODY:")
        print(r.text[:5000])

    except Exception as e:
        print("ERROR:", repr(e))

print("\n====================================")
print("TEST FINISHED")
print("====================================")