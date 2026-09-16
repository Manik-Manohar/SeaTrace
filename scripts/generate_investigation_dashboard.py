import os
import json
import base64
import pandas as pd
import rasterio


# ============================================================
# MARITIME OIL-SPILL INTELLIGENCE
# SIH 2026 - INVESTIGATION DASHBOARD
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

SAR_IMAGE = (
    "data/results/sar_overlay/"
    "sentinel1_vv_web.png"
)

OUTPUT_FILE = (
    "data/results/maritime_investigation_dashboard.html"
)


# ============================================================
# HELPERS
# ============================================================

def clean_value(value):

    if pd.isna(value):
        return None

    if hasattr(value, "item"):
        return value.item()

    return value


def json_safe(value):

    if hasattr(value, "item"):
        return value.item()

    raise TypeError(
        f"Cannot serialize {type(value)}"
    )


def get_backtracking(data, candidate_id):

    if isinstance(data, dict):

        item = data.get(str(candidate_id))

        if item is not None:
            return item

    if isinstance(data, list):

        for item in data:

            if not isinstance(item, dict):
                continue

            value = item.get("candidate_id")

            if value is None:
                continue

            try:

                if int(value) == int(candidate_id):
                    return item

            except Exception:
                pass

    return None


# ============================================================
# START
# ============================================================

print()
print("=" * 78)
print("MARITIME OIL-SPILL INVESTIGATION DASHBOARD")
print("=" * 78)


# ============================================================
# LOAD DATA
# ============================================================

print()
print("Loading attribution data...")

attr = pd.read_csv(
    ATTRIBUTION_FILE
)

print(
    "Records:",
    len(attr)
)


print()
print("Loading drift backtracking...")

with open(
    BACKTRACKING_FILE,
    "r",
    encoding="utf-8"
) as f:

    backtracking = json.load(f)


print(
    "Backtracking records:",
    len(backtracking)
)


print()
print("Loading AIS data...")

ais = pd.read_csv(
    AIS_FILE
)

print(
    "AIS records:",
    len(ais)
)


# ============================================================
# SAR BOUNDS
# ============================================================

print()
print("Reading Sentinel-1 SAR extent...")

with rasterio.open(
    SAR_FILE
) as src:

    sar_bounds = {

        "west":
            float(src.bounds.left),

        "south":
            float(src.bounds.bottom),

        "east":
            float(src.bounds.right),

        "north":
            float(src.bounds.top)

    }

    print(
        "SAR bounds:",
        src.bounds
    )


# ============================================================
# EMBED SAR IMAGE
#
# This makes the HTML self-contained.
# No relative-image-path problem.
# ============================================================

print()
print("Embedding Sentinel-1 SAR image...")

sar_data_uri = ""

if os.path.exists(SAR_IMAGE):

    with open(
        SAR_IMAGE,
        "rb"
    ) as f:

        encoded = base64.b64encode(
            f.read()
        ).decode("ascii")


    sar_data_uri = (
        "data:image/png;base64,"
        + encoded
    )

    print(
        "SAR image embedded successfully."
    )

else:

    print(
        "WARNING: SAR web image not found."
    )


# ============================================================
# BUILD CANDIDATES
# ============================================================

print()
print("Building investigation records...")


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
        attr["candidate_id"] == candidate_id
    ].copy()


    if group.empty:
        continue


    group = group.sort_values(
        "rank"
    )


    top = group.iloc[0]


    # --------------------------------------------------------
    # IDENTITY
    # --------------------------------------------------------

    vessel_name = str(
        top.get(
            "final_vessel_name",
            top.get(
                "vessel_name",
                "UNKNOWN"
            )
        )
    )


    vessel_id = str(
        top.get(
            "vessel_id",
            ""
        )
    )


    # --------------------------------------------------------
    # BACKTRACKING
    # --------------------------------------------------------

    backtrack = get_backtracking(
        backtracking,
        candidate_id
    )


    trajectory = []


    if backtrack:

        raw_trajectory = backtrack.get(
            "trajectory",
            []
        )


        if isinstance(
            raw_trajectory,
            list
        ):

            for point in raw_trajectory:

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

                    trajectory.append({

                        "lat":
                            float(lat),

                        "lon":
                            float(lon),

                        "hour":
                            clean_value(hour)

                    })


    # --------------------------------------------------------
    # AIS
    # --------------------------------------------------------

    vessel_records = ais[
        ais["candidate_id"] == candidate_id
    ].copy()


    ais_points = []


    if not vessel_records.empty:

        # Keep a useful number of points
        # for visualization.

        if "distance_km" in vessel_records.columns:

            vessel_records = (
                vessel_records
                .sort_values(
                    "distance_km"
                )
            )


        vessel_records = vessel_records.head(
            25
        )


        for _, row in vessel_records.iterrows():

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


            ais_points.append({

                "id":
                    str(
                        row.get(
                            "vessel_id",
                            ""
                        )
                    ),

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


    # --------------------------------------------------------
    # RECORD
    # --------------------------------------------------------

    candidates.append({

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

        "attribution":
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

        "acquisition_distance":
            clean_value(
                top[
                    "acquisition_source_distance_km"
                ]
            ),

        "best_hour":
            clean_value(
                top[
                    "best_matching_hour_utc"
                ]
            ),

        "evidence":
            str(
                top[
                    "evidence_strength"
                ]
            ),

        "vessel_name":
            vessel_name,

        "vessel_id":
            vessel_id,

        "trajectory":
            trajectory,

        "ais":
            ais_points

    })


print(
    "Candidates prepared:",
    len(candidates)
)


# ============================================================
# SORT BY ATTRIBUTION
# ============================================================

candidates.sort(
    key=lambda x: x["attribution"],
    reverse=True
)


# ============================================================
# HTML
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

<link
rel="stylesheet"
href="https://unpkg.com/maplibre-gl@5/dist/maplibre-gl.css"
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

    overflow: hidden;

}


body {

    background: #061321;

    color: #eaf3fb;

    font-family:
        Arial,
        Helvetica,
        sans-serif;

}


/* ==========================================================
   HEADER
   ========================================================== */

.header {

    height: 76px;

    display: flex;

    align-items: center;

    justify-content: space-between;

    padding:
        0 24px;

    background:
        linear-gradient(
            90deg,
            #081827,
            #0b1d2f
        );

    border-bottom:
        1px solid #203b54;

}


.brand {

    display: flex;

    flex-direction: column;

}


.brand-title {

    font-size: 21px;

    font-weight: 700;

    letter-spacing: .3px;

}


.brand-subtitle {

    margin-top: 4px;

    font-size: 12px;

    color: #89a8c1;

}


.mode {

    border:
        1px solid #31516d;

    background:
        #10283d;

    color:
        #9ed0f3;

    padding:
        9px 14px;

    border-radius:
        18px;

    font-size:
        11px;

    font-weight:
        600;

    letter-spacing:
        .5px;

}


/* ==========================================================
   MAIN
   ========================================================== */

.main {

    height:
        calc(100vh - 76px);

    display:
        grid;

    grid-template-columns:
        minmax(0, 1fr)
        390px;

}


/* ==========================================================
   MAP
   ========================================================== */

.map-container {

    position:
        relative;

    background:
        radial-gradient(
            ellipse at center,
            #10304a 0%,
            #071a2b 52%,
            #04101b 100%
        );

    overflow:
        hidden;

}


#map {

    width:
        100%;

    height:
        100%;

    background:
        #071b2b;

}


/* subtle grid */

.map-grid {

    position:
        absolute;

    inset:
        0;

    pointer-events:
        none;

    z-index:
        300;

    opacity:
        .14;

    background-image:

        linear-gradient(
            rgba(100,170,210,.15)
            1px,
            transparent 1px
        ),

        linear-gradient(
            90deg,
            rgba(100,170,210,.15)
            1px,
            transparent 1px
        );

    background-size:
        80px 80px;

}


/* ==========================================================
   MAP TITLE
   ========================================================== */

.map-label {

    position:
        absolute;

    top:
        18px;

    left:
        18px;

    z-index:
        500;

    background:
        rgba(5,17,29,.88);

    border:
        1px solid #294761;

    border-radius:
        8px;

    padding:
        9px 12px;

}


.map-label-title {

    font-size:
        12px;

    font-weight:
        700;

}


.map-label-sub {

    margin-top:
        3px;

    font-size:
        10px;

    color:
        #7f9db5;

}


/* ==========================================================
   SIDEBAR
   ========================================================== */

.sidebar {

    background:
        #091827;

    border-left:
        1px solid #203b54;

    overflow-y:
        auto;

    padding:
        18px;

}


.sidebar-heading {

    color:
        #91b3cc;

    font-size:
        12px;

    font-weight:
        700;

    text-transform:
        uppercase;

    letter-spacing:
        1px;

    margin-bottom:
        13px;

}


/* ==========================================================
   CANDIDATE CARD
   ========================================================== */

.card {

    background:
        linear-gradient(
            145deg,
            #102236,
            #0b1b2c
        );

    border:
        1px solid #23415b;

    border-radius:
        10px;

    padding:
        13px;

    margin-bottom:
        12px;

    cursor:
        pointer;

    transition:
        .18s ease;

}


.card:hover {

    transform:
        translateY(-1px);

    border-color:
        #4d8fbd;

}


.card.selected {

    border-color:
        #4fa6df;

    box-shadow:
        0 0 0 1px
        rgba(79,166,223,.18);

}


.card-head {

    display:
        flex;

    align-items:
        center;

    justify-content:
        space-between;

    margin-bottom:
        10px;

}


.card-title {

    font-size:
        14px;

    font-weight:
        700;

}


.rank {

    width:
        23px;

    height:
        23px;

    border-radius:
        50%;

    display:
        flex;

    align-items:
        center;

    justify-content:
        center;

    background:
        #173650;

    color:
        #a9d5f2;

    font-size:
        11px;

    font-weight:
        700;

}


.metrics {

    display:
        grid;

    grid-template-columns:
        1fr 1fr;

    gap:
        7px;

}


.metric {

    background:
        #081727;

    border-radius:
        7px;

    padding:
        8px;

}


.metric-label {

    font-size:
        9px;

    color:
        #718da5;

    letter-spacing:
        .3px;

}


.metric-value {

    margin-top:
        4px;

    font-size:
        16px;

    font-weight:
        700;

}


.vessel-box {

    margin-top:
        9px;

    padding:
        9px;

    background:
        #081727;

    border-radius:
        7px;

}


.vessel-name {

    font-size:
        12px;

    font-weight:
        700;

}


.vessel-sub {

    margin-top:
        3px;

    color:
        #82a5bd;

    font-size:
        10px;

}


.evidence {

    display:
        inline-block;

    margin-top:
        7px;

    padding:
        4px 7px;

    border-radius:
        5px;

    background:
        #12314b;

    color:
        #9bd1f3;

    font-size:
        9px;

}


/* ==========================================================
   LEGEND
   ========================================================== */

.legend {

    position:
        absolute;

    left:
        18px;

    bottom:
        18px;

    z-index:
        600;

    background:
        rgba(5,16,28,.94);

    border:
        1px solid #29455e;

    border-radius:
        9px;

    padding:
        11px 13px;

    font-size:
        10px;

}


.legend-row {

    margin:
        6px 0;

}


.dot {

    display:
        inline-block;

    width:
        9px;

    height:
        9px;

    border-radius:
        50%;

    margin-right:
        7px;

}


/* ==========================================================
   INVESTIGATION PANEL
   ========================================================== */

.overlay {

    display:
        none;

    position:
        fixed;

    inset:
        0;

    z-index:
        3000;

    background:
        rgba(2,10,18,.72);

    backdrop-filter:
        blur(4px);

}


.investigation {

    position:
        absolute;

    left:
        50%;

    top:
        50%;

    transform:
        translate(-50%, -50%);

    width:
        min(930px, 92vw);

    max-height:
        88vh;

    overflow-y:
        auto;

    background:
        linear-gradient(
            145deg,
            #0b1d2f,
            #071523
        );

    border:
        1px solid #34536d;

    border-radius:
        14px;

    box-shadow:
        0 25px 80px
        rgba(0,0,0,.65);

}


.investigation-header {

    display:
        flex;

    justify-content:
        space-between;

    align-items:
        center;

    padding:
        18px 20px;

    border-bottom:
        1px solid #213c53;

}


.investigation-title {

    font-size:
        18px;

    font-weight:
        700;

}


.investigation-sub {

    margin-top:
        4px;

    font-size:
        11px;

    color:
        #85a6be;

}


.close {

    border:
        1px solid #36536b;

    background:
        #10273b;

    color:
        #b9d3e7;

    border-radius:
        7px;

    padding:
        7px 11px;

    cursor:
        pointer;

}


/* ==========================================================
   INVESTIGATION BODY
   ========================================================== */

.investigation-body {

    padding:
        18px;

}


.section {

    margin-bottom:
        17px;

}


.section-title {

    font-size:
        11px;

    font-weight:
        700;

    text-transform:
        uppercase;

    letter-spacing:
        .8px;

    color:
        #8eb2ca;

    margin-bottom:
        9px;

}


.evidence-grid {

    display:
        grid;

    grid-template-columns:
        repeat(4, 1fr);

    gap:
        9px;

}


.evidence-card {

    background:
        #081727;

    border:
        1px solid #1e3a51;

    border-radius:
        8px;

    padding:
        11px;

}


.evidence-card-label {

    font-size:
        9px;

    color:
        #708ba2;

}


.evidence-card-value {

    margin-top:
        5px;

    font-size:
        21px;

    font-weight:
        700;

}


.evidence-card-unit {

    font-size:
        9px;

    color:
        #7895ab;

}


/* ==========================================================
   VESSEL
   ========================================================== */

.vessel-detail-grid {

    display:
        grid;

    grid-template-columns:
        1fr 1fr;

    gap:
        9px;

}


.detail {

    background:
        #081727;

    border-radius:
        8px;

    padding:
        10px;

}


.detail-label {

    font-size:
        9px;

    color:
        #708ba2;

}


.detail-value {

    margin-top:
        4px;

    font-size:
        13px;

    font-weight:
        700;

}


/* ==========================================================
   SCORE BAR
   ========================================================== */

.score-row {

    margin:
        9px 0;

}


.score-head {

    display:
        flex;

    justify-content:
        space-between;

    font-size:
        10px;

    color:
        #a8bfd1;

}


.score-track {

    margin-top:
        5px;

    height:
        6px;

    border-radius:
        5px;

    background:
        #12273a;

    overflow:
        hidden;

}


.score-fill {

    height:
        100%;

    border-radius:
        5px;

    background:
        linear-gradient(
            90deg,
            #17618a,
            #58b5e8
        );

}


/* ==========================================================
   TIMELINE
   ========================================================== */

.timeline {

    display:
        flex;

    align-items:
        center;

    gap:
        0;

    overflow-x:
        auto;

    padding:
        8px 0;

}


.timeline-item {

    min-width:
        105px;

    position:
        relative;

    text-align:
        center;

}


.timeline-dot {

    width:
        11px;

    height:
        11px;

    margin:
        0 auto 6px;

    border-radius:
        50%;

    background:
        #39a9ed;

    border:
        2px solid #092035;

    box-shadow:
        0 0 0 1px #327fae;

}


.timeline-line {

    height:
        1px;

    background:
        #31516a;

    position:
        absolute;

    top:
        5px;

    left:
        55%;

    width:
        90px;

}


.timeline-time {

    font-size:
        9px;

    color:
        #8da8bb;

}


.timeline-distance {

    font-size:
        10px;

    font-weight:
        700;

    margin-top:
        3px;

}


/* ==========================================================
   WARNING
   ========================================================== */

.warning {

    padding:
        11px;

    border-left:
        3px solid #4d7897;

    background:
        #0a1b2b;

    color:
        #91aabd;

    font-size:
        10px;

    line-height:
        1.5;

}


@media(max-width:900px) {

    .main {

        grid-template-columns:
            1fr;

    }


    .sidebar {

        display:
            none;

    }


    .evidence-grid {

        grid-template-columns:
            1fr 1fr;

    }

}

</style>

</head>


<body>


<!-- ========================================================
     HEADER
     ======================================================== -->

<div class="header">

    <div class="brand">

        <div class="brand-title">
            MARITIME OIL-SPILL INTELLIGENCE
        </div>

        <div class="brand-subtitle">
            Sentinel-1 SAR • AI Detection • Ocean Drift • AIS Attribution
        </div>

    </div>


    <div class="mode">
        ● INVESTIGATION MODE
    </div>

</div>


<!-- ========================================================
     MAIN
     ======================================================== -->

<div class="main">


    <!-- MAP -->

    <div class="map-container">

        <div id="map"></div>

        <div class="map-grid"></div>


        <div class="map-label">

            <div class="map-label-title">
                INDIAN OCEAN — MARITIME INTELLIGENCE
            </div>

            <div class="map-label-sub">
                Real geographic map • Sentinel-1 SAR • AIS correlation
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
                ┄┄ Drift backtracking
            </div>

            <div class="legend-row">
                ▰ Sentinel-1 SAR
            </div>

        </div>

    </div>


    <!-- SIDEBAR -->

    <div class="sidebar">

        <div class="sidebar-heading">
            Oil-spill candidates
        </div>

        <div id="candidateList"></div>

    </div>

</div>


<!-- ========================================================
     INVESTIGATION MODAL
     ======================================================== -->

<div
    id="investigationOverlay"
    class="overlay"
>


    <div class="investigation">


        <div class="investigation-header">

            <div>

                <div
                    id="investigationTitle"
                    class="investigation-title">
                </div>

                <div
                    id="investigationSubtitle"
                    class="investigation-sub">
                </div>

            </div>


            <button
                id="closeInvestigation"
                class="close">
                CLOSE
            </button>

        </div>


        <div
            id="investigationBody"
            class="investigation-body">
        </div>


    </div>

</div>


<script
src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js">
</script>

<script
src="https://unpkg.com/maplibre-gl@5/dist/maplibre-gl.js">
</script>

<script
src="https://unpkg.com/@maplibre/maplibre-gl-leaflet/leaflet-maplibre-gl.js">
</script>


<script>


// ============================================================
// DATA
// ============================================================

const candidates =
__CANDIDATES_JSON__;


const sarBounds =
__SAR_BOUNDS_JSON__;


const sarImage =
"__SAR_DATA_URI__";


// ============================================================
// MAP
// ============================================================

const map =
L.map(
    "map",
    {
        zoomControl: true,
        attributionControl: true,
        preferCanvas: true
    }
);


// ============================================================
// REAL DARK GEOGRAPHIC BASEMAP
// MapLibre renders OpenFreeMap vector tiles inside Leaflet.
// This provides real coastlines, countries, islands, labels,
// smooth zooming and geographic context.
// ============================================================

const realBasemap =
L.maplibreGL({
    style:
        "https://tiles.openfreemap.org/styles/dark"
}).addTo(map);


map.attributionControl.addAttribution(
    'Map data © OpenStreetMap contributors • OpenFreeMap'
);


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
// SAR OVERLAY
// ============================================================

if (
    sarBounds &&
    sarImage
) {

    const bounds = [

        [
            sarBounds.south,
            sarBounds.west
        ],

        [
            sarBounds.north,
            sarBounds.east
        ]

    ];


    const overlay =
        L.imageOverlay(
            sarImage,
            bounds,
            {
                opacity: 0.64,
                interactive: false
            }
        );


    overlay.addTo(
        map
    );

}


// ============================================================
// ICONS
// ============================================================

function icon(
    color,
    size
) {

    return L.divIcon({

        className: "",

        html:
            '<div style="' +

            'width:' +
            size +
            'px;' +

            'height:' +
            size +
            'px;' +

            'background:' +
            color +
            ';' +

            'border:2px solid white;' +

            'border-radius:50%;' +

            'box-shadow:0 0 10px rgba(0,0,0,.9);' +

            '"></div>',

        iconSize:
            [size, size],

        iconAnchor:
            [
                size / 2,
                size / 2
            ]

    });

}


// ============================================================
// MARKERS
// ============================================================

const candidateLayers = [];


candidates.forEach(
    candidate => {


        // ----------------------------------------------------
        // CANDIDATE
        // ----------------------------------------------------

        const marker =
            L.marker(

                [
                    candidate.lat,
                    candidate.lon
                ],

                {
                    icon:
                        icon(
                            "#ff3b30",
                            candidate.id === 3
                                ? 19
                                : 15
                        )
                }

            ).addTo(
                map
            );


        marker.bindTooltip(
            "Candidate #" +
            candidate.id,
            {
                direction:
                    "top"
            }
        );


        marker.on(
            "click",
            function() {

                openInvestigation(
                    candidate.id
                );

            }
        );


        candidateLayers.push(
            marker
        );


        // ----------------------------------------------------
        // DRIFT TRAJECTORY
        // ----------------------------------------------------

        if (
            candidate.trajectory &&
            candidate.trajectory.length >= 2
        ) {

            const points =
                candidate.trajectory.map(
                    p => [
                        p.lat,
                        p.lon
                    ]
                );


            L.polyline(
                points,
                {

                    color:
                        "#d8e8f4",

                    weight:
                        3,

                    opacity:
                        .85,

                    dashArray:
                        "7,8"

                }
            ).addTo(
                map
            );


            // source

            const source =
                candidate.trajectory[
                    candidate.trajectory.length - 1
                ];


            L.marker(

                [
                    source.lat,
                    source.lon
                ],

                {
                    icon:
                        icon(
                            "#ffd60a",
                            14
                        )
                }

            ).addTo(
                map
            )
            .bindTooltip(
                "Estimated source",
                {
                    direction:
                        "top"
                }
            );

        }


        // ----------------------------------------------------
        // AIS
        // ----------------------------------------------------

        candidate.ais.forEach(
            vessel => {


                L.marker(

                    [
                        vessel.lat,
                        vessel.lon
                    ],

                    {
                        icon:
                            icon(
                                "#38a9ff",
                                10
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

                    ${vessel.name}

                    <br>

                    Time:
                    ${
                        vessel.hour !== null
                        ? vessel.hour + ":00 UTC"
                        : "N/A"
                    }

                    <br>

                    Distance:
                    ${
                        vessel.distance !== null
                        ? vessel.distance.toFixed(1) + " km"
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


candidates.forEach(
    (candidate, index) => {


        const card =
            document.createElement(
                "div"
            );


        card.className =
            "card";


        card.dataset.id =
            candidate.id;


        card.innerHTML = `

            <div class="card-head">

                <div class="card-title">
                    Oil-spill candidate #${candidate.id}
                </div>

                <div class="rank">
                    ${index + 1}
                </div>

            </div>


            <div class="metrics">

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
                        ${candidate.attribution.toFixed(1)}
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


            <div class="vessel-box">

                <div class="vessel-name">
                    ${candidate.vessel_name}
                </div>

                <div class="vessel-sub">
                    Highest-ranked potential source vessel
                </div>

                <div class="vessel-sub">

                    Best matching hour:
                    ${
                        candidate.best_hour !== null
                        ? candidate.best_hour + ":00 UTC"
                        : "N/A"
                    }

                </div>

                <span class="evidence">
                    ${candidate.evidence} evidence
                </span>

            </div>

        `;


        card.onclick =
        function() {

            openInvestigation(
                candidate.id
            );

        };


        list.appendChild(
            card
        );

    }
);


// ============================================================
// INVESTIGATION
// ============================================================

function openInvestigation(
    candidateId
) {


    const candidate =
        candidates.find(
            c =>
                c.id === candidateId
        );


    if (!candidate) {
        return;
    }


    // --------------------------------------------------------
    // SELECT CARD
    // --------------------------------------------------------

    document
        .querySelectorAll(".card")
        .forEach(
            card => {

                card.classList.remove(
                    "selected"
                );

            }
        );


    const selectedCard =
        document.querySelector(
            '.card[data-id="' +
            candidateId +
            '"]'
        );


    if (selectedCard) {

        selectedCard.classList.add(
            "selected"
        );

    }


    // --------------------------------------------------------
    // HEADER
    // --------------------------------------------------------

    document.getElementById(
        "investigationTitle"
    ).textContent =
        "CANDIDATE #" +
        candidate.id +
        " — INVESTIGATION";


    document.getElementById(
        "investigationSubtitle"
    ).textContent =
        "Satellite evidence → drift reconstruction → AIS correlation";


    // --------------------------------------------------------
    // BODY
    // --------------------------------------------------------

    const body =
        document.getElementById(
            "investigationBody"
        );


    body.innerHTML = `


        <!-- SATELLITE -->

        <div class="section">

            <div class="section-title">
                Satellite evidence
            </div>


            <div class="evidence-grid">


                <div class="evidence-card">

                    <div class="evidence-card-label">
                        AI OIL SCORE
                    </div>

                    <div class="evidence-card-value">
                        ${candidate.ai_score.toFixed(1)}
                    </div>

                    <div class="evidence-card-unit">
                        / 100
                    </div>

                </div>


                <div class="evidence-card">

                    <div class="evidence-card-label">
                        SAR ANOMALY
                    </div>

                    <div class="evidence-card-value">
                        ${candidate.sar_score.toFixed(1)}
                    </div>

                    <div class="evidence-card-unit">
                        / 100
                    </div>

                </div>


                <div class="evidence-card">

                    <div class="evidence-card-label">
                        SOURCE DISTANCE
                    </div>

                    <div class="evidence-card-value">
                        ${candidate.source_distance.toFixed(1)}
                    </div>

                    <div class="evidence-card-unit">
                        km
                    </div>

                </div>


                <div class="evidence-card">

                    <div class="evidence-card-label">
                        ATTRIBUTION
                    </div>

                    <div class="evidence-card-value">
                        ${candidate.attribution.toFixed(1)}
                    </div>

                    <div class="evidence-card-unit">
                        / 100
                    </div>

                </div>


            </div>

        </div>


        <!-- VESSEL -->

        <div class="section">

            <div class="section-title">
                AIS vessel correlation
            </div>


            <div class="vessel-detail-grid">


                <div class="detail">

                    <div class="detail-label">
                        HIGHEST-RANKED POTENTIAL SOURCE
                    </div>

                    <div class="detail-value">
                        ${candidate.vessel_name}
                    </div>

                </div>


                <div class="detail">

                    <div class="detail-label">
                        VESSEL ID
                    </div>

                    <div class="detail-value">
                        ${candidate.vessel_id}
                    </div>

                </div>


                <div class="detail">

                    <div class="detail-label">
                        BEST MATCHING HOUR
                    </div>

                    <div class="detail-value">

                        ${
                            candidate.best_hour !== null
                            ? candidate.best_hour + ":00 UTC"
                            : "N/A"
                        }

                    </div>

                </div>


                <div class="detail">

                    <div class="detail-label">
                        SOURCE CORRIDOR DISTANCE
                    </div>

                    <div class="detail-value">
                        ${candidate.source_distance.toFixed(1)}
                        km
                    </div>

                </div>


            </div>

        </div>


        <!-- SCORE -->

        <div class="section">

            <div class="section-title">
                Evidence strength
            </div>


            <div class="score-row">

                <div class="score-head">

                    <span>
                        AI oil-spill screening
                    </span>

                    <span>
                        ${candidate.ai_score.toFixed(1)}
                    </span>

                </div>


                <div class="score-track">

                    <div
                        class="score-fill"
                        style="width:${candidate.ai_score}%">
                    </div>

                </div>

            </div>


            <div class="score-row">

                <div class="score-head">

                    <span>
                        SAR anomaly
                    </span>

                    <span>
                        ${candidate.sar_score.toFixed(1)}
                    </span>

                </div>


                <div class="score-track">

                    <div
                        class="score-fill"
                        style="width:${candidate.sar_score}%">
                    </div>

                </div>

            </div>


            <div class="score-row">

                <div class="score-head">

                    <span>
                        Drift-aware attribution
                    </span>

                    <span>
                        ${candidate.attribution.toFixed(1)}
                    </span>

                </div>


                <div class="score-track">

                    <div
                        class="score-fill"
                        style="width:${candidate.attribution}%">
                    </div>

                </div>

            </div>

        </div>


        <!-- TIMELINE -->

        <div class="section">

            <div class="section-title">
                Investigation timeline
            </div>


            <div class="timeline">


                <div class="timeline-item">

                    <div class="timeline-dot"></div>

                    <div class="timeline-time">
                        15:01 UTC
                    </div>

                    <div class="timeline-distance">
                        SAR acquired
                    </div>

                </div>


                <div class="timeline-item">

                    <div class="timeline-dot"></div>

                    <div class="timeline-line"></div>

                    <div class="timeline-time">
                        -1h
                    </div>

                    <div class="timeline-distance">
                        Drift model
                    </div>

                </div>


                <div class="timeline-item">

                    <div class="timeline-dot"></div>

                    <div class="timeline-line"></div>

                    <div class="timeline-time">
                        -3h
                    </div>

                    <div class="timeline-distance">
                        Backtrack
                    </div>

                </div>


                <div class="timeline-item">

                    <div class="timeline-dot"></div>

                    <div class="timeline-line"></div>

                    <div class="timeline-time">
                        ${
                            candidate.best_hour !== null
                            ? candidate.best_hour + ":00"
                            : "N/A"
                        }
                    </div>

                    <div class="timeline-distance">
                        AIS match
                    </div>

                </div>


            </div>

        </div>


        <!-- CONCLUSION -->

        <div class="section">

            <div class="section-title">
                Investigation assessment
            </div>


            <div class="warning">

                <b>
                ${candidate.evidence} evidence
                </b>

                <br><br>

                <b>
                ${candidate.vessel_name}
                </b>
                is the highest-ranked potential
                source vessel for Candidate #${candidate.id}
                under the current prototype scoring model.

                <br><br>

                The result combines satellite screening,
                SAR dark-anomaly detection,
                environmental drift backtracking and
                AIS proximity.

                <br><br>

                This ranking supports investigation and
                response. It does <b>not</b> establish
                legal or causal responsibility.

            </div>

        </div>

    `;


    // --------------------------------------------------------
    // SHOW
    // --------------------------------------------------------

    document.getElementById(
        "investigationOverlay"
    ).style.display =
        "block";


    // --------------------------------------------------------
    // FOCUS MAP
    // --------------------------------------------------------

    map.setView(

        [
            candidate.lat,
            candidate.lon
        ],

        8

    );

}


// ============================================================
// CLOSE
// ============================================================

document.getElementById(
    "closeInvestigation"
).onclick =
function() {

    document.getElementById(
        "investigationOverlay"
    ).style.display =
        "none";

};


// ============================================================
// CLOSE WHEN CLICKING OUTSIDE
// ============================================================

document.getElementById(
    "investigationOverlay"
).onclick =
function(event) {

    if (
        event.target.id ===
        "investigationOverlay"
    ) {

        event.currentTarget.style.display =
            "none";

    }

};


// ============================================================
// ESCAPE
// ============================================================

document.addEventListener(
    "keydown",
    function(event) {

        if (
            event.key === "Escape"
        ) {

            document.getElementById(
                "investigationOverlay"
            ).style.display =
                "none";

        }

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
    json.dumps(
        candidates,
        default=json_safe
    )
)


html = html.replace(
    "__SAR_BOUNDS_JSON__",
    json.dumps(
        sar_bounds,
        default=json_safe
    )
)


html = html.replace(
    "__SAR_DATA_URI__",
    sar_data_uri
)


# ============================================================
# SAVE
# ============================================================

os.makedirs(
    os.path.dirname(
        OUTPUT_FILE
    ),
    exist_ok=True
)


print()
print("Writing dashboard...")


with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as f:

    f.write(
        html
    )


# ============================================================
# DONE
# ============================================================

print()
print("=" * 78)
print("INVESTIGATION DASHBOARD CREATED")
print("=" * 78)

print()
print(
    "Saved:"
)

print(
    OUTPUT_FILE
)

print()

print(
    "Candidates:",
    len(candidates)
)

print()

print(
    "SAR image:",
    "EMBEDDED"
    if sar_data_uri
    else "NOT FOUND"
)

print()

print(
    "Open with:"
)

print(
    "start " + OUTPUT_FILE
)

print()

print("=" * 78)
print("DONE")
print("=" * 78)