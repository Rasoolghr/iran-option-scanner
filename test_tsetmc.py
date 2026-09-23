import requests

urls = [
    "https://brsapi.ir/bourse-api-option-webservice/",
    "https://api.brsapi.ir/",
]

for url in urls:
    print("\n==============================")
    print("URL:", url)

    try:
        r = requests.get(url, timeout=(10, 20))
        print("STATUS:", r.status_code)
        print("LENGTH:", len(r.content))
        print("DATA:", r.text[:2000])
    except Exception as e:
        print("ERROR:", repr(e))

print("\nTEST FINISHED")