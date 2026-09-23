import requests
import re
JS_URL = "https://chartix.ir/_nuxt/BlP3i0K2.js"
headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "*/*",
}
print("Downloading Chartix JS...")
r = requests.get(JS_URL, headers=headers, timeout=60)
print("STATUS:", r.status_code)
print("SIZE:", len(r.text))
js = r.text
target = "market.chartix.ir/symbol/info/"
pos = js.find(target)
if pos == -1:
    print("TARGET NOT FOUND")
    exit()
print("\nTARGET FOUND AT:", pos)
start = max(0, pos - 3000)
end = min(len(js), pos + 3000)
print("\n================ CONTEXT ================\n")
print(js[start:end])
print("\n==========================================")