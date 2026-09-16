import os
import csv

import numpy as np
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
import rasterio


# ============================================================
# CONFIG
# ============================================================

VV_FILE = (
    r"data\processed\sentinel1\geocoded"
    r"\sentinel1_vv_sigma0_db_geocoded.tif"
)

CSV_FILE = (
    r"data\results\sar_candidates.csv"
)

MODEL_FILE = (
    r"models\oil_spill_classifier.pth"
)

OUTPUT_FILE = (
    r"data\results\ai_verified_candidates.csv"
)

NUM_CANDIDATES = 15

PATCH_SIZE = 400

IMAGE_SIZE = 224


# ============================================================
# DEVICE
# ============================================================

device = torch.device(
    "cuda" if torch.cuda.is_available()
    else "cpu"
)

print("=" * 70)
print("AI VERIFICATION OF SAR CANDIDATES")
print("=" * 70)

print(
    f"\nDevice: {device}"
)


# ============================================================
# LOAD MODEL
# ============================================================

print("\nLoading ResNet18...")

model = models.resnet18(
    weights=None
)

model.fc = nn.Linear(
    model.fc.in_features,
    2
)

checkpoint = torch.load(
    MODEL_FILE,
    map_location=device
)

# Handle either a plain state_dict or a checkpoint dictionary.

if isinstance(
    checkpoint,
    dict
) and "model_state_dict" in checkpoint:

    model.load_state_dict(
        checkpoint["model_state_dict"]
    )

else:

    model.load_state_dict(
        checkpoint
    )

model = model.to(
    device
)

model.eval()

print(
    f"Loaded model: {MODEL_FILE}"
)


# ============================================================
# CLASS ORDER
# ============================================================
#
# This matches the ImageFolder ordering used by the training
# dataset:
#
# clean_area -> 0
# oil_spill  -> 1
#

class_names = [
    "clean_area",
    "oil_spill"
]


# ============================================================
# PREPROCESSING
# ============================================================
#
# Match the classifier's training preprocessing:
#
# grayscale SAR -> 3 channels
# resize -> 224
# ImageNet normalization
#

transform = transforms.Compose([
    transforms.Resize(
        (IMAGE_SIZE, IMAGE_SIZE)
    ),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[
            0.485,
            0.456,
            0.406
        ],
        std=[
            0.229,
            0.224,
            0.225
        ]
    )
])


# ============================================================
# LOAD CANDIDATES
# ============================================================

with open(
    CSV_FILE,
    "r",
    encoding="utf-8"
) as f:

    candidates = list(
        csv.DictReader(f)
    )


candidates = candidates[
    :NUM_CANDIDATES
]

print(
    f"\nCandidates to verify: "
    f"{len(candidates)}"
)


# ============================================================
# OPEN VV
# ============================================================

results = []

with rasterio.open(
    VV_FILE
) as src:

    print(
        f"Raster: "
        f"{src.width} x {src.height}"
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

        # ----------------------------------------------------
        # Extract ORIGINAL calibrated VV patch
        # ----------------------------------------------------

        x1 = max(
            0,
            x - half
        )

        y1 = max(
            0,
            y - half
        )

        x2 = min(
            src.width,
            x + half
        )

        y2 = min(
            src.height,
            y + half
        )

        window = rasterio.windows.Window(
            x1,
            y1,
            x2 - x1,
            y2 - y1
        )

        patch = src.read(
            1,
            window=window
        ).astype(
            np.float32
        )

        valid = (
            np.isfinite(patch)
            &
            (patch != 0)
        )

        if not np.any(valid):

            print(
                f"#{rank}: no valid pixels"
            )

            continue

        # ----------------------------------------------------
        # Robust normalization for the classifier
        # ----------------------------------------------------
        #
        # The original training images are grayscale intensity
        # images. We convert this dB patch into an 8-bit
        # grayscale representation using its local distribution.
        #

        values = patch[
            valid
        ]

        low = np.percentile(
            values,
            2
        )

        high = np.percentile(
            values,
            98
        )

        patch_display = np.clip(
            patch,
            low,
            high
        )

        patch_display = (
            (patch_display - low)
            /
            (high - low + 1e-8)
            *
            255
        )

        patch_display[
            ~valid
        ] = 0

        patch_display = np.clip(
            patch_display,
            0,
            255
        ).astype(
            np.uint8
        )

        # ----------------------------------------------------
        # Convert to PIL
        # ----------------------------------------------------

        image = Image.fromarray(
            patch_display
        ).convert(
            "RGB"
        )

        tensor = transform(
            image
        ).unsqueeze(
            0
        ).to(
            device
        )

        # ----------------------------------------------------
        # AI prediction
        # ----------------------------------------------------

        with torch.no_grad():

            logits = model(
                tensor
            )

            probabilities = torch.softmax(
                logits,
                dim=1
            )[0]

        clean_probability = float(
            probabilities[0].cpu()
        )

        oil_probability = float(
            probabilities[1].cpu()
        )

        predicted_class = class_names[
            int(
                torch.argmax(
                    probabilities
                ).cpu()
            )
        ]

        # ----------------------------------------------------
        # Save result
        # ----------------------------------------------------

        result = dict(
            candidate
        )

        result[
            "ai_clean_probability"
        ] = clean_probability

        result[
            "ai_oil_probability"
        ] = oil_probability

        result[
            "ai_prediction"
        ] = predicted_class

        results.append(
            result
        )

        print(
            f"\n#{rank}"
        )

        print(
            f"  Location: "
            f"{candidate['latitude']}, "
            f"{candidate['longitude']}"
        )

        print(
            f"  SAR score: "
            f"{float(candidate['score']):.1f}"
        )

        print(
            f"  AI clean: "
            f"{clean_probability * 100:.2f}%"
        )

        print(
            f"  AI oil: "
            f"{oil_probability * 100:.2f}%"
        )

        print(
            f"  Prediction: "
            f"{predicted_class}"
        )


# ============================================================
# SORT BY AI OIL SCORE
# ============================================================

results.sort(
    key=lambda x: float(
        x["ai_oil_probability"]
    ),
    reverse=True
)


# ============================================================
# SAVE
# ============================================================

fieldnames = list(
    results[0].keys()
)

with open(
    OUTPUT_FILE,
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
        results
    )


# ============================================================
# SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("AI VERIFICATION RESULTS")
print("=" * 70)

for rank, result in enumerate(
    results,
    start=1
):

    print(
        f"\nAI Rank #{rank}"
    )

    print(
        f"  Original candidate: "
        f"#{result['rank']}"
    )

    print(
        f"  Location: "
        f"{result['latitude']}, "
        f"{result['longitude']}"
    )

    print(
        f"  Oil probability: "
        f"{float(result['ai_oil_probability']) * 100:.2f}%"
    )

    print(
        f"  Prediction: "
        f"{result['ai_prediction']}"
    )


print(
    f"\nSaved:"
)

print(
    OUTPUT_FILE
)

print("\n" + "=" * 70)
print("AI VERIFICATION COMPLETE")
print("=" * 70)