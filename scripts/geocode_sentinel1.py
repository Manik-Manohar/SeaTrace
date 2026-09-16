import os
import glob
import xml.etree.ElementTree as ET

import numpy as np
import rasterio
from rasterio.control import GroundControlPoint
from rasterio.transform import from_bounds
from rasterio.warp import reproject, Resampling


# ============================================================
# CONFIG
# ============================================================

SAFE_DIR = r"data\raw\sentinel1"
INPUT_DIR = r"data\processed\sentinel1"
OUTPUT_DIR = r"data\processed\sentinel1\geocoded"

DST_CRS = "EPSG:4326"

# Approximately 40 m in latitude/longitude.
# This is appropriate for the EW GRD medium-resolution product.
RESOLUTION_DEG = 0.0004


# ============================================================
# FIND FILES
# ============================================================

def find_annotation():

    annotation_dir = os.path.join(
        SAFE_DIR,
        "annotation"
    )

    files = glob.glob(
        os.path.join(
            annotation_dir,
            "*.xml"
        )
    )

    # We need the product annotation XML,
    # NOT the calibration/noise XML.
    candidates = [
        f for f in files
        if "calibration" not in os.path.basename(f).lower()
        and "noise" not in os.path.basename(f).lower()
    ]

    if not candidates:
        raise FileNotFoundError(
            "Main Sentinel-1 annotation XML not found."
        )

    print("Annotation XML:")
    print(candidates[0])

    return candidates[0]


# ============================================================
# PARSE GEOLOCATION GRID
# ============================================================

def parse_geolocation_grid(xml_path):

    print("\nReading geolocation grid...")

    tree = ET.parse(xml_path)
    root = tree.getroot()

    points = []

    for node in root.iter():

        if not node.tag.endswith(
            "geolocationGridPoint"
        ):
            continue

        values = {}

        for child in node:

            tag = child.tag.split("}")[-1]

            if tag in [
                "line",
                "pixel",
                "latitude",
                "longitude"
            ]:

                if child.text is not None:
                    values[tag] = float(
                        child.text.strip()
                    )

        required = [
            "line",
            "pixel",
            "latitude",
            "longitude"
        ]

        if all(k in values for k in required):

            points.append(
                values
            )

    if not points:

        raise RuntimeError(
            "No geolocation grid points found."
        )

    print(
        f"Geolocation points found: {len(points)}"
    )

    lines = np.array(
        [p["line"] for p in points],
        dtype=np.float64
    )

    pixels = np.array(
        [p["pixel"] for p in points],
        dtype=np.float64
    )

    lats = np.array(
        [p["latitude"] for p in points],
        dtype=np.float64
    )

    lons = np.array(
        [p["longitude"] for p in points],
        dtype=np.float64
    )

    print(
        f"Line range: {lines.min():.1f} -> {lines.max():.1f}"
    )

    print(
        f"Pixel range: {pixels.min():.1f} -> {pixels.max():.1f}"
    )

    print(
        f"Latitude range: "
        f"{lats.min():.6f} -> {lats.max():.6f}"
    )

    print(
        f"Longitude range: "
        f"{lons.min():.6f} -> {lons.max():.6f}"
    )

    return points


# ============================================================
# CREATE GCPs
# ============================================================

def create_gcps(points):

    gcps = []

    for p in points:

        gcps.append(
            GroundControlPoint(
                row=p["line"],
                col=p["pixel"],
                x=p["longitude"],
                y=p["latitude"],
                z=0
            )
        )

    return gcps


# ============================================================
# GEOCODE ONE BAND
# ============================================================

def geocode_band(
    input_path,
    output_path,
    gcps
):

    print("\n" + "=" * 70)
    print("GEOCODING")
    print("=" * 70)

    print(
        f"Input:\n{input_path}"
    )

    with rasterio.open(input_path) as src:

        width = src.width
        height = src.height

        print(
            f"Input size: {width} x {height}"
        )

        # ----------------------------------------------------
        # Calculate geographic bounds from GCPs
        # ----------------------------------------------------

        lons = np.array(
            [g.x for g in gcps],
            dtype=np.float64
        )

        lats = np.array(
            [g.y for g in gcps],
            dtype=np.float64
        )

        west = float(lons.min())
        east = float(lons.max())
        south = float(lats.min())
        north = float(lats.max())

        # Small margin
        margin_x = 0.01
        margin_y = 0.01

        west -= margin_x
        east += margin_x
        south -= margin_y
        north += margin_y

        dst_width = int(
            np.ceil(
                (east - west)
                /
                RESOLUTION_DEG
            )
        )

        dst_height = int(
            np.ceil(
                (north - south)
                /
                RESOLUTION_DEG
            )
        )

        transform = from_bounds(
            west,
            south,
            east,
            north,
            dst_width,
            dst_height
        )

        print(
            f"Output size: "
            f"{dst_width} x {dst_height}"
        )

        print(
            f"Geographic bounds:"
        )

        print(
            f"  West : {west:.6f}"
        )

        print(
            f"  East : {east:.6f}"
        )

        print(
            f"  South: {south:.6f}"
        )

        print(
            f"  North: {north:.6f}"
        )

        destination = np.zeros(
            (
                dst_height,
                dst_width
            ),
            dtype=np.float32
        )

        source = src.read(
            1
        ).astype(
            np.float32
        )

        # ----------------------------------------------------
        # Reproject using Sentinel-1 GCP geolocation
        # ----------------------------------------------------

        print(
            "\nWarping using Sentinel-1 "
            "geolocation GCPs..."
        )

        reproject(
            source=source,
            destination=destination,

            gcps=gcps,

            src_crs="EPSG:4326",

            dst_transform=transform,
            dst_crs=DST_CRS,

            src_nodata=0,
            dst_nodata=0,

            resampling=Resampling.bilinear
        )

        profile = {
            "driver": "GTiff",
            "height": dst_height,
            "width": dst_width,
            "count": 1,
            "dtype": "float32",
            "crs": DST_CRS,
            "transform": transform,
            "nodata": 0,
            "compress": "deflate",
            "predictor": 3,
            "tiled": True
        }

        os.makedirs(
            os.path.dirname(output_path),
            exist_ok=True
        )

        with rasterio.open(
            output_path,
            "w",
            **profile
        ) as dst:

            dst.write(
                destination,
                1
            )

        print(
            f"\nSaved:"
        )

        print(
            output_path
        )


# ============================================================
# VALIDATE OUTPUT
# ============================================================

def validate_output(path):

    print("\nValidating output...")

    with rasterio.open(path) as src:

        print(
            f"CRS: {src.crs}"
        )

        print(
            f"Size: "
            f"{src.width} x {src.height}"
        )

        print(
            f"Bounds:"
        )

        print(
            f"  left   = {src.bounds.left:.6f}"
        )

        print(
            f"  right  = {src.bounds.right:.6f}"
        )

        print(
            f"  bottom = {src.bounds.bottom:.6f}"
        )

        print(
            f"  top    = {src.bounds.top:.6f}"
        )

        print(
            f"Transform:"
        )

        print(
            src.transform
        )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print("=" * 70)
    print("SENTINEL-1 GEOCODING")
    print("=" * 70)

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    annotation = find_annotation()

    points = parse_geolocation_grid(
        annotation
    )

    gcps = create_gcps(
        points
    )

    print(
        f"\nCreated {len(gcps)} Ground Control Points."
    )

    vv_input = os.path.join(
        INPUT_DIR,
        "sentinel1_vv_sigma0_db.tif"
    )

    vh_input = os.path.join(
        INPUT_DIR,
        "sentinel1_vh_sigma0_db.tif"
    )

    vv_output = os.path.join(
        OUTPUT_DIR,
        "sentinel1_vv_sigma0_db_geocoded.tif"
    )

    vh_output = os.path.join(
        OUTPUT_DIR,
        "sentinel1_vh_sigma0_db_geocoded.tif"
    )

    if not os.path.exists(vv_input):
        raise FileNotFoundError(
            vv_input
        )

    if not os.path.exists(vh_input):
        raise FileNotFoundError(
            vh_input
        )

    # --------------------------------------------------------
    # VV
    # --------------------------------------------------------

    geocode_band(
        vv_input,
        vv_output,
        gcps
    )

    # --------------------------------------------------------
    # VH
    # --------------------------------------------------------

    geocode_band(
        vh_input,
        vh_output,
        gcps
    )

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("VV OUTPUT")
    print("=" * 70)

    validate_output(
        vv_output
    )

    print("\n" + "=" * 70)
    print("VH OUTPUT")
    print("=" * 70)

    validate_output(
        vh_output
    )

    print("\n" + "=" * 70)
    print("GEOCODING COMPLETE")
    print("=" * 70)