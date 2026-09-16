import os
import csv
import json
import math
import requests

import mapbox_vector_tile


# ============================================================
# CONFIG
# ============================================================

API_TOKEN = os.environ.get(
    "GFW_API_TOKEN"
)

if not API_TOKEN:
    raise RuntimeError(
        "GFW_API_TOKEN is not loaded."
    )


BASE_URL = (
    "https://gateway.api.globalfishingwatch.org"
)

DATASET = (
    "public-global-presence:latest"
)

# IMPORTANT:
# Use the next day as the end date so that the
# complete 2026-08-01 period is included.
DATE_RANGE = (
    "2026-08-01,2026-08-02"
)


# ============================================================
# SENTINEL-1 CANDIDATES
# ============================================================

CANDIDATES = [
    {
        "candidate_id": 3,
        "lat": -16.417958157423403,
        "lon": 51.86933396852679,
        "ai_oil": 98.37,
        "sar_score": 69.7,
    },
    {
        "candidate_id": 8,
        "lat": -16.245958546388568,
        "lon": 51.879733429957156,
        "ai_oil": 80.82,
        "sar_score": 68.5,
    },
    {
        "candidate_id": 15,
        "lat": -14.90836157127114,
        "lon": 51.54935053990012,
        "ai_oil": 85.96,
        "sar_score": 66.3,
    },
    {
        "candidate_id": 5,
        "lat": -15.345960581671399,
        "lon": 51.52455182418155,
        "ai_oil": 67.20,
        "sar_score": 68.8,
    },
]


# GFW tile zoom level
Z = 7


# ============================================================
# HTTP SESSION
# ============================================================

session = requests.Session()

session.headers.update(
    {
        "Authorization": f"Bearer {API_TOKEN}"
    }
)


# ============================================================
# COORDINATE → TILE
# ============================================================

def lonlat_to_tile(
    lon,
    lat,
    zoom
):

    lat = max(
        min(lat, 85.05112878),
        -85.05112878
    )

    n = 2 ** zoom

    x = int(
        (lon + 180.0)
        / 360.0
        * n
    )

    lat_rad = math.radians(
        lat
    )

    y = int(
        (
            1.0
            -
            math.asinh(
                math.tan(
                    lat_rad
                )
            )
            / math.pi
        )
        /
        2.0
        *
        n
    )

    return x, y


# ============================================================
# HAVERSINE DISTANCE
# ============================================================

def haversine_km(
    lat1,
    lon1,
    lat2,
    lon2
):

    r = 6371.0088

    p1 = math.radians(
        lat1
    )

    p2 = math.radians(
        lat2
    )

    dp = math.radians(
        lat2 - lat1
    )

    dl = math.radians(
        lon2 - lon1
    )

    a = (
        math.sin(dp / 2) ** 2
        +
        math.cos(p1)
        *
        math.cos(p2)
        *
        math.sin(dl / 2) ** 2
    )

    return (
        2
        *
        r
        *
        math.asin(
            math.sqrt(a)
        )
    )


# ============================================================
# GET GFW MVT TILE
# ============================================================

def get_tile(
    z,
    x,
    y
):

    url = (
        f"{BASE_URL}"
        f"/v3/4wings/tile/heatmap/"
        f"{z}/{x}/{y}"
    )

    params = {
        "format": "MVT",
        "interval": "DAY",
        "temporal-aggregation": "true",
        "datasets[0]": DATASET,
        "date-range": DATE_RANGE,
    }

    response = session.get(
        url,
        params=params,
        timeout=60
    )

    print(
        f"Tile {z}/{x}/{y}: "
        f"HTTP {response.status_code}"
    )

    if response.status_code != 200:

        print(
            response.text[:500]
        )

        return None

    try:

        return mapbox_vector_tile.decode(
            response.content
        )

    except Exception as e:

        print(
            f"Could not decode tile: {e}"
        )

        return None


# ============================================================
# CELL CENTER
# ============================================================

def cell_center(
    geometry
):

    coordinates = geometry[
        "coordinates"
    ]

    # Polygon → first ring
    ring = coordinates[0]

    xs = [
        p[0]
        for p in ring
    ]

    ys = [
        p[1]
        for p in ring
    ]

    return (
        sum(xs) / len(xs),
        sum(ys) / len(ys)
    )


# ============================================================
# TILE PIXELS → LAT/LON
# ============================================================

def tile_pixel_to_lonlat(
    px,
    py,
    z,
    x,
    y,
    extent=4096
):

    world_x = (
        x
        +
        px / extent
    )

    world_y = (
        y
        +
        py / extent
    )

    n = 2 ** z

    lon = (
        world_x / n
        * 360.0
        -
        180.0
    )

    lat_rad = math.atan(
        math.sinh(
            math.pi
            *
            (
                1
                -
                2
                *
                world_y
                /
                n
            )
        )
    )

    lat = math.degrees(
        lat_rad
    )

    return lat, lon


# ============================================================
# FIND NEAREST GFW CELLS
# ============================================================

def find_nearest_cells(
    tile,
    target_lat,
    target_lon,
    tile_x,
    tile_y,
    max_cells=12
):

    if not tile:
        return []

    if "main" not in tile:
        return []

    features = tile[
        "main"
    ][
        "features"
    ]

    cells = []

    extent = (
        tile["main"].get(
            "extent",
            4096
        )
    )

    for feature in features:

        props = feature.get(
            "properties",
            {}
        )

        cell_id = props.get(
            "cell"
        )

        if cell_id is None:
            continue

        try:

            cx, cy = cell_center(
                feature["geometry"]
            )

            lat, lon = (
                tile_pixel_to_lonlat(
                    cx,
                    cy,
                    Z,
                    tile_x,
                    tile_y,
                    extent
                )
            )

            distance = haversine_km(
                target_lat,
                target_lon,
                lat,
                lon
            )

            cells.append(
                {
                    "cell": int(
                        cell_id
                    ),
                    "lat": lat,
                    "lon": lon,
                    "distance_km": distance,
                }
            )

        except Exception:
            continue

    cells.sort(
        key=lambda item:
        item["distance_km"]
    )

    return cells[
        :max_cells
    ]


# ============================================================
# INTERACTION API
# ============================================================

def get_interaction(
    z,
    x,
    y,
    cells
):

    if not cells:
        return None

    cell_string = ",".join(
        str(c)
        for c in cells
    )

    url = (
        f"{BASE_URL}"
        f"/v3/4wings/interaction/"
        f"{z}/{x}/{y}/{cell_string}"
    )

    params = {
        "datasets[0]": DATASET,
        "date-range": DATE_RANGE,
        "limit": 1000,
    }

    response = session.get(
        url,
        params=params,
        timeout=60
    )

    print(
        f"Interaction cells "
        f"{len(cells)}: "
        f"HTTP {response.status_code}"
    )

    if response.status_code != 200:

        print(
            response.text[:1000]
        )

        return None

    try:

        return response.json()

    except Exception as e:

        print(
            f"Could not decode JSON: {e}"
        )

        return None


# ============================================================
# EXTRACT VESSEL IDs
# ============================================================

def extract_vessels(
    data
):

    vessels = {}

    if not data:
        return vessels

    # GFW Interaction API uses "id"
    # for the vessel identifier.
    #
    # We also support older/alternative
    # field names just in case.

    def walk(obj):

        if isinstance(
            obj,
            dict
        ):

            vessel_id = (
                obj.get("id")
                or
                obj.get("vessel_id")
                or
                obj.get("vesselId")
            )

            # Avoid treating unrelated IDs as vessels.
            # Vessel records normally contain vessel-related
            # fields such as hours, vessel_type, flag or speed.

            if (
                vessel_id
                and
                (
                    "hours" in obj
                    or
                    "vessel_type" in obj
                    or
                    "flag" in obj
                    or
                    "speed" in obj
                )
            ):

                vessels.setdefault(
                    str(vessel_id),
                    []
                ).append(
                    obj
                )

            for value in obj.values():

                walk(value)

        elif isinstance(
            obj,
            list
        ):

            for item in obj:

                walk(item)

    walk(data)

    return vessels


# ============================================================
# MAIN
# ============================================================

print("=" * 70)

print(
    "MULTI-CANDIDATE GFW AIS CORRELATION"
)

print("=" * 70)

print(
    "\nSentinel-1 acquisition:"
)

print(
    "2026-08-01 15:01:56 UTC"
)

print(
    f"GFW date range: {DATE_RANGE}"
)

all_results = []


# ============================================================
# PROCESS EACH CANDIDATE
# ============================================================

for candidate in CANDIDATES:

    cid = candidate[
        "candidate_id"
    ]

    target_lat = candidate[
        "lat"
    ]

    target_lon = candidate[
        "lon"
    ]

    print(
        "\n"
        +
        "-"
        * 70
    )

    print(
        f"Candidate #{cid}"
    )

    print(
        f"Location: "
        f"{target_lat:.6f}, "
        f"{target_lon:.6f}"
    )

    print(
        f"AI oil score: "
        f"{candidate['ai_oil']:.2f}%"
    )

    print(
        f"SAR score: "
        f"{candidate['sar_score']:.1f}"
    )


    # --------------------------------------------------------
    # TILE
    # --------------------------------------------------------

    tile_x, tile_y = (
        lonlat_to_tile(
            target_lon,
            target_lat,
            Z
        )
    )

    print(
        f"GFW tile: "
        f"{Z}/{tile_x}/{tile_y}"
    )

    tile = get_tile(
        Z,
        tile_x,
        tile_y
    )

    if tile is None:

        print(
            "Could not retrieve tile."
        )

        continue


    # --------------------------------------------------------
    # CELLS
    # --------------------------------------------------------

    nearest = find_nearest_cells(
        tile,
        target_lat,
        target_lon,
        tile_x,
        tile_y,
        max_cells=12
    )

    print(
        "\nNearest cells:"
    )

    for item in nearest:

        print(
            f"  cell={item['cell']} "
            f"distance="
            f"{item['distance_km']:.2f} km"
        )

    cells = [
        item["cell"]
        for item in nearest
    ]

    if not cells:

        print(
            "No cells found."
        )

        continue


    # --------------------------------------------------------
    # INTERACTION
    # --------------------------------------------------------

    interaction = get_interaction(
        Z,
        tile_x,
        tile_y,
        cells
    )

    if interaction is None:

        continue


    # --------------------------------------------------------
    # SAVE RAW RESPONSE
    # --------------------------------------------------------

    raw_file = (
        f"data/results/"
        f"gfw_candidate_{cid}_interaction.json"
    )

    with open(
        raw_file,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            interaction,
            f,
            indent=2
        )

    print(
        f"Raw response saved: "
        f"{raw_file}"
    )


    # --------------------------------------------------------
    # EXTRACT VESSELS
    # --------------------------------------------------------

    vessel_records = (
        extract_vessels(
            interaction
        )
    )

    print(
        "\nVessel IDs found: "
        f"{len(vessel_records)}"
    )


    # --------------------------------------------------------
    # PROCESS VESSELS
    # --------------------------------------------------------

    for vessel_id, records in (
        vessel_records.items()
    ):

        total_hours = 0.0

        distances = []

        vessel_type = ""

        flag = ""

        speed_values = []


        for record in records:

            # Hours
            try:

                total_hours += float(
                    record.get(
                        "hours",
                        0
                    )
                    or 0
                )

            except (
                ValueError,
                TypeError
            ):

                pass


            # Vessel type
            if not vessel_type:

                vessel_type = (
                    record.get(
                        "vessel_type",
                        ""
                    )
                    or ""
                )


            # Flag
            if not flag:

                flag = (
                    record.get(
                        "flag",
                        ""
                    )
                    or ""
                )


            # Speed
            speed = record.get(
                "speed"
            )

            if speed is not None:

                try:

                    speed_values.append(
                        float(speed)
                    )

                except (
                    ValueError,
                    TypeError
                ):

                    pass


            # Lat/lon, if supplied by API
            lat = record.get(
                "lat"
            )

            lon = record.get(
                "lon"
            )

            if (
                lat is not None
                and
                lon is not None
            ):

                try:

                    distances.append(
                        haversine_km(
                            target_lat,
                            target_lon,
                            float(lat),
                            float(lon)
                        )
                    )

                except (
                    ValueError,
                    TypeError
                ):

                    pass


        nearest_distance = (
            min(distances)
            if distances
            else None
        )


        average_speed = (
            sum(speed_values)
            /
            len(speed_values)
            if speed_values
            else None
        )


        all_results.append(
            {
                "candidate_id":
                    cid,

                "candidate_lat":
                    target_lat,

                "candidate_lon":
                    target_lon,

                "sar_score":
                    candidate[
                        "sar_score"
                    ],

                "ai_oil_score":
                    candidate[
                        "ai_oil"
                    ],

                "vessel_id":
                    vessel_id,

                "hours":
                    total_hours,

                "vessel_type":
                    vessel_type,

                "flag":
                    flag,

                "average_speed":
                    average_speed,

                "nearest_distance_km":
                    nearest_distance,

                "record_count":
                    len(records),
            }
        )


        # ----------------------------------------------------
        # PRINT VESSEL
        # ----------------------------------------------------

        print(
            "\n  Vessel:"
            f" {vessel_id}"
        )

        print(
            f"    Hours: "
            f"{total_hours}"
        )

        if vessel_type:

            print(
                f"    Type: "
                f"{vessel_type}"
            )

        if flag:

            print(
                f"    Flag: "
                f"{flag}"
            )

        if average_speed is not None:

            print(
                f"    Average speed: "
                f"{average_speed:.2f}"
            )

        if nearest_distance is not None:

            print(
                f"    AIS distance: "
                f"{nearest_distance:.2f} km"
            )

        else:

            print(
                "    AIS distance: "
                "not provided by Interaction API"
            )


# ============================================================
# SAVE SUMMARY CSV
# ============================================================

output_file = (
    "data/results/"
    "gfw_multi_candidate_ais.csv"
)


fieldnames = [
    "candidate_id",
    "candidate_lat",
    "candidate_lon",
    "sar_score",
    "ai_oil_score",
    "vessel_id",
    "hours",
    "vessel_type",
    "flag",
    "average_speed",
    "nearest_distance_km",
    "record_count",
]


with open(
    output_file,
    "w",
    newline="",
    encoding="utf-8"
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=fieldnames
    )

    writer.writeheader()

    writer.writerows(
        all_results
    )


# ============================================================
# FINAL OUTPUT
# ============================================================

print(
    "\n"
    +
    "="
    * 70
)

print(
    "AIS CORRELATION COMPLETE"
)

print(
    "="
    * 70
)

print(
    "\nSaved:"
)

print(
    output_file
)

print(
    "\nTotal vessel/candidate records: "
    f"{len(all_results)}"
)