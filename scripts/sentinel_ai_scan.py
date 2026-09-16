from pathlib import Path

import numpy as np
import torch
import rasterio
from PIL import Image, ImageDraw
from torchvision import models, transforms


VV_FILE = Path(
    r"data\raw\sentinel1\measurement"
    r"\s1d-ew-grd-vv-20260801t150156-20260801t150247-003933-0071f6-001-cog.tiff"
)

MODEL_FILE = Path("models/oil_spill_classifier.pth")
OUTPUT = Path("data/results/sentinel_ai_scan.png")

IMAGE_SIZE = 224
TILE_SIZE = 400
STRIDE = 400


device = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

print("Device:", device)
print("Loading Sentinel-1 image...")


# Load VV image
with rasterio.open(VV_FILE) as src:
    vv = src.read(1).astype(np.float32)


# Valid Sentinel-1 pixels
valid = vv > 0


# Load ocean mask
ocean = np.array(
    Image.open("data/results/safe_ocean_mask.png")
) > 0


# Convert Sentinel-1 values to a visible grayscale image
low = np.percentile(vv[valid], 2)
high = np.percentile(vv[valid], 98)

vv_display = np.clip(vv, low, high)

vv_display = (
    (vv_display - low)
    / (high - low)
    * 255
).astype(np.uint8)


# Load AI model
model = models.resnet18(weights=None)

model.fc = torch.nn.Linear(
    model.fc.in_features,
    2
)

model.load_state_dict(
    torch.load(
        MODEL_FILE,
        map_location=device
    )
)

model.to(device)
model.eval()


# Image preprocessing
transform = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(
        [0.485, 0.456, 0.406],
        [0.229, 0.224, 0.225]
    )
])


results = []

height, width = vv.shape

print("Scanning tiles...")


# Scan image
for y in range(
    0,
    height - TILE_SIZE + 1,
    STRIDE
):

    for x in range(
        0,
        width - TILE_SIZE + 1,
        STRIDE
    ):

        tile_valid = valid[
            y:y + TILE_SIZE,
            x:x + TILE_SIZE
        ]

        tile_ocean = ocean[
            y:y + TILE_SIZE,
            x:x + TILE_SIZE
        ]


        # Ignore tiles containing mostly NoData
        if tile_valid.mean() < 0.5:
            continue


        # Ignore tiles that are not mostly ocean
        if tile_ocean.mean() < 0.98:
            continue


        tile = vv_display[
            y:y + TILE_SIZE,
            x:x + TILE_SIZE
        ]


        # Sentinel-1 is grayscale,
        # so copy it into 3 channels
        tile_rgb = np.stack(
            [tile, tile, tile],
            axis=2
        )


        image = Image.fromarray(tile_rgb)


        input_tensor = transform(
            image
        ).unsqueeze(0).to(device)


        # AI prediction
        with torch.no_grad():

            output = model(
                input_tensor
            )

            probability = torch.softmax(
                output,
                dim=1
            )[0, 1].item()


        results.append({
            "x": x,
            "y": y,
            "probability": probability
        })


print("Tiles scanned:", len(results))


# Create overview image
overview = Image.fromarray(
    np.stack(
        [vv_display] * 3,
        axis=2
    )
).convert("RGB")


draw = ImageDraw.Draw(overview)


# Draw high-probability tiles
for result in results:

    if result["probability"] >= 0.80:

        x = result["x"]
        y = result["y"]

        draw.rectangle(
            [
                x,
                y,
                x + TILE_SIZE,
                y + TILE_SIZE
            ],
            outline=(255, 0, 0),
            width=8
        )

        draw.text(
            (x + 10, y + 10),
            f"{result['probability']:.2f}",
            fill=(255, 0, 0)
        )


# Sort predictions
results.sort(
    key=lambda item: item["probability"],
    reverse=True
)


print("\nTop 10 AI predictions:")


for i, result in enumerate(
    results[:10],
    start=1
):

    print(
        f"{i}. "
        f"Probability={result['probability']:.3f} "
        f"Location=({result['x']}, {result['y']})"
    )


# Save result
OUTPUT.parent.mkdir(
    parents=True,
    exist_ok=True
)

overview.save(OUTPUT)


print("\nAI scan created:")
print(OUTPUT)