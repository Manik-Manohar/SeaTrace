import os
import csv

import numpy as np
import rasterio
from scipy import ndimage
from PIL import Image, ImageDraw


# ============================================================
# CONFIG
# ============================================================

VV_FILE = (
    r"data\processed\sentinel1\geocoded"
    r"\sentinel1_vv_sigma0_db_geocoded.tif"
)

VH_FILE = (
    r"data\processed\sentinel1\geocoded"
    r"\sentinel1_vh_sigma0_db_geocoded.tif"
)

MASK_FILE = (
    r"data\results\geocoded_ocean_mask.png"
)

OUTPUT_DIR = r"data\results"

ANOMALY_FILE = os.path.join(
    OUTPUT_DIR,
    "sar_dark_anomaly_map.png"
)

CANDIDATE_FILE = os.path.join(
    OUTPUT_DIR,
    "sar_candidate_mask.png"
)

OVERLAY_FILE = os.path.join(
    OUTPUT_DIR,
    "sar_candidate_overlay.png"
)

CSV_FILE = os.path.join(
    OUTPUT_DIR,
    "sar_candidates.csv"
)


# ------------------------------------------------------------
# Processing scale
# ------------------------------------------------------------
#
# The full image is ~114 million pixels.
#
# We detect candidates on a 4x reduced image to keep memory
# reasonable. Geographic accuracy is still roughly hundreds
# of metres at this stage. Later we will return to full
# resolution for each candidate.
#

DOWNSAMPLE = 4


# ------------------------------------------------------------
# Local background size
# ------------------------------------------------------------
#
# At the reduced resolution, sigma=25 corresponds to roughly
# 25 * 4 * ~40m = ~4 km.
#
# This allows us to find regions that are significantly darker
# than their surrounding ocean.
#

BACKGROUND_SIGMA = 25


# ------------------------------------------------------------
# Candidate thresholds
# ------------------------------------------------------------

VV_ANOMALY_THRESHOLD = -2.5

VH_ANOMALY_THRESHOLD = -1.0

# Avoid extremely bright land/coastal returns.
VV_MAX_FOR_CANDIDATE = -18.0

# Minimum and maximum candidate size in reduced pixels.
MIN_AREA = 20
MAX_AREA = 15000


# ============================================================
# HELPERS
# ============================================================

def resize_mask(mask, height, width):

    image = Image.fromarray(
        (mask.astype(np.uint8) * 255)
    )

    image = image.resize(
        (width, height),
        Image.Resampling.NEAREST
    )

    return np.array(image) > 127


def normalize_image(image, valid):

    values = image[valid]

    low = np.percentile(
        values,
        2
    )

    high = np.percentile(
        values,
        98
    )

    display = np.clip(
        image,
        low,
        high
    )

    display = (
        (display - low)
        /
        (high - low + 1e-8)
        * 255
    )

    display[~valid] = 0

    return np.clip(
        display,
        0,
        255
    ).astype(np.uint8)


# ============================================================
# MAIN
# ============================================================

print("=" * 70)
print("SAR DARK-ANOMALY CANDIDATE DETECTION")
print("=" * 70)


# ============================================================
# LOAD DATA
# ============================================================

print("\nLoading Sentinel-1 VV...")

with rasterio.open(VV_FILE) as src:

    vv_full = src.read(1).astype(
        np.float32
    )

    bounds = src.bounds
    transform = src.transform
    crs = src.crs

    full_height = src.height
    full_width = src.width


print("Loading Sentinel-1 VH...")

with rasterio.open(VH_FILE) as src:

    vh_full = src.read(1).astype(
        np.float32
    )


print(
    f"Full resolution: "
    f"{full_width} x {full_height}"
)


# ============================================================
# LOAD OCEAN MASK
# ============================================================

print("\nLoading ocean mask...")

mask_full = np.array(
    Image.open(
        MASK_FILE
    ).convert("L")
) > 127


if mask_full.shape != vv_full.shape:

    raise RuntimeError(
        "Ocean mask dimensions do not match "
        "the Sentinel-1 image."
    )


# ============================================================
# DOWNSAMPLE
# ============================================================

print(
    f"\nDownsampling by factor {DOWNSAMPLE}..."
)

height = full_height // DOWNSAMPLE
width = full_width // DOWNSAMPLE


vv = vv_full[
    :height * DOWNSAMPLE,
    :width * DOWNSAMPLE
].reshape(
    height,
    DOWNSAMPLE,
    width,
    DOWNSAMPLE
).mean(
    axis=(1, 3)
)


vh = vh_full[
    :height * DOWNSAMPLE,
    :width * DOWNSAMPLE
].reshape(
    height,
    DOWNSAMPLE,
    width,
    DOWNSAMPLE
).mean(
    axis=(1, 3)
)


ocean = resize_mask(
    mask_full,
    height,
    width
)


# ============================================================
# VALID PIXELS
# ============================================================

valid = (
    ocean
    &
    np.isfinite(vv)
    &
    np.isfinite(vh)
    &
    (vv != 0)
    &
    (vh != 0)
)


print(
    f"Reduced image: "
    f"{width} x {height}"
)

print(
    f"Valid ocean pixels: "
    f"{np.sum(valid):,}"
)


# ============================================================
# LOCAL BACKGROUND — VV
# ============================================================

print(
    "\nCalculating local VV background..."
)

vv_data = np.zeros_like(
    vv,
    dtype=np.float32
)

vv_data[valid] = vv[valid]

weights = valid.astype(
    np.float32
)

smooth_vv = ndimage.gaussian_filter(
    vv_data,
    sigma=BACKGROUND_SIGMA,
    mode="nearest"
)

smooth_weights = ndimage.gaussian_filter(
    weights,
    sigma=BACKGROUND_SIGMA,
    mode="nearest"
)

global_vv = np.median(
    vv[valid]
)

vv_background = np.full_like(
    vv,
    global_vv,
    dtype=np.float32
)

good = smooth_weights > 0.05

vv_background[good] = (
    smooth_vv[good]
    /
    smooth_weights[good]
)


vv_anomaly = np.zeros_like(
    vv,
    dtype=np.float32
)

vv_anomaly[valid] = (
    vv[valid]
    -
    vv_background[valid]
)


# ============================================================
# LOCAL BACKGROUND — VH
# ============================================================

print(
    "Calculating local VH background..."
)

vh_data = np.zeros_like(
    vh,
    dtype=np.float32
)

vh_data[valid] = vh[valid]

smooth_vh = ndimage.gaussian_filter(
    vh_data,
    sigma=BACKGROUND_SIGMA,
    mode="nearest"
)

vh_background = np.full_like(
    vh,
    np.median(vh[valid]),
    dtype=np.float32
)

vh_background[good] = (
    smooth_vh[good]
    /
    smooth_weights[good]
)

vh_anomaly = np.zeros_like(
    vh,
    dtype=np.float32
)

vh_anomaly[valid] = (
    vh[valid]
    -
    vh_background[valid]
)


# ============================================================
# BASIC STATISTICS
# ============================================================

print("\nStatistics:")

print(
    f"VV median: "
    f"{np.median(vv[valid]):.2f} dB"
)

print(
    f"VH median: "
    f"{np.median(vh[valid]):.2f} dB"
)

print(
    f"VV anomaly median: "
    f"{np.median(vv_anomaly[valid]):.2f} dB"
)

print(
    f"VH anomaly median: "
    f"{np.median(vh_anomaly[valid]):.2f} dB"
)


# ============================================================
# DARK ANOMALY CONDITIONS
# ============================================================

print("\nBuilding candidate mask...")


vv_dark = (
    vv_anomaly
    <=
    VV_ANOMALY_THRESHOLD
)

vh_support = (
    vh_anomaly
    <=
    VH_ANOMALY_THRESHOLD
)

vv_not_extreme = (
    vv
    <=
    VV_MAX_FOR_CANDIDATE
)


# Primary detection:
#
# A region must be significantly darker in VV.
#
# VH is used as supporting evidence rather than a mandatory
# requirement because oil signatures can vary between
# polarizations.

candidate = (
    valid
    &
    vv_dark
    &
    vv_not_extreme
)


# ============================================================
# MORPHOLOGICAL CLEANING
# ============================================================

print(
    "Cleaning candidate regions..."
)

# Remove single-pixel noise.
candidate = ndimage.binary_opening(
    candidate,
    structure=np.ones((3, 3))
)

# Connect nearby pixels.
candidate = ndimage.binary_closing(
    candidate,
    structure=np.ones((5, 5))
)


# ============================================================
# CONNECTED COMPONENTS
# ============================================================

labels, count = ndimage.label(
    candidate
)

print(
    f"Initial connected regions: {count}"
)


components = []

for region_id in range(
    1,
    count + 1
):

    ys, xs = np.where(
        labels == region_id
    )

    if len(xs) == 0:
        continue

    area = len(xs)

    if area < MIN_AREA:
        continue

    if area > MAX_AREA:
        continue

    min_x = xs.min()
    max_x = xs.max()
    min_y = ys.min()
    max_y = ys.max()

    bbox_width = (
        max_x - min_x + 1
    )

    bbox_height = (
        max_y - min_y + 1
    )

    # --------------------------------------------------------
    # Shape metrics
    # --------------------------------------------------------

    bbox_area = (
        bbox_width
        *
        bbox_height
    )

    fill_ratio = (
        area
        /
        max(bbox_area, 1)
    )

    aspect_ratio = (
        max(bbox_width, bbox_height)
        /
        max(
            min(bbox_width, bbox_height),
            1
        )
    )

    # --------------------------------------------------------
    # Average anomaly
    # --------------------------------------------------------

    region_vv_anomaly = vv_anomaly[
        labels == region_id
    ]

    mean_anomaly = float(
        np.mean(
            region_vv_anomaly
        )
    )

    min_anomaly = float(
        np.min(
            region_vv_anomaly
        )
    )

    region_vh_anomaly = vh_anomaly[
        labels == region_id
    ]

    mean_vh_anomaly = float(
        np.mean(
            region_vh_anomaly
        )
    )

    vh_support_ratio = float(
        np.mean(
            region_vh_anomaly
            <=
            VH_ANOMALY_THRESHOLD
        )
    )

    # --------------------------------------------------------
    # Reject extreme stripe-like regions
    #
    # Very long, thin structures are more likely to be
    # acquisition artifacts than compact slicks.
    # --------------------------------------------------------

    if aspect_ratio > 12:
        continue

    # --------------------------------------------------------
    # Score
    # --------------------------------------------------------

    score = 0.0

    # VV anomaly
    score += min(
        abs(mean_anomaly) * 10,
        40
    )

    # VH support
    score += (
        vh_support_ratio
        *
        25
    )

    # Shape/fill
    score += (
        min(fill_ratio, 1.0)
        *
        20
    )

    # Moderate area preference
    if area >= 50:
        score += 5

    components.append(
        {
            "id": region_id,
            "area_reduced_pixels": area,
            "bbox_x": int(min_x),
            "bbox_y": int(min_y),
            "bbox_width": int(bbox_width),
            "bbox_height": int(bbox_height),
            "fill_ratio": float(fill_ratio),
            "aspect_ratio": float(aspect_ratio),
            "mean_vv_anomaly_db": mean_anomaly,
            "min_vv_anomaly_db": min_anomaly,
            "mean_vh_anomaly_db": mean_vh_anomaly,
            "vh_support_ratio": vh_support_ratio,
            "score": float(score)
        }
    )


# ============================================================
# SORT
# ============================================================

components.sort(
    key=lambda x: x["score"],
    reverse=True
)


# Keep the strongest 50.

components = components[:50]


print(
    f"\nCandidate regions retained: "
    f"{len(components)}"
)


# ============================================================
# GEOLOCATION
# ============================================================

print(
    "\nConverting candidate centers to coordinates..."
)

for rank, component in enumerate(
    components,
    start=1
):

    cx = (
        component["bbox_x"]
        +
        component["bbox_width"] / 2
    )

    cy = (
        component["bbox_y"]
        +
        component["bbox_height"] / 2
    )

    # Convert reduced-image coordinates to original
    # geocoded raster pixel coordinates.

    full_x = (
        cx * DOWNSAMPLE
    )

    full_y = (
        cy * DOWNSAMPLE
    )

    lon, lat = rasterio.transform.xy(
        transform,
        full_y,
        full_x
    )

    component["rank"] = rank

    component["pixel_x"] = float(
        full_x
    )

    component["pixel_y"] = float(
        full_y
    )

    component["longitude"] = float(
        lon
    )

    component["latitude"] = float(
        lat
    )


# ============================================================
# PRINT TOP CANDIDATES
# ============================================================

print("\nTop candidates:")

for component in components[:15]:

    print(
        f"\n#{component['rank']} "
        f"score={component['score']:.1f}"
    )

    print(
        f"  Lat/Lon: "
        f"{component['latitude']:.6f}, "
        f"{component['longitude']:.6f}"
    )

    print(
        f"  Area: "
        f"{component['area_reduced_pixels']} reduced px"
    )

    print(
        f"  VV anomaly: "
        f"{component['mean_vv_anomaly_db']:.2f} dB"
    )

    print(
        f"  VH support: "
        f"{component['vh_support_ratio'] * 100:.1f}%"
    )

    print(
        f"  Aspect ratio: "
        f"{component['aspect_ratio']:.2f}"
    )


# ============================================================
# SAVE CSV
# ============================================================

fieldnames = [
    "id",
    "rank",
    "score",
    "latitude",
    "longitude",
    "pixel_x",
    "pixel_y",
    "area_reduced_pixels",
    "bbox_x",
    "bbox_y",
    "bbox_width",
    "bbox_height",
    "fill_ratio",
    "aspect_ratio",
    "mean_vv_anomaly_db",
    "min_vv_anomaly_db",
    "mean_vh_anomaly_db",
    "vh_support_ratio"
]

with open(
    CSV_FILE,
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
        components
    )


print(
    f"\nSaved candidate table:"
)

print(
    CSV_FILE
)


# ============================================================
# SAVE ANOMALY MAP
# ============================================================

print(
    "\nCreating anomaly visualization..."
)

anomaly_display = np.clip(
    vv_anomaly,
    -5,
    5
)

valid_anomaly = valid

low = -5.0
high = 5.0

anomaly_display = (
    (anomaly_display - low)
    /
    (high - low)
    *
    255
)

anomaly_display[
    ~valid_anomaly
] = 0

anomaly_display = np.clip(
    anomaly_display,
    0,
    255
).astype(
    np.uint8
)


anomaly_img = Image.fromarray(
    anomaly_display
)

anomaly_img.save(
    ANOMALY_FILE
)

print(
    f"Saved:\n{ANOMALY_FILE}"
)


# ============================================================
# SAVE CANDIDATE MASK
# ============================================================

candidate_display = (
    candidate.astype(
        np.uint8
    )
    *
    255
)

Image.fromarray(
    candidate_display
).save(
    CANDIDATE_FILE
)

print(
    f"Saved:\n{CANDIDATE_FILE}"
)


# ============================================================
# CREATE OVERLAY
# ============================================================

print(
    "\nCreating candidate overlay..."
)

base = normalize_image(
    vv,
    valid
)

rgb = np.stack(
    [
        base,
        base,
        base
    ],
    axis=-1
)


# Draw candidate regions.

overlay = Image.fromarray(
    rgb
).convert("RGB")

draw = ImageDraw.Draw(
    overlay
)

for component in components:

    x1 = component["bbox_x"]
    y1 = component["bbox_y"]

    x2 = (
        x1
        +
        component["bbox_width"]
    )

    y2 = (
        y1
        +
        component["bbox_height"]
    )

    draw.rectangle(
        [
            x1,
            y1,
            x2,
            y2
        ],
        outline=(255, 0, 0),
        width=2
    )

    draw.text(
        (
            x1 + 2,
            y1 + 2
        ),
        f"#{component['rank']}",
        fill=(255, 0, 0)
    )


overlay.save(
    OVERLAY_FILE
)

print(
    f"Saved:\n{OVERLAY_FILE}"
)


# ============================================================
# COMPLETE
# ============================================================

print("\n" + "=" * 70)
print("SAR CANDIDATE DETECTION COMPLETE")
print("=" * 70)