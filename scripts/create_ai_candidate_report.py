import os
import csv

import numpy as np
import rasterio
from PIL import Image, ImageDraw, ImageFont


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

CSV_FILE = (
    r"data\results\ai_verified_candidates.csv"
)

OUTPUT_FILE = (
    r"data\results\ai_candidate_report.png"
)

# Candidate numbers to inspect.
ORIGINAL_CANDIDATES = [3, 15, 8, 5]

PATCH_SIZE = 512


# ============================================================
# NORMALIZATION
# ============================================================

def normalize(image):

    valid = (
        np.isfinite(image)
        &
        (image != 0)
    )

    if not np.any(valid):
        return np.zeros_like(
            image,
            dtype=np.uint8
        )

    values = image[valid]

    low = np.percentile(
        values,
        2
    )

    high = np.percentile(
        values,
        98
    )

    image = np.clip(
        image,
        low,
        high
    )

    image = (
        (image - low)
        /
        (high - low + 1e-8)
        *
        255
    )

    image[~valid] = 0

    return np.clip(
        image,
        0,
        255
    ).astype(np.uint8)


# ============================================================
# READ AI RESULTS
# ============================================================

with open(
    CSV_FILE,
    "r",
    encoding="utf-8"
) as f:

    rows = list(
        csv.DictReader(f)
    )


selected = []

for original_id in ORIGINAL_CANDIDATES:

    for row in rows:

        if int(row["rank"]) == original_id:

            selected.append(row)

            break


# ============================================================
# CREATE REPORT
# ============================================================

print("=" * 70)
print("CREATING AI CANDIDATE VISUAL REPORT")
print("=" * 70)


cell_width = 540
cell_height = 650

report_width = cell_width * 2
report_height = cell_height * 2

report = Image.new(
    "RGB",
    (
        report_width,
        report_height
    ),
    (20, 20, 20)
)

draw = ImageDraw.Draw(
    report
)


# ============================================================
# LOAD RASTERS
# ============================================================

with rasterio.open(VV_FILE) as vv_src:

    with rasterio.open(VH_FILE) as vh_src:

        half = PATCH_SIZE // 2

        for index, row in enumerate(
            selected
        ):

            candidate_id = int(
                row["rank"]
            )

            x = int(
                float(
                    row["pixel_x"]
                )
            )

            y = int(
                float(
                    row["pixel_y"]
                )
            )

            lat = float(
                row["latitude"]
            )

            lon = float(
                row["longitude"]
            )

            sar_score = float(
                row["score"]
            )

            ai_oil = float(
                row["ai_oil_probability"]
            ) * 100

            prediction = row[
                "ai_prediction"
            ]

            # -----------------------------------------------
            # Extract patch
            # -----------------------------------------------

            x1 = max(
                0,
                x - half
            )

            y1 = max(
                0,
                y - half
            )

            x2 = min(
                vv_src.width,
                x + half
            )

            y2 = min(
                vv_src.height,
                y + half
            )

            window = rasterio.windows.Window(
                x1,
                y1,
                x2 - x1,
                y2 - y1
            )

            vv = vv_src.read(
                1,
                window=window
            ).astype(
                np.float32
            )

            vh = vh_src.read(
                1,
                window=window
            ).astype(
                np.float32
            )

            vv_img = Image.fromarray(
                normalize(vv)
            ).convert(
                "RGB"
            )

            vh_img = Image.fromarray(
                normalize(vh)
            ).convert(
                "RGB"
            )

            # -----------------------------------------------
            # Resize
            # -----------------------------------------------

            vv_img = vv_img.resize(
                (250, 250),
                Image.Resampling.LANCZOS
            )

            vh_img = vh_img.resize(
                (250, 250),
                Image.Resampling.LANCZOS
            )

            # -----------------------------------------------
            # Candidate center
            # -----------------------------------------------

            center_x = (
                (x - x1)
                *
                250
                /
                max(x2 - x1, 1)
            )

            center_y = (
                (y - y1)
                *
                250
                /
                max(y2 - y1, 1)
            )

            for image in [
                vv_img,
                vh_img
            ]:

                d = ImageDraw.Draw(
                    image
                )

                r = 8

                d.rectangle(
                    [
                        center_x - r,
                        center_y - r,
                        center_x + r,
                        center_y + r
                    ],
                    outline=(255, 0, 0),
                    width=2
                )

            # -----------------------------------------------
            # Position in report
            # -----------------------------------------------

            col = index % 2
            row_index = index // 2

            base_x = (
                col
                *
                cell_width
            )

            base_y = (
                row_index
                *
                cell_height
            )

            report.paste(
                vv_img,
                (
                    base_x + 10,
                    base_y + 10
                )
            )

            report.paste(
                vh_img,
                (
                    base_x + 270,
                    base_y + 10
                )
            )

            # -----------------------------------------------
            # Labels
            # -----------------------------------------------

            draw.text(
                (
                    base_x + 15,
                    base_y + 270
                ),
                f"Candidate #{candidate_id}",
                fill=(255, 255, 255)
            )

            draw.text(
                (
                    base_x + 15,
                    base_y + 300
                ),
                f"SAR score: {sar_score:.1f}",
                fill=(255, 255, 255)
            )

            draw.text(
                (
                    base_x + 15,
                    base_y + 330
                ),
                f"AI oil score: {ai_oil:.2f}%",
                fill=(255, 255, 255)
            )

            draw.text(
                (
                    base_x + 15,
                    base_y + 360
                ),
                f"AI prediction: {prediction}",
                fill=(255, 255, 255)
            )

            draw.text(
                (
                    base_x + 15,
                    base_y + 390
                ),
                f"Lat: {lat:.6f}",
                fill=(255, 255, 255)
            )

            draw.text(
                (
                    base_x + 15,
                    base_y + 420
                ),
                f"Lon: {lon:.6f}",
                fill=(255, 255, 255)
            )

            draw.text(
                (
                    base_x + 15,
                    base_y + 460
                ),
                "VV",
                fill=(255, 255, 255)
            )

            draw.text(
                (
                    base_x + 275,
                    base_y + 460
                ),
                "VH",
                fill=(255, 255, 255)
            )


# ============================================================
# SAVE
# ============================================================

report.save(
    OUTPUT_FILE
)

print(
    f"\nSaved:"
)

print(
    OUTPUT_FILE
)

print("\n" + "=" * 70)
print("REPORT COMPLETE")
print("=" * 70)