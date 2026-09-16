import os
import csv

import numpy as np
import rasterio
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

CSV_FILE = (
    r"data\results\sar_candidates.csv"
)

OUTPUT_DIR = (
    r"data\results\sar_candidate_patches"
)

NUM_CANDIDATES = 15

PATCH_SIZE = 512


# ============================================================
# PREVIEW FUNCTION
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
    ).astype(
        np.uint8
    )


# ============================================================
# MAIN
# ============================================================

print("=" * 70)
print("EXTRACTING FULL-RESOLUTION SAR CANDIDATE PATCHES")
print("=" * 70)


os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


# ============================================================
# READ CSV
# ============================================================

with open(
    CSV_FILE,
    "r",
    encoding="utf-8"
) as f:

    reader = csv.DictReader(f)

    candidates = list(reader)


candidates = candidates[
    :NUM_CANDIDATES
]

print(
    f"\nCandidates selected: "
    f"{len(candidates)}"
)


# ============================================================
# OPEN RASTERS
# ============================================================

with rasterio.open(
    VV_FILE
) as vv_src:

    with rasterio.open(
        VH_FILE
    ) as vh_src:

        print(
            f"\nRaster size: "
            f"{vv_src.width} x {vv_src.height}"
        )

        half = PATCH_SIZE // 2

        for candidate in candidates:

            rank = int(
                candidate["rank"]
            )

            x = int(
                float(
                    candidate["pixel_x"]
                )
            )

            y = int(
                float(
                    candidate["pixel_y"]
                )
            )

            lat = float(
                candidate["latitude"]
            )

            lon = float(
                candidate["longitude"]
            )

            score = float(
                candidate["score"]
            )

            # ------------------------------------------------
            # PATCH WINDOW
            # ------------------------------------------------

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

            width = x2 - x1
            height = y2 - y1

            window = rasterio.windows.Window(
                x1,
                y1,
                width,
                height
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

            # ------------------------------------------------
            # NORMALIZE
            # ------------------------------------------------

            vv_img = normalize(
                vv
            )

            vh_img = normalize(
                vh
            )

            # ------------------------------------------------
            # SAVE DIRECTORY
            # ------------------------------------------------

            candidate_dir = os.path.join(
                OUTPUT_DIR,
                f"candidate_{rank:02d}"
            )

            os.makedirs(
                candidate_dir,
                exist_ok=True
            )

            vv_path = os.path.join(
                candidate_dir,
                "vv.png"
            )

            vh_path = os.path.join(
                candidate_dir,
                "vh.png"
            )

            # ------------------------------------------------
            # ADD CENTER MARKER
            # ------------------------------------------------

            vv_pil = Image.fromarray(
                vv_img
            ).convert(
                "RGB"
            )

            vh_pil = Image.fromarray(
                vh_img
            ).convert(
                "RGB"
            )

            draw_vv = ImageDraw.Draw(
                vv_pil
            )

            draw_vh = ImageDraw.Draw(
                vh_pil
            )

            center_x = x - x1
            center_y = y - y1

            r = 12

            draw_vv.rectangle(
                [
                    center_x - r,
                    center_y - r,
                    center_x + r,
                    center_y + r
                ],
                outline=(255, 0, 0),
                width=3
            )

            draw_vh.rectangle(
                [
                    center_x - r,
                    center_y - r,
                    center_x + r,
                    center_y + r
                ],
                outline=(255, 0, 0),
                width=3
            )

            vv_pil.save(
                vv_path
            )

            vh_pil.save(
                vh_path
            )

            # ------------------------------------------------
            # SAVE METADATA
            # ------------------------------------------------

            metadata_path = os.path.join(
                candidate_dir,
                "metadata.txt"
            )

            with open(
                metadata_path,
                "w",
                encoding="utf-8"
            ) as meta:

                meta.write(
                    f"Rank: {rank}\n"
                )

                meta.write(
                    f"Score: {score:.2f}\n"
                )

                meta.write(
                    f"Latitude: {lat:.6f}\n"
                )

                meta.write(
                    f"Longitude: {lon:.6f}\n"
                )

                meta.write(
                    f"Pixel X: {x}\n"
                )

                meta.write(
                    f"Pixel Y: {y}\n"
                )

                meta.write(
                    f"Patch size: "
                    f"{width} x {height}\n"
                )

            print(
                f"Candidate #{rank}: "
                f"{lat:.6f}, {lon:.6f} "
                f"score={score:.1f}"
            )


print("\n" + "=" * 70)
print("PATCH EXTRACTION COMPLETE")
print("=" * 70)

print(
    f"\nOutput directory:"
)

print(
    OUTPUT_DIR
)