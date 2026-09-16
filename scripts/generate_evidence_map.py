import os
import json
import pandas as pd
import rasterio


# ============================================================
# MARITIME OIL-SPILL INTELLIGENCE
# OFFLINE EVIDENCE MAP
# ============================================================

ATTRIBUTION_FILE = (
    "data/results/final_attribution_evidence.csv"
)

BACKTRACKING_FILE = (
    "data/results/environmental/"
    "oil_spill_backtracking_results.json"
)

AIS_FILE = (
    "data/results/gfw_hourly_vessel_proximity.csv"
)

SAR_FILE = (
    "data/processed/sentinel1/geocoded/"
    "sentinel1_vv_sigma0_db_geocoded.tif"
)

SAR_WEB_IMAGE = (
    "data/results/sar_overlay/"
    "sentinel1_vv_web.png"
)

OUTPUT_FILE = (
    "data/results/maritime_evidence_map.html"
)


# ============================================================
# START
# ============================================================

print()
print("=" * 75)
print("MARITIME OIL-SPILL EVIDENCE MAP")
print("=" * 75)


# ============================================================
# LOAD ATTRIBUTION
# ============================================================

print()
print("Loading attribution data...")

attr = pd.read_csv(
    ATTRIBUTION_FILE
)

print(
    "Attribution records:",
    len(attr)
)


# ============================================================
# LOAD BACKTRACKING
# ============================================================

print()
print("Loading drift backtracking data...")

with open(
    BACKTRACKING_FILE,
    "r",
    encoding="utf-8"
) as f:

    backtracking = json.load(f)

print(
    "Backtracking candidates:",
    len(backtracking)
)


# ============================================================
# LOAD AIS
# ============================================================

print()
print("Loading AIS proximity data...")

ais = pd.read_csv(
    AIS_FILE
)

print(
    "AIS records:",
    len(ais)
)


# ============================================================
# READ SAR BOUNDS
# ============================================================

print()
print("Reading Sentinel-1 geographic extent...")

sar_bounds = None

if os.path.exists(SAR_FILE):

    with rasterio.open(
        SAR_FILE
    ) as src:

        sar_bounds = {
            "west": float(src.bounds.left),
            "south": float(src.bounds.bottom),
            "east": float(src.bounds.right),
            "north": float(src.bounds.top)
        }

        print(
            "SAR bounds:",
            src.bounds
        )

else:

    print(
        "WARNING: Sentinel-1 TIFF not found."
    )


# ============================================================
# VALUE CLEANER
# ============================================================

def clean_value(value):

    if pd.isna(value):

        return None

    if hasattr(
        value,
        "item"
    ):

        return value.item()

    return value


# ============================================================
# FIND BACKTRACKING
# ============================================================

def get_backtracking(
    candidate_id
):

    if isinstance(
        backtracking,
        dict
    ):

        return backtracking.get(
            str(candidate_id)
        )


    if isinstance(
        backtracking,
        list
    ):

        for item in backtracking:

            if not isinstance(
                item,
                dict
            ):

                continue


            item_id = item.get(
                "candidate_id"
            )


            if item_id is None:

                continue


            try:

                if int(item_id) == int(
                    candidate_id
                ):

                    return item

            except Exception:

                pass


    return None


# ============================================================
# BUILD CANDIDATES
# ============================================================

print()
print("Building candidate data...")


candidates = []


candidate_ids = sorted(
    attr[
        "candidate_id"
    ]
    .dropna()
    .astype(int)
    .unique()
)


for candidate_id in candidate_ids:

    group = attr[
        attr["candidate_id"]
        == candidate_id
    ].copy()


    if group.empty:

        continue


    group = group.sort_values(
        "rank"
    )


    top = group.iloc[0]


    candidate = {

        "id":
            int(candidate_id),

        "lat":
            float(
                top["candidate_lat"]
            ),

        "lon":
            float(
                top["candidate_lon"]
            ),

        "ai_score":
            float(
                top["ai_oil_score"]
            ),

        "sar_score":
            float(
                top["sar_score"]
            ),

        "top_vessel":
            str(
                top["final_vessel_name"]
            ),

        "vessel_id":
            str(
                top["vessel_id"]
            ),

        "attribution_score":
            float(
                top[
                    "drift_aware_attribution_score"
                ]
            ),

        "source_distance":
            float(
                top[
                    "min_source_corridor_distance_km"
                ]
            ),

        "best_hour":
            clean_value(
                top[
                    "best_matching_hour_utc"
                ]
            ),

        "evidence_strength":
            str(
                top[
                    "evidence_strength"
                ]
            ),

        "trajectory":
            [],

        "vessels":
            []
    }


    # ========================================================
    # DRIFT TRAJECTORY
    # ========================================================

    backtrack = get_backtracking(
        candidate_id
    )


    if backtrack:

        trajectory = backtrack.get(
            "trajectory",
            []
        )


        if isinstance(
            trajectory,
            list
        ):

            for point in trajectory:

                if not isinstance(
                    point,
                    dict
                ):

                    continue


                lat = point.get(
                    "lat"
                )

                if lat is None:

                    lat = point.get(
                        "latitude"
                    )


                lon = point.get(
                    "lon"
                )

                if lon is None:

                    lon = point.get(
                        "longitude"
                    )


                hour = point.get(
                    "hours"
                )

                if hour is None:

                    hour = point.get(
                        "hour"
                    )


                if (
                    lat is not None
                    and
                    lon is not None
                ):

                    candidate[
                        "trajectory"
                    ].append({

                        "lat":
                            float(lat),

                        "lon":
                            float(lon),

                        "hour":
                            clean_value(
                                hour
                            )
                    })


    # ========================================================
    # AIS DATA
    # ========================================================

    vessel_records = ais[
        ais["candidate_id"]
        == candidate_id
    ].copy()


    if not vessel_records.empty:

        if "distance_km" in vessel_records.columns:

            vessel_records = (
                vessel_records
                .sort_values(
                    "distance_km"
                )
            )


        seen = set()


        for _, row in (
            vessel_records.iterrows()
        ):

            vessel_id = str(
                row.get(
                    "vessel_id",
                    ""
                )
            )


            if vessel_id in seen:

                continue


            seen.add(
                vessel_id
            )


            lat = clean_value(
                row.get("lat")
            )

            lon = clean_value(
                row.get("lon")
            )


            if (
                lat is None
                or
                lon is None
            ):

                continue


            candidate[
                "vessels"
            ].append({

                "id":
                    vessel_id,

                "name":
                    str(
                        row.get(
                            "vessel_name",
                            "UNKNOWN"
                        )
                    ),

                "lat":
                    float(lat),

                "lon":
                    float(lon),

                "distance":
                    clean_value(
                        row.get(
                            "distance_km"
                        )
                    ),

                "hour":
                    clean_value(
                        row.get(
                            "hour_utc"
                        )
                    )
            })


    candidates.append(
        candidate
    )


# ============================================================
# JSON
# ============================================================

def json_safe(
    value
):

    if hasattr(
        value,
        "item"
    ):

        return value.item()

    raise TypeError(
        f"Cannot serialize {type(value)}"
    )


candidates_json = json.dumps(
    candidates,
    indent=2,
    default=json_safe
)


sar_json = json.dumps(
    sar_bounds,
    default=json_safe
)


# ============================================================
# HTML
#
# IMPORTANT:
# This is a normal raw string.
# It is NOT a Python f-string.
# ============================================================

html = r"""
<!DOCTYPE html>

<html lang="en">

<head>

<meta charset="UTF-8">

<meta name="viewport"
content="width=device-width, initial-scale=1.0">

<title>
Maritime Oil-Spill Intelligence
</title>


<link
rel="stylesheet"
href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
/>


<style>

* {
    box-sizing: border-box;
}


html,
body {
    margin: 0;
    padding: 0;
    width: 100%;
    height: 100%;
}


body {
    background: #06111d;
    color: #e8f0f8;
    font-family: Arial, Helvetica, sans-serif;
}


.header {
    height: 72px;

    display: flex;

    align-items: center;

    justify-content: space-between;

    padding: 0 24px;

    background: #0b1828;

    border-bottom: 1px solid #20354d;
}


.title {
    font-size: 21px;
    font-weight: 700;
}


.subtitle {
    color: #8fa7bd;
    font-size: 12px;
    margin-top: 4px;
}


.badge {
    padding: 8px 13px;

    border-radius: 20px;

    background: #12263a;

    border: 1px solid #2c4965;

    color: #9fc5e7;

    font-size: 12px;
}


.layout {
    display: grid;

    grid-template-columns: 1fr 370px;

    height: calc(100vh - 72px);
}


#map {
    width: 100%;
    height: 100%;

    background:
        radial-gradient(
            circle at center,
            #102b42 0%,
            #071827 55%,
            #04101a 100%
        );
}


.sidebar {
    background: #0b1828;

    border-left: 1px solid #20354d;

    overflow-y: auto;

    padding: 18px;
}


.section-title {
    font-size: 13px;

    font-weight: 700;

    color: #8fa7bd;

    text-transform: uppercase;

    letter-spacing: 0.8px;

    margin: 4px 0 12px;
}


.card {
    background: #101f31;

    border: 1px solid #213950;

    border-radius: 10px;

    padding: 13px;

    margin-bottom: 12px;

    cursor: pointer;
}


.card:hover {
    border-color: #5ca7df;
}


.card-title {
    font-weight: 700;

    font-size: 14px;

    margin-bottom: 7px;
}


.metric-grid {
    display: grid;

    grid-template-columns: 1fr 1fr;

    gap: 8px;
}


.metric {
    background: #0a1726;

    border-radius: 7px;

    padding: 8px;
}


.metric-label {
    font-size: 10px;

    color: #7890a6;
}


.metric-value {
    margin-top: 3px;

    font-size: 16px;

    font-weight: 700;
}


.vessel {
    padding: 9px;

    margin-top: 8px;

    background: #0a1726;

    border-radius: 7px;
}


.vessel-name {
    font-size: 13px;

    font-weight: 700;
}


.vessel-detail {
    font-size: 11px;

    color: #8fa7bd;

    margin-top: 3px;
}


.status {
    display: inline-block;

    padding: 4px 7px;

    border-radius: 5px;

    font-size: 10px;

    margin-top: 7px;

    background: #172f45;

    color: #aad4f5;
}


.legend {
    position: absolute;

    z-index: 1000;

    bottom: 20px;

    left: 20px;

    background: rgba(8,18,31,0.95);

    border: 1px solid #2a4158;

    border-radius: 8px;

    padding: 12px;

    font-size: 11px;
}


.legend-row {
    margin: 6px 0;
}


.dot {
    display: inline-block;

    width: 10px;

    height: 10px;

    border-radius: 50%;

    margin-right: 7px;
}


.warning {
    font-size: 10px;

    color: #8299ad;

    line-height: 1.5;

    margin-top: 16px;

    padding-bottom: 20px;
}


.sar-label {
    background: rgba(8,18,31,0.9);

    color: #dcecff;

    border: 1px solid #55738d;

    padding: 3px 7px;

    font-size: 10px;
}


@media(max-width:900px) {

    .layout {
        grid-template-columns: 1fr;
    }

    .sidebar {
        height: 45vh;

        border-left: none;

        border-top: 1px solid #20354d;
    }

}

</style>

</head>


<body>


<div class="header">

<div>

<div class="title">
MARITIME OIL-SPILL INTELLIGENCE
</div>

<div class="subtitle">
Sentinel-1 SAR • AI Detection • Ocean Drift • AIS Attribution
</div>

</div>

<div class="badge">
INVESTIGATION MODE
</div>

</div>


<div class="layout">


<div id="map"></div>


<div class="sidebar">

<div class="section-title">
Oil-spill candidates
</div>

<div id="candidateList"></div>

<div class="warning">

<b>Evidence interpretation</b>

<br><br>

The system ranks potential source vessels
using satellite evidence, environmental
drift backtracking and AIS proximity.

<br><br>

The ranking supports investigation and
response.

<br><br>

It does not establish legal or causal
responsibility.

</div>

</div>


</div>


<div class="legend">

<div class="legend-row">

<span
class="dot"
style="background:#ff3b30">
</span>

Oil-spill candidate

</div>


<div class="legend-row">

<span
class="dot"
style="background:#38a9ff">
</span>

AIS vessel

</div>


<div class="legend-row">

<span
class="dot"
style="background:#ffd60a">
</span>

Estimated source

</div>


<div class="legend-row">

━━ Drift backtracking

</div>


<div class="legend-row">

━━ Sentinel-1 SAR

</div>

</div>


<script
src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js">
</script>


<script>


// ============================================================
// DATA
// ============================================================

const candidates =
__CANDIDATES_JSON__;


const sarBounds =
__SAR_BOUNDS_JSON__;


// ============================================================
// MAP
// ============================================================

const map =
L.map(
    "map",
    {
        zoomControl: true,

        attributionControl: false
    }
);


// ============================================================
// NO EXTERNAL BASEMAP
//
// The Sentinel-1 image is the main geographic layer.
// This prevents OpenStreetMap 403/block messages.
// ============================================================


// ============================================================
// INITIAL VIEW
// ============================================================

if (sarBounds) {

    map.fitBounds([

        [
            sarBounds.south,
            sarBounds.west
        ],

        [
            sarBounds.north,
            sarBounds.east
        ]

    ]);

} else {

    map.setView(
        [-16, 52],
        7
    );

}


// ============================================================
// SENTINEL-1 SAR OVERLAY
// ============================================================

const sarImagePath =
    "sar_overlay/sentinel1_vv_web.png";


if (sarBounds) {

    const sarImageBounds = [

        [
            sarBounds.south,
            sarBounds.west
        ],

        [
            sarBounds.north,
            sarBounds.east
        ]

    ];


    const sarOverlay =
        L.imageOverlay(
            sarImagePath,
            sarImageBounds,
            {
                opacity: 0.82,

                interactive: false
            }
        );


    sarOverlay.addTo(
        map
    );


    sarOverlay.bringToBack();

}


// ============================================================
// MARKER ICON
// ============================================================

function markerIcon(
    color,
    size
) {

    return L.divIcon({

        className: "",

        html:
            '<div style="' +
            'width:' + size + 'px;' +
            'height:' + size + 'px;' +
            'background:' + color + ';' +
            'border-radius:50%;' +
            'border:2px solid white;' +
            'box-shadow:0 0 9px rgba(0,0,0,.9);' +
            '"></div>',

        iconSize:
            [size, size],

        iconAnchor:
            [size / 2, size / 2]

    });

}


// ============================================================
// CANDIDATES
// ============================================================

candidates.forEach(
    candidate => {


        // ----------------------------------------------------
        // OIL-SPILL CANDIDATE
        // ----------------------------------------------------

        const candidateMarker =
            L.marker(

                [
                    candidate.lat,
                    candidate.lon
                ],

                {
                    icon:
                        markerIcon(
                            "#ff3b30",

                            candidate.id === 3
                                ? 20
                                : 15
                        )
                }

            ).addTo(
                map
            );


        candidateMarker.bindPopup(`

            <div style="min-width:230px;">

                <b>
                OIL-SPILL CANDIDATE #${candidate.id}
                </b>

                <br><br>

                AI oil score:
                <b>
                ${candidate.ai_score.toFixed(2)}
                </b>

                <br>

                SAR score:
                <b>
                ${candidate.sar_score.toFixed(2)}
                </b>

                <br>

                Attribution:
                <b>
                ${candidate.attribution_score.toFixed(1)}
                </b>

                <br>

                Source distance:
                <b>
                ${candidate.source_distance.toFixed(1)}
                km
                </b>

                <br><br>

                Highest-ranked potential source:
                <b>
                ${candidate.top_vessel}
                </b>

            </div>

        `);


        // ----------------------------------------------------
        // DRIFT TRAJECTORY
        // ----------------------------------------------------

        const trajectory =
            candidate.trajectory;


        if (
            trajectory &&
            trajectory.length >= 2
        ) {

            const latlngs =
                trajectory.map(
                    point => [

                        point.lat,
                        point.lon

                    ]
                );


            L.polyline(
                latlngs,
                {

                    weight: 4,

                    opacity: 0.95,

                    dashArray:
                        "8,8"

                }
            ).addTo(
                map
            );


            // ------------------------------------------------
            // SOURCE
            // ------------------------------------------------

            const source =
                trajectory[
                    trajectory.length - 1
                ];


            L.marker(

                [
                    source.lat,
                    source.lon
                ],

                {
                    icon:
                        markerIcon(
                            "#ffd60a",
                            15
                        )
                }

            ).addTo(
                map
            )
            .bindPopup(`

                <b>
                ESTIMATED SOURCE REGION
                </b>

                <br><br>

                Candidate #${candidate.id}

                <br>

                Backtracked:
                ${trajectory.length - 1}
                hours

                <br><br>

                Model-derived source estimate.

            `);

        }


        // ----------------------------------------------------
        // AIS VESSELS
        // ----------------------------------------------------

        candidate.vessels.forEach(
            vessel => {


                if (
                    vessel.lat === null ||
                    vessel.lon === null
                ) {

                    return;

                }


                L.marker(

                    [
                        vessel.lat,
                        vessel.lon
                    ],

                    {
                        icon:
                            markerIcon(
                                "#38a9ff",
                                11
                            )
                    }

                ).addTo(
                    map
                )
                .bindPopup(`

                    <b>
                    AIS VESSEL
                    </b>

                    <br><br>

                    Vessel:
                    <b>
                    ${vessel.name}
                    </b>

                    <br>

                    Distance:
                    ${
                        vessel.distance !== null
                        ? vessel.distance.toFixed(1)
                        : "N/A"
                    }
                    km

                    <br>

                    Time:
                    ${
                        vessel.hour !== null
                        ? vessel.hour + ":00 UTC"
                        : "N/A"
                    }

                `);

            }
        );

    }
);


// ============================================================
// SIDEBAR
// ============================================================

const list =
document.getElementById(
    "candidateList"
);


candidates
.sort(
    (a, b) =>
        b.attribution_score -
        a.attribution_score
)
.forEach(
    candidate => {


        const card =
            document.createElement(
                "div"
            );


        card.className =
            "card";


        card.innerHTML = `

            <div class="card-title">

                Oil-spill candidate #${candidate.id}

            </div>


            <div class="metric-grid">


                <div class="metric">

                    <div class="metric-label">
                    AI OIL SCORE
                    </div>

                    <div class="metric-value">

                    ${candidate.ai_score.toFixed(1)}

                    </div>

                </div>


                <div class="metric">

                    <div class="metric-label">
                    SAR SCORE
                    </div>

                    <div class="metric-value">

                    ${candidate.sar_score.toFixed(1)}

                    </div>

                </div>


                <div class="metric">

                    <div class="metric-label">
                    ATTRIBUTION
                    </div>

                    <div class="metric-value">

                    ${candidate.attribution_score.toFixed(1)}

                    </div>

                </div>


                <div class="metric">

                    <div class="metric-label">
                    SOURCE DISTANCE
                    </div>

                    <div class="metric-value">

                    ${candidate.source_distance.toFixed(1)}
                    km

                    </div>

                </div>


            </div>


            <div class="vessel">

                <div class="vessel-name">

                    ${candidate.top_vessel}

                </div>


                <div class="vessel-detail">

                    Highest-ranked potential
                    source vessel

                </div>


                <div class="vessel-detail">

                    Best matching hour:

                    ${
                        candidate.best_hour !== null
                        ? candidate.best_hour + ":00 UTC"
                        : "N/A"
                    }

                </div>


                <div class="status">

                    ${candidate.evidence_strength}

                    evidence

                </div>

            </div>

        `;


        // ----------------------------------------------------
        // CARD CLICK
        // ----------------------------------------------------

        card.onclick =
        function() {


            map.setView(

                [
                    candidate.lat,
                    candidate.lon
                ],

                9

            );


            L.popup()

                .setLatLng(
                    [
                        candidate.lat,
                        candidate.lon
                    ]
                )

                .setContent(`

                    <b>
                    OIL-SPILL CANDIDATE #${candidate.id}
                    </b>

                    <br><br>

                    AI score:
                    ${candidate.ai_score.toFixed(2)}

                    <br>

                    SAR score:
                    ${candidate.sar_score.toFixed(2)}

                    <br>

                    Attribution:
                    ${candidate.attribution_score.toFixed(1)}

                    <br><br>

                    Highest-ranked potential source:

                    <b>
                    ${candidate.top_vessel}
                    </b>

                `)

                .openOn(
                    map
                );

        };


        list.appendChild(
            card
        );

    }
);


</script>


</body>

</html>
"""


# ============================================================
# INSERT DATA
# ============================================================

html = html.replace(
    "__CANDIDATES_JSON__",
    candidates_json
)


html = html.replace(
    "__SAR_BOUNDS_JSON__",
    sar_json
)


# ============================================================
# SAVE
# ============================================================

print()
print("Writing HTML map...")


os.makedirs(
    os.path.dirname(
        OUTPUT_FILE
    ),
    exist_ok=True
)


with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as f:

    f.write(
        html
    )


# ============================================================
# FINISH
# ============================================================

print()
print("=" * 75)
print("OFFLINE EVIDENCE MAP CREATED")
print("=" * 75)

print()

print(
    "Saved:"
)

print(
    OUTPUT_FILE
)

print()

print(
    "SAR overlay:"
)

print(
    SAR_WEB_IMAGE
)

print()

print(
    "Candidates:",
    len(candidates)
)

print()

print(
    "External OpenStreetMap tiles:"
)

print(
    "DISABLED"
)

print()

print(
    "The dashboard now uses the local Sentinel-1"
)

print(
    "SAR image as its primary geographic layer."
)

print()

print("=" * 75)
print("DONE")
print("=" * 75)