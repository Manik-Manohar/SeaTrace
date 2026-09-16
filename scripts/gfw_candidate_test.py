import os
import math
import requests


LAT = -15.824387
LON = 51.655060

DATE_RANGE = "2026-08-01,2026-08-02"

TOKEN = os.getenv("GFW_API_TOKEN")

if not TOKEN:
    print("ERROR: GFW_API_TOKEN is not loaded.")
    raise SystemExit(1)


def lon_to_tile_x(lon, zoom):
    return int((lon + 180.0) / 360.0 * (2 ** zoom))


def lat_to_tile_y(lat, zoom):
    lat_rad = math.radians(lat)

    return int(
        (
            1
            - math.asinh(math.tan(lat_rad)) / math.pi
        )
        / 2
        * (2 ** zoom)
    )


headers = {
    "Authorization": f"Bearer {TOKEN}"
}

print("=" * 60)
print("GFW TILE AVAILABILITY TEST")
print("=" * 60)

print(f"Candidate latitude : {LAT}")
print(f"Candidate longitude: {LON}")
print(f"Date range         : {DATE_RANGE}")
print()


for zoom in [4, 5, 6, 7, 8]:

    x = lon_to_tile_x(LON, zoom)
    y = lat_to_tile_y(LAT, zoom)

    url = (
        "https://gateway.api.globalfishingwatch.org"
        f"/v3/4wings/tile/heatmap/{zoom}/{x}/{y}"
    )

    params = {
        "date-range": DATE_RANGE,
        "datasets[0]": "public-global-presence:latest",
        "format": "MVT",
        "interval": "DAY",
        "temporal-aggregation": "true",
    }

    print("-" * 60)
    print(f"Zoom: {zoom}")
    print(f"Tile: {x}/{y}")
    print("Requesting...")

    response = requests.get(
        url,
        params=params,
        headers=headers,
        timeout=60
    )

    print("HTTP:", response.status_code)

    if response.status_code == 200:

        print("DATA FOUND")
        print("Size:", len(response.content), "bytes")

    else:

        try:
            print("Message:", response.json())
        except Exception:
            print("Message:", response.text)


print()
print("=" * 60)
print("TEST COMPLETE")
print("=" * 60)