import os
import requests

KEY = os.environ.get("PELYR_KEY")

if not KEY:
    raise RuntimeError("PELYR_KEY is not set.")

MMSI = "477637100"

URL = f"https://api.pelyr.com/v1/vessels/{MMSI}/track"

headers = {
    "Authorization": f"Bearer {KEY}"
}

params = {
    "from": "2026-08-01T12:00:00Z",
    "to": "2026-08-01T18:00:00Z",
    "resolution": "15min",
}

print("Testing historical AIS track...")
print()
print("MMSI:", MMSI)
print("Time:", params["from"], "→", params["to"])
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

    if isinstance(data, dict):
        print("Response keys:")
        print(list(data.keys()))
        print()

    print("Response:")
    print(data)

except Exception:
    print(response.text)