import requests

URL = "https://brsapi.ir"

print("====================================")
print("BRSAPI CONNECTION TEST")
print("====================================")
print("URL:", URL)

try:
    r = requests.get(URL, timeout=(10, 20))

    print("STATUS:", r.status_code)
    print("LENGTH:", len(r.content))
    print("DATA:", r.text[:1000])

except Exception as e:
    print("FAILED")
    print("ERROR:", repr(e))