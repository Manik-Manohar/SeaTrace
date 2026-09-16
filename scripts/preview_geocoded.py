import os

import numpy as np
import rasterio
from PIL import Image


INPUT_DIR = r"data\processed\sentinel1\geocoded"
OUTPUT_DIR = r"data\results"

os.makedirs(OUTPUT_DIR, exist_ok=True)


def create_preview(input_path, output_path, title):

    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)

    with rasterio.open(input_path) as src:

        print(f"Input: {input_path}")
        print(f"CRS: {src.crs}")
        print(f"Size: {src.width} x {src.height}")
        print(f"Bounds: {src.bounds}")

        # Downsample to approximately 1400 pixels wide
        scale = max(
            1,
            int(src.width / 1400)
        )

        width = max(
            1,
            src.width // scale
        )

        height = max(
            1,
            src.height // scale
        )

        image = src.read(
            1,
            out_shape=(height, width),
            resampling=rasterio.enums.Resampling.average
        ).astype(np.float32)

    # Valid SAR dB values.
    # Ignore zero/no-data pixels.
    valid = np.isfinite(image) & (image != 0)

    if not np.any(valid):
        raise RuntimeError(
            "No valid pixels found."
        )

    values = image[valid]

    low = np.percentile(values, 2)
    high = np.percentile(values, 98)

    print(f"2nd percentile : {low:.2f} dB")
    print(f"98th percentile: {high:.2f} dB")

    # Clip extreme values for visualization
    image = np.clip(
        image,
        low,
        high
    )

    # Normalize to 0-255
    image = (
        (image - low)
        /
        (high - low + 1e-8)
        * 255
    )

    image[~valid] = 0

    image = np.clip(
        image,
        0,
        255
    ).astype(np.uint8)

    Image.fromarray(
        image
    ).save(output_path)

    print(f"Saved: {output_path}")


if __name__ == "__main__":

    vv_input = os.path.join(
        INPUT_DIR,
        "sentinel1_vv_sigma0_db_geocoded.tif"
    )

    vh_input = os.path.join(
        INPUT_DIR,
        "sentinel1_vh_sigma0_db_geocoded.tif"
    )

    vv_output = os.path.join(
        OUTPUT_DIR,
        "sentinel1_vv_geocoded_preview.png"
    )

    vh_output = os.path.join(
        OUTPUT_DIR,
        "sentinel1_vh_geocoded_preview.png"
    )

    create_preview(
        vv_input,
        vv_output,
        "GEOCODED SENTINEL-1 VV"
    )

    create_preview(
        vh_input,
        vh_output,
        "GEOCODED SENTINEL-1 VH"
    )

    print("\n" + "=" * 70)
    print("PREVIEWS COMPLETE")
    print("=" * 70)