import os
import json
import urllib.parse
import urllib.request
import urllib.error
import pandas as pd


# ============================================================
# GFW UNKNOWN VESSEL IDENTITY RESOLVER
# ============================================================

AIS_FILE = (
    "data/results/gfw_hourly_vessel_proximity.csv"
)

ATTRIBUTION_FILE = (
    "data/results/drift_aware_vessel_attribution.csv"
)

OUTPUT_DIR = "data/results"

OUTPUT_FILE = os.path.join(
    OUTPUT_DIR,
    "resolved_vessel_identities.csv"
)

RAW_FILE = os.path.join(
    OUTPUT_DIR,
    "gfw_vessel_identity_raw.json"
)

GFW_BASE_URL = (
    "https://gateway.api.globalfishingwatch.org"
)

DATASET = (
    "public-global-vessel-identity:latest"
)


# ============================================================
# CHECK TOKEN
# ============================================================

TOKEN = os.environ.get(
    "GFW_API_TOKEN"
)

if not TOKEN:

    print()
    print("=" * 70)
    print("ERROR")
    print("=" * 70)

    print()
    print(
        "GFW_API_TOKEN is not available "
        "in this PowerShell session."
    )

    print()
    print(
        "Make sure you loaded your GFW token "
        "before running this script."
    )

    raise SystemExit(1)


# ============================================================
# LOAD ATTRIBUTION DATA
# ============================================================

print()
print("=" * 70)
print("GFW VESSEL IDENTITY RESOLUTION")
print("=" * 70)

print()
print("Loading attribution data...")

if not os.path.exists(
    ATTRIBUTION_FILE
):

    print()
    print(
        "ERROR: Attribution file not found:"
    )

    print(
        ATTRIBUTION_FILE
    )

    raise SystemExit(1)


attr_df = pd.read_csv(
    ATTRIBUTION_FILE
)

print(
    "Attribution records:",
    len(attr_df)
)


# ============================================================
# FIND UNKNOWN VESSEL IDs
# ============================================================

unknown_df = attr_df[
    (
        attr_df["vessel_name"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
        .isin([
            "",
            "UNKNOWN",
            "NAN"
        ])
    )
].copy()


unknown_ids = sorted(
    set(
        unknown_df[
            "vessel_id"
        ]
        .fillna("")
        .astype(str)
        .str.strip()
        .tolist()
    )
)


unknown_ids = [
    vessel_id
    for vessel_id in unknown_ids
    if vessel_id
    and vessel_id.lower() != "nan"
]


print()
print(
    "Unknown vessel IDs found:",
    len(unknown_ids)
)


for vessel_id in unknown_ids:

    print(
        "  ",
        vessel_id
    )


if not unknown_ids:

    print()
    print(
        "No unknown vessel IDs require resolution."
    )

    raise SystemExit(0)


# ============================================================
# GFW API REQUEST
# ============================================================

def get_vessel(
    vessel_id
):

    encoded_id = urllib.parse.quote(
        vessel_id,
        safe=""
    )

    encoded_dataset = urllib.parse.quote(
        DATASET,
        safe=""
    )

    url = (
        GFW_BASE_URL
        +
        "/v3/vessels/"
        +
        encoded_id
        +
        "?dataset="
        +
        encoded_dataset
    )

    request = urllib.request.Request(
        url,
        headers={
            "Authorization":
                f"Bearer {TOKEN}",

            "Accept":
                "application/json",

            "User-Agent":
                "Maritime-Oil-Spill-Research/1.0"
        }
    )

    try:

        with urllib.request.urlopen(
            request,
            timeout=60
        ) as response:

            body = response.read().decode(
                "utf-8"
            )

            return json.loads(
                body
            )

    except urllib.error.HTTPError as e:

        body = ""

        try:
            body = e.read().decode(
                "utf-8"
            )
        except Exception:
            pass

        print()
        print(
            f"HTTP ERROR {e.code} "
            f"for vessel {vessel_id}"
        )

        if body:
            print(body[:1000])

        return None

    except Exception as e:

        print()
        print(
            f"ERROR resolving {vessel_id}:"
        )

        print(
            str(e)
        )

        return None


# ============================================================
# EXTRACT IDENTITY
# ============================================================

def extract_identity(
    vessel_id,
    data
):

    if not data:

        return {
            "vessel_id":
                vessel_id,

            "status":
                "NOT_FOUND"
        }


    result = {
        "vessel_id":
            vessel_id,

        "status":
            "FOUND"
    }


    # --------------------------------------------------------
    # Self-reported AIS information
    # --------------------------------------------------------

    self_reported = (
        data.get(
            "selfReportedInfo"
        )
    )


    if isinstance(
        self_reported,
        list
    ):

        if self_reported:

            info = self_reported[0]

        else:

            info = {}

    elif isinstance(
        self_reported,
        dict
    ):

        info = self_reported

    else:

        info = {}


    result["ais_name"] = (
        info.get(
            "shipname"
        )
        or
        info.get(
            "nShipname"
        )
        or
        ""
    )


    result["mmsi"] = (
        info.get(
            "ssvid"
        )
        or
        ""
    )


    result["imo"] = (
        info.get(
            "imo"
        )
        or
        ""
    )


    result["flag"] = (
        info.get(
            "flag"
        )
        or
        ""
    )


    result["callsign"] = (
        info.get(
            "callsign"
        )
        or
        ""
    )


    result["shiptype"] = (
        info.get(
            "shiptype"
        )
        or
        ""
    )


    # --------------------------------------------------------
    # Registry information
    # --------------------------------------------------------

    registry_info = (
        data.get(
            "registryInfo"
        )
    )


    if isinstance(
        registry_info,
        list
    ) and registry_info:

        registry = registry_info[0]


        if not result["ais_name"]:

            result["registry_name"] = (
                registry.get(
                    "shipname"
                )
                or
                ""
            )

        else:

            result["registry_name"] = (
                registry.get(
                    "shipname"
                )
                or
                ""
            )


        if not result["mmsi"]:

            result["registry_mmsi"] = (
                registry.get(
                    "ssvid"
                )
                or
                ""
            )

        else:

            result["registry_mmsi"] = (
                registry.get(
                    "ssvid"
                )
                or
                ""
            )


        if not result["imo"]:

            result["registry_imo"] = (
                registry.get(
                    "imo"
                )
                or
                ""
            )

        else:

            result["registry_imo"] = (
                registry.get(
                    "imo"
                )
                or
                ""
            )


        if not result["flag"]:

            result["registry_flag"] = (
                registry.get(
                    "flag"
                )
                or
                ""
            )

        else:

            result["registry_flag"] = (
                registry.get(
                    "flag"
                )
                or
                ""
            )

    else:

        result["registry_name"] = ""
        result["registry_mmsi"] = ""
        result["registry_imo"] = ""
        result["registry_flag"] = ""


    # --------------------------------------------------------
    # Related information
    # --------------------------------------------------------

    result["registry_records"] = (
        data.get(
            "registryInfoTotalRecords",
            0
        )
    )


    return result


# ============================================================
# RESOLVE ALL UNKNOWN IDs
# ============================================================

resolved = []

raw_responses = {}


for index, vessel_id in enumerate(
    unknown_ids,
    start=1
):

    print()
    print("-" * 70)

    print(
        f"[{index}/{len(unknown_ids)}]"
    )

    print(
        "Resolving:"
    )

    print(
        vessel_id
    )

    print("-" * 70)


    data = get_vessel(
        vessel_id
    )


    if data is not None:

        raw_responses[
            vessel_id
        ] = data


    identity = extract_identity(
        vessel_id,
        data
    )


    resolved.append(
        identity
    )


    if identity.get(
        "status"
    ) == "FOUND":

        print()

        print(
            "Name:",
            identity.get(
                "ais_name",
                ""
            )
            or
            identity.get(
                "registry_name",
                ""
            )
            or
            "UNKNOWN"
        )

        print(
            "MMSI:",
            identity.get(
                "mmsi",
                ""
            )
            or
            identity.get(
                "registry_mmsi",
                ""
            )
            or
            "N/A"
        )

        print(
            "IMO:",
            identity.get(
                "imo",
                ""
            )
            or
            identity.get(
                "registry_imo",
                ""
            )
            or
            "N/A"
        )

        print(
            "Flag:",
            identity.get(
                "flag",
                ""
            )
            or
            identity.get(
                "registry_flag",
                ""
            )
            or
            "N/A"
        )

        print(
            "Callsign:",
            identity.get(
                "callsign",
                ""
            )
            or
            "N/A"
        )

        print(
            "Ship type:",
            identity.get(
                "shiptype",
                ""
            )
            or
            "N/A"
        )

    else:

        print(
            "Identity not found."
        )


# ============================================================
# SAVE RAW API RESPONSES
# ============================================================

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


with open(
    RAW_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        raw_responses,
        f,
        indent=2
    )


# ============================================================
# SAVE RESOLVED TABLE
# ============================================================

resolved_df = pd.DataFrame(
    resolved
)


resolved_df.to_csv(
    OUTPUT_FILE,
    index=False
)


# ============================================================
# FINISH
# ============================================================

print()
print("=" * 70)

print(
    "VESSEL IDENTITY RESOLUTION COMPLETE"
)

print("=" * 70)

print()

print(
    "Resolved vessels:",
    len(resolved_df)
)

print()

print(
    "Saved:"
)

print(
    OUTPUT_FILE
)

print()

print(
    "Raw API responses:"
)

print(
    RAW_FILE
)

print()

print(
    "GFW Vessel API was used to resolve"
)

print(
    "the previously unknown vessel IDs."
)

print()
print("=" * 70)
print("DONE")
print("=" * 70)