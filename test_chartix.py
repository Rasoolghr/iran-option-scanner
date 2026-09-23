import requests
import json
URL = "https://chartix.ir/api/symbols/search"
queries = [
    "اهرم",
    "خودرو",
    "شستا",
    "وبملت",
    "اختیار"
]
headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json"
}
for q in queries:
    try:
        r = requests.get(
            URL,
            params={"q": q},
            headers=headers,
            timeout=30
        )
        print("\n==============================")
        print("QUERY:", q)
        print("STATUS:", r.status_code)
        data = r.json()
        if data.get("success"):
            for item in data.get("data", []):
                print(json.dumps({
                    "ticker": item.get("ticker"),
                    "name": item.get("name"),
                    "description": item.get("description"),
                    "exchange": item.get("exchange"),
                    "categoryName": item.get("categoryName"),
                    "alias": item.get("alias")
                }, ensure_ascii=False))
        else:
            print("ERROR:", data)
    except Exception as e:
        print("ERROR:", type(e).__name__, e)