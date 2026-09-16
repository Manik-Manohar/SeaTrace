import os

import numpy as np
import rasterio
from scipy import ndimage
from PIL import Image


# ============================================================
# CONFIG
# ============================================================

INPUT_FILE = (
    r"data\processed\sentinel1\geocoded"
    r"\sentinel1_vv_sigma0_db_geocoded.tif"
)

MASK_FILE = (
    r"data\results\geocoded_ocean_mask.png"
)

OUTPUT_DIR = r"data\processed\sentinel1\geocoded"

OUTPUT_FILE = os.path.join(
    OUTPUT_DIR,
    "sentinel1_vv_destriped_db.tif"
)

PREVIEW_FILE = (
    r"data\results\sentinel1_vv_destriped_preview.png"
)

ANOMALY_PREVIEW_FILE = (
    r"data\results\sentinel1_vv_local_anomaly_preview.png"
)

# Size of the broad background window.
#
# This is intentionally large so that we estimate broad
# acquisition/background variations rather than removing
# normal SAR texture.
BACKGROUND_SIGMA = 120.0


# ============================================================
# LOAD
# ============================================================

print("=" * 70)
print("SENTINEL-1 VV DESTRIPING")
print("=" * 70)

print("\nInput:")
print(INPUT_FILE)

with rasterio.open(INPUT_FILE) as src:

    vv = src.read(1).astype(np.float32)

    profile = src.profile.copy()

    height = src.height
    width = src.width

    print(f"Size: {width} x {height}")
    print(f"CRS: {src.crs}")
    print(f"Bounds: {src.bounds}")


# ============================================================
# LOAD OCEAN MASK
# ============================================================

print("\nLoading ocean mask...")

mask_image = Image.open(
    MASK_FILE
).convert("L")

mask = np.array(
    mask_image
) > 127

if mask.shape != vv.shape:

    raise RuntimeError(
        f"Mask shape {mask.shape} does not match "
        f"VV shape {vv.shape}"
    )

print(
    f"Ocean pixels: {np.sum(mask):,}"
)


# ============================================================
# VALID DATA
# ============================================================

valid = (
    np.isfinite(vv)
    &
    (vv != 0)
    &
    mask
)

print(
    f"Valid ocean pixels: {np.sum(valid):,}"
)


# ============================================================
# ROBUST GLOBAL REFERENCE
# ============================================================

values = vv[valid]

global_median = np.median(
    values
)

print(
    f"Global ocean median: "
    f"{global_median:.2f} dB"
)


# ============================================================
# CREATE VALIDITY WEIGHT
# ============================================================

# Gaussian filtering cannot directly handle NaN values
# correctly, so we calculate:
#
#   weighted_sum / weighted_weight
#
# only over valid ocean pixels.

data = np.zeros_like(
    vv,
    dtype=np.float32
)

data[valid] = vv[valid]

weights = valid.astype(
    np.float32
)


# ============================================================
# BROAD BACKGROUND
# ============================================================

print(
    "\nEstimating broad SAR background..."
)

smooth_data = ndimage.gaussian_filter(
    data,
    sigma=BACKGROUND_SIGMA,
    mode="nearest"
)

smooth_weights = ndimage.gaussian_filter(
    weights,
    sigma=BACKGROUND_SIGMA,
    mode="nearest"
)

background = np.full_like(
    vv,
    global_median,
    dtype=np.float32
)

good_background = (
    smooth_weights > 0.05
)

background[
    good_background
] = (
    smooth_data[
        good_background
    ]
    /
    smooth_weights[
        good_background
    ]
)


# ============================================================
# LOCAL ANOMALY
# ============================================================
#
# Negative values mean the pixel is darker than its
# surrounding broad-scale background.
#
# This is useful for oil-slick candidate detection because
# oil can reduce sea-surface radar backscatter.
#

anomaly = np.zeros_like(
    vv,
    dtype=np.float32
)

anomaly[valid] = (
    vv[valid]
    -
    background[valid]
)


# ============================================================
# LIMIT EXTREME ANOMALIES
# ============================================================

valid_anomaly = anomaly[
    valid
]

p_low = np.percentile(
    valid_anomaly,
    1
)

p_high = np.percentile(
    valid_anomaly,
    99
)

print(
    f"Anomaly 1st percentile : "
    f"{p_low:.2f} dB"
)

print(
    f"Anomaly 99th percentile: "
    f"{p_high:.2f} dB"
)


# ============================================================
# CREATE DESTRIPED IMAGE
# ============================================================
#
# Correct the broad background while preserving the overall
# approximate scene brightness.
#

destriped = np.zeros_like(
    vv,
    dtype=np.float32
)

destriped[valid] = (
    vv[valid]
    -
    (
        background[valid]
        -
        global_median
    )
)


# ============================================================
# SAVE DESTRIPED TIFF
# ============================================================

profile.update(
    dtype="float32",
    count=1,
    nodata=0,
    compress="deflate",
    predictor=3,
    tiled=True
)

print(
    "\nSaving destriped GeoTIFF..."
)

with rasterio.open(
    OUTPUT_FILE,
    "w",
    **profile
) as dst:

    dst.write(
        destriped,
        1
    )

print(
    f"Saved:\n{OUTPUT_FILE}"
)


# ============================================================
# PREVIEW HELPER
# ============================================================

def save_preview(
    image,
    valid_mask,
    output_file,
    title
):

    display = image.copy()

    values = display[
        valid_mask
    ]

    low = np.percentile(
        values,
        2
    )

    high = np.percentile(
        values,
        98
    )

    print(
        f"\n{title}"
    )

    print(
        f"Display range: "
        f"{low:.2f} -> {high:.2f} dB"
    )

    display = np.clip(
        display,
        low,
        high
    )

    display = (
        (display - low)
        /
        (high - low + 1e-8)
        * 255
    )

    display[
        ~valid_mask
    ] = 0

    display = np.clip(
        display,
        0,
        255
    ).astype(
        np.uint8
    )

    scale = max(
        1,
        int(width / 1400)
    )

    new_width = max(
        1,
        width // scale
    )

    new_height = max(
        1,
        height // scale
    )

    image_pil = Image.fromarray(
        display
    )

    image_pil = image_pil.resize(
        (
            new_width,
            new_height
        ),
        Image.Resampling.LANCZOS
    )

    image_pil.save(
        output_file
    )

    print(
        f"Saved:\n{output_file}"
    )


# ============================================================
# DESTRIPED PREVIEW
# ============================================================

save_preview(
    destriped,
    valid,
    PREVIEW_FILE,
    "DESTRIPED VV"
)


# ============================================================
# LOCAL ANOMALY PREVIEW
# ============================================================
#
# For visualization only.
#
# Strong negative anomalies become dark.
# Strong positive anomalies become bright.
#

anomaly_display = np.clip(
    anomaly,
    -5.0,
    5.0
)

save_preview(
    anomaly_display,
    valid,
    ANOMALY_PREVIEW_FILE,
    "LOCAL VV ANOMALY"
)


# ============================================================
# SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("DESTRIPING COMPLETE")
print("=" * 70)

print(
    "\nOriginal calibrated VV was NOT modified."
)

print(
    "\nCreated:"
)

print(
    OUTPUT_FILE
)

print(
    PREVIEW_FILE
)

print(
    ANOMALY_PREVIEW_FILE
)