import os
import requests

TOKEN = os.getenv("GFW_API_TOKEN")

if not TOKEN:
    print("ERROR: GFW_API_TOKEN is not loaded.")
    raise SystemExit(1)

url = "https://gateway.api.globalfishingwatch.org/v3/4wings/interaction/1/0/0/0"

params = {
    "datasets[0]": "public-global-presence:latest",
    "date-range": "2026-08-01,2026-08-02",
    "limit": 5,
}

headers = {
    "Authorization": f"Bearer {TOKEN}"
}

print("Testing Global Fishing Watch API...")
print("Dataset: public-global-presence:latest")
print("Date range: 2026-08-01 to 2026-08-02")

response = requests.get(
    url,
    params=params,
    headers=headers,
    timeout=30
)

print()
print("HTTP Status:", response.status_code)
print("Response:")

try:
    print(response.json())
except Exception:
    print(response.text)