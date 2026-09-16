import os
import glob
import xml.etree.ElementTree as ET

import numpy as np
import rasterio
from rasterio.windows import Window
from PIL import Image


# ============================================================
# CONFIG
# ============================================================

SAFE_DIR = r"data\raw\sentinel1"
OUTPUT_DIR = r"data\processed\sentinel1"

CHUNK_ROWS = 512


# ============================================================
# HELPERS
# ============================================================

def find_files():
    measurement_dir = os.path.join(SAFE_DIR, "measurement")
    annotation_dir = os.path.join(SAFE_DIR, "annotation")

    vv_files = glob.glob(
        os.path.join(measurement_dir, "*-vv-*.tif*")
    )

    vh_files = glob.glob(
        os.path.join(measurement_dir, "*-vh-*.tif*")
    )

    vv_cal = glob.glob(
        os.path.join(annotation_dir, "**", "*calibration*vv*.xml"),
        recursive=True
    )

    vh_cal = glob.glob(
        os.path.join(annotation_dir, "**", "*calibration*vh*.xml"),
        recursive=True
    )

    if not vv_files:
        raise FileNotFoundError("VV measurement TIFF not found")

    if not vh_files:
        raise FileNotFoundError("VH measurement TIFF not found")

    if not vv_cal:
        raise FileNotFoundError("VV calibration XML not found")

    if not vh_cal:
        raise FileNotFoundError("VH calibration XML not found")

    return vv_files[0], vh_files[0], vv_cal[0], vh_cal[0]


def parse_calibration_xml(xml_path):
    print(f"\nReading calibration XML:")
    print(xml_path)

    tree = ET.parse(xml_path)
    root = tree.getroot()

    vectors = []

    for vector in root.iter():
        if vector.tag.endswith("calibrationVector"):

            line_node = None
            pixel_node = None
            sigma_node = None

            for child in vector:
                tag = child.tag.split("}")[-1]

                if tag == "line":
                    line_node = child

                elif tag == "pixel":
                    pixel_node = child

                elif tag == "sigmaNought":
                    sigma_node = child

            if (
                line_node is None
                or pixel_node is None
                or sigma_node is None
            ):
                continue

            line = int(line_node.text.strip())

            pixels = np.fromstring(
                pixel_node.text.strip(),
                sep=" ",
                dtype=np.float64
            )

            sigma = np.fromstring(
                sigma_node.text.strip(),
                sep=" ",
                dtype=np.float64
            )

            if len(pixels) != len(sigma):
                continue

            vectors.append(
                {
                    "line": line,
                    "pixels": pixels,
                    "sigma": sigma
                }
            )

    if not vectors:
        raise RuntimeError(
            f"No usable calibration vectors found in {xml_path}"
        )

    vectors.sort(key=lambda x: x["line"])

    lines = np.array(
        [v["line"] for v in vectors],
        dtype=np.float64
    )

    pixels = vectors[0]["pixels"]

    sigma_lut = np.array(
        [v["sigma"] for v in vectors],
        dtype=np.float64
    )

    print(f"Calibration vectors: {len(lines)}")
    print(f"Calibration pixels per vector: {len(pixels)}")
    print(f"Line range: {lines[0]} -> {lines[-1]}")
    print(f"Pixel range: {pixels[0]} -> {pixels[-1]}")

    return lines, pixels, sigma_lut


def interpolate_lut(
    target_lines,
    image_width,
    cal_lines,
    cal_pixels,
    cal_sigma
):
    """
    Bilinear interpolation of sigma0 calibration LUT.

    First interpolate along range/pixel.
    Then interpolate along azimuth/line.
    """

    x = np.arange(image_width, dtype=np.float64)

    # --------------------------------------------------------
    # Interpolate every calibration vector across image width
    # --------------------------------------------------------

    lut_x = np.empty(
        (len(cal_lines), image_width),
        dtype=np.float64
    )

    for i in range(len(cal_lines)):
        lut_x[i] = np.interp(
            x,
            cal_pixels,
            cal_sigma[i]
        )

    # --------------------------------------------------------
    # Interpolate calibration values along lines
    # --------------------------------------------------------

    result = np.empty(
        (len(target_lines), image_width),
        dtype=np.float64
    )

    for i, line in enumerate(target_lines):

        if line <= cal_lines[0]:
            result[i] = lut_x[0]

        elif line >= cal_lines[-1]:
            result[i] = lut_x[-1]

        else:
            upper = np.searchsorted(
                cal_lines,
                line
            )

            lower = upper - 1

            l0 = cal_lines[lower]
            l1 = cal_lines[upper]

            weight = (line - l0) / (l1 - l0)

            result[i] = (
                lut_x[lower]
                + weight *
                (lut_x[upper] - lut_x[lower])
            )

    return result


# ============================================================
# PROCESS ONE POLARIZATION
# ============================================================

def process_band(
    input_path,
    calibration_path,
    polarization
):

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    print("\n" + "=" * 70)
    print(f"PROCESSING {polarization.upper()}")
    print("=" * 70)

    cal_lines, cal_pixels, cal_sigma = parse_calibration_xml(
        calibration_path
    )

    output_linear = os.path.join(
        OUTPUT_DIR,
        f"sentinel1_{polarization}_sigma0.tif"
    )

    output_db = os.path.join(
        OUTPUT_DIR,
        f"sentinel1_{polarization}_sigma0_db.tif"
    )

    with rasterio.open(input_path) as src:

        width = src.width
        height = src.height

        print(f"\nInput:")
        print(input_path)

        print(f"Size: {width} x {height}")
        print(f"Input dtype: {src.dtypes[0]}")

        profile = src.profile.copy()

        profile.update(
            dtype="float32",
            count=1,
            compress="deflate",
            predictor=3,
            nodata=0
        )

        # ----------------------------------------------------
        # LINEAR SIGMA0
        # ----------------------------------------------------

        with rasterio.open(
            output_linear,
            "w",
            **profile
        ) as dst_linear:

            for row_start in range(
                0,
                height,
                CHUNK_ROWS
            ):

                rows = min(
                    CHUNK_ROWS,
                    height - row_start
                )

                window = Window(
                    0,
                    row_start,
                    width,
                    rows
                )

                raw = src.read(
                    1,
                    window=window
                ).astype(
                    np.float64
                )

                target_lines = (
                    np.arange(rows)
                    + row_start
                )

                sigma_lut = interpolate_lut(
                    target_lines,
                    width,
                    cal_lines,
                    cal_pixels,
                    cal_sigma
                )

                # Sentinel-1 GRD calibration:
                #
                # sigma0 = (DN / sigmaNought_LUT)^2
                #
                # Avoid division by zero.

                sigma_lut[
                    sigma_lut <= 0
                ] = np.nan

                sigma0 = (
                    raw / sigma_lut
                ) ** 2

                sigma0[
                    raw <= 0
                ] = 0

                sigma0 = np.nan_to_num(
                    sigma0,
                    nan=0.0,
                    posinf=0.0,
                    neginf=0.0
                )

                dst_linear.write(
                    sigma0.astype(np.float32),
                    1,
                    window=window
                )

                print(
                    f"\rLinear σ⁰: "
                    f"{row_start + rows}/{height} rows",
                    end=""
                )

    print("\n")
    print(
        f"Saved linear σ⁰:\n{output_linear}"
    )

    # --------------------------------------------------------
    # CREATE dB VERSION
    # --------------------------------------------------------

    with rasterio.open(
        output_linear
    ) as src:

        profile = src.profile.copy()

        with rasterio.open(
            output_db,
            "w",
            **profile
        ) as dst:

            for row_start in range(
                0,
                src.height,
                CHUNK_ROWS
            ):

                rows = min(
                    CHUNK_ROWS,
                    src.height - row_start
                )

                window = Window(
                    0,
                    row_start,
                    src.width,
                    rows
                )

                sigma0 = src.read(
                    1,
                    window=window
                ).astype(
                    np.float32
                )

                db = np.zeros_like(
                    sigma0,
                    dtype=np.float32
                )

                valid = sigma0 > 0

                db[valid] = (
                    10.0 *
                    np.log10(
                        sigma0[valid]
                    )
                )

                dst.write(
                    db,
                    1,
                    window=window
                )

    print(
        f"Saved σ⁰ dB:\n{output_db}"
    )

    # --------------------------------------------------------
    # CREATE PREVIEW PNG
    # --------------------------------------------------------

    preview_path = os.path.join(
        OUTPUT_DIR,
        f"sentinel1_{polarization}_sigma0_preview.png"
    )

    with rasterio.open(
        output_db
    ) as src:

        # Downsample for preview
        scale = max(
            1,
            int(
                max(
                    src.width,
                    src.height
                ) / 1200
            )
        )

        preview = src.read(
            1,
            out_shape=(
                max(1, src.height // scale),
                max(1, src.width // scale)
            ),
            resampling=rasterio.enums.Resampling.average
        )

    valid = preview[
        np.isfinite(preview) &
        (preview < 0)
    ]

    if valid.size > 0:

        low = np.percentile(
            valid,
            2
        )

        high = np.percentile(
            valid,
            98
        )

        preview = np.clip(
            preview,
            low,
            high
        )

        preview = (
            (preview - low)
            /
            (high - low + 1e-8)
            * 255
        )

    else:
        preview = np.zeros_like(
            preview
        )

    preview = np.clip(
        preview,
        0,
        255
    ).astype(
        np.uint8
    )

    Image.fromarray(
        preview
    ).save(
        preview_path
    )

    print(
        f"Saved preview:\n{preview_path}"
    )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print("=" * 70)
    print("SENTINEL-1 RADIOMETRIC CALIBRATION")
    print("=" * 70)

    vv_file, vh_file, vv_cal, vh_cal = find_files()

    print("\nDetected files:")
    print(f"VV measurement: {vv_file}")
    print(f"VH measurement: {vh_file}")
    print(f"VV calibration: {vv_cal}")
    print(f"VH calibration: {vh_cal}")

    process_band(
        vv_file,
        vv_cal,
        "vv"
    )

    process_band(
        vh_file,
        vh_cal,
        "vh"
    )

    print("\n" + "=" * 70)
    print("CALIBRATION COMPLETE")
    print("=" * 70)