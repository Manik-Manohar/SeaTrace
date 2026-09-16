import os
import numpy as np
import rasterio
from PIL import Image


# ============================================================
# CONFIGURATION
# ============================================================

INPUT_FILE = (
    "data/processed/sentinel1/geocoded/"
    "sentinel1_vv_sigma0_db_geocoded.tif"
)

OUTPUT_DIR = (
    "data/results/sar_overlay"
)

OUTPUT_IMAGE = (
    os.path.join(
        OUTPUT_DIR,
        "sentinel1_vv_web.png"
    )
)

OUTPUT_BOUNDS = (
    os.path.join(
        OUTPUT_DIR,
        "sentinel1_vv_bounds.txt"
    )
)

# Maximum browser image dimension
MAX_SIZE = 2500


# ============================================================
# START
# ============================================================

print()
print("=" * 75)
print("PREPARING SENTINEL-1 SAR WEB OVERLAY")
print("=" * 75)

print()
print("Input:")
print(INPUT_FILE)


if not os.path.exists(INPUT_FILE):

    print()
    print("ERROR: Sentinel-1 TIFF not found.")

    raise SystemExit(1)


os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


# ============================================================
# READ RASTER
# ============================================================

with rasterio.open(
    INPUT_FILE
) as src:

    print()
    print("CRS:", src.crs)

    print(
        "Original size:",
        src.width,
        "x",
        src.height
    )

    print(
        "Bounds:",
        src.bounds
    )

    # --------------------------------------------------------
    # Calculate downsampled dimensions
    # --------------------------------------------------------

    scale = min(
        MAX_SIZE / src.width,
        MAX_SIZE / src.height
    )

    out_width = max(
        1,
        int(src.width * scale)
    )

    out_height = max(
        1,
        int(src.height * scale)
    )


    print()
    print(
        "Web size:",
        out_width,
        "x",
        out_height
    )


    # --------------------------------------------------------
    # Read downsampled raster
    # --------------------------------------------------------

    data = src.read(
        1,
        out_shape=(
            out_height,
            out_width
        ),
        resampling=rasterio.enums.Resampling.average
    )


    bounds = src.bounds


# ============================================================
# HANDLE NODATA
# ============================================================

data = np.asarray(
    data,
    dtype=np.float32
)


finite = np.isfinite(
    data
)


if not finite.any():

    print()
    print(
        "ERROR: Raster contains no valid pixels."
    )

    raise SystemExit(1)


# ============================================================
# CONTRAST STRETCH
# ============================================================

valid = data[
    finite
]


# Robust percentile stretch
low = np.percentile(
    valid,
    2
)

high = np.percentile(
    valid,
    98
)


print()
print(
    "2nd percentile:",
    round(float(low), 3)
)

print(
    "98th percentile:",
    round(float(high), 3)
)


if high <= low:

    high = low + 1.0


normalized = (
    (data - low)
    /
    (high - low)
)


normalized = np.clip(
    normalized,
    0,
    1
)


# ============================================================
# CREATE GRAYSCALE IMAGE
# ============================================================

image_array = (
    normalized * 255
).astype(
    np.uint8
)


# Make invalid pixels transparent
alpha = np.where(
    finite,
    215,
    0
).astype(
    np.uint8
)


rgba = np.dstack(
    [
        image_array,
        image_array,
        image_array,
        alpha
    ]
)


image = Image.fromarray(
    rgba,
    mode="RGBA"
)


# ============================================================
# SAVE IMAGE
# ============================================================

image.save(
    OUTPUT_IMAGE,
    optimize=True
)


# ============================================================
# SAVE BOUNDS
# ============================================================

with open(
    OUTPUT_BOUNDS,
    "w",
    encoding="utf-8"
) as f:

    f.write(
        f"west={bounds.left}\n"
    )

    f.write(
        f"south={bounds.bottom}\n"
    )

    f.write(
        f"east={bounds.right}\n"
    )

    f.write(
        f"north={bounds.top}\n"
    )


# ============================================================
# FINISH
# ============================================================

print()
print("=" * 75)
print("SAR WEB OVERLAY CREATED")
print("=" * 75)

print()
print("Image:")
print(OUTPUT_IMAGE)

print()
print("Bounds:")
print(OUTPUT_BOUNDS)

print()
print(
    "Final image size:",
    image.width,
    "x",
    image.height
)

print()
print("=" * 75)
print("DONE")
print("=" * 75)