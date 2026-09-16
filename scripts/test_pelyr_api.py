import os
import requests

KEY = os.environ.get("PELYR_KEY")

if not KEY:
    raise RuntimeError("PELYR_KEY is not set.")

URL = "https://api.pelyr.com/v1/vessels"

headers = {
    "Authorization": f"Bearer {KEY}"
}

params = {
    "bbox": "40,-30,70,0"
}

print("Testing Pelyr HTTPS API...")
print()

response = requests.get(
    URL,
    headers=headers,
    params=params,
    timeout=30
)

print("HTTP status:", response.status_code)
print()

try:
    data = response.json()
    print("Response:")
    print(data)
except Exception:
    print(response.text)