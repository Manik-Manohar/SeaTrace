from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from PIL import Image, ImageDraw
from scipy import ndimage
from torchvision import models, transforms


# =========================================================
# PATHS
# =========================================================

MODEL_PATH = Path("models/oil_spill_classifier.pth")

TEST_DIR = Path("data/processed/test/oil_spill")

OUTPUT_DIR = Path("data/results/spill_region")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# =========================================================
# SETTINGS
# =========================================================

IMAGE_SIZE = 224

CLASS_NAMES = ["clean_area", "oil_spill"]
OIL_CLASS_INDEX = 1

# Grad-CAM threshold
# Higher = smaller/more selective regions
CAM_THRESHOLD = 0.45

# Ignore very tiny regions
MIN_REGION_PIXELS = 100


# =========================================================
# DEVICE
# =========================================================

device = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

print("Device:", device)


# =========================================================
# LOAD MODEL
# =========================================================

print("Loading trained model...")

model = models.resnet18(weights=None)

model.fc = nn.Linear(
    model.fc.in_features,
    2
)

checkpoint = torch.load(
    MODEL_PATH,
    map_location=device
)

model.load_state_dict(checkpoint)

model = model.to(device)
model.eval()

print("Model loaded successfully.")


# =========================================================
# IMAGE TRANSFORM
# =========================================================

transform = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])


# =========================================================
# GRAD-CAM
# =========================================================

activations = None
gradients = None


def forward_hook(module, input, output):
    global activations
    activations = output.detach()


def backward_hook(module, grad_input, grad_output):
    global gradients
    gradients = grad_output[0].detach()


# We found this layer gives better localization
target_layer = model.layer3[-1].conv2

target_layer.register_forward_hook(forward_hook)
target_layer.register_full_backward_hook(backward_hook)


# =========================================================
# SELECT TEST IMAGE
# =========================================================

images = sorted(
    list(TEST_DIR.glob("*.jpg")) +
    list(TEST_DIR.glob("*.jpeg")) +
    list(TEST_DIR.glob("*.png"))
)

if not images:
    raise FileNotFoundError(
        f"No test images found in {TEST_DIR}"
    )

image_path = images[0]

print()
print("Input image:")
print(image_path)


# =========================================================
# LOAD IMAGE
# =========================================================

original_image = Image.open(
    image_path
).convert("RGB")

original_width, original_height = original_image.size

input_tensor = transform(original_image)
input_tensor = input_tensor.unsqueeze(0).to(device)


# =========================================================
# PREDICTION
# =========================================================

model.zero_grad()

output = model(input_tensor)

probabilities = torch.softmax(
    output,
    dim=1
)

oil_probability = probabilities[
    0,
    OIL_CLASS_INDEX
].item()

predicted_class = torch.argmax(
    probabilities,
    dim=1
).item()

print()
print("MODEL RESULT")
print("-------------------------")
print(
    "Predicted class:",
    CLASS_NAMES[predicted_class]
)

print(
    "Oil spill probability:",
    f"{oil_probability * 100:.2f}%"
)


# =========================================================
# GRAD-CAM FOR OIL-SPILL CLASS
# =========================================================

oil_score = output[
    0,
    OIL_CLASS_INDEX
]

oil_score.backward()


# Calculate Grad-CAM weights
weights = gradients.mean(
    dim=(2, 3),
    keepdim=True
)

cam = (
    weights * activations
).sum(dim=1)

cam = torch.relu(cam)

cam = cam.squeeze().cpu().numpy()


# =========================================================
# NORMALIZE CAM
# =========================================================

cam_min = cam.min()
cam_max = cam.max()

if cam_max - cam_min > 1e-8:
    cam = (
        cam - cam_min
    ) / (
        cam_max - cam_min
    )
else:
    cam = np.zeros_like(cam)


# =========================================================
# RESIZE CAM TO ORIGINAL IMAGE
# =========================================================

heatmap = Image.fromarray(
    np.uint8(cam * 255)
)

heatmap = heatmap.resize(
    (original_width, original_height),
    Image.Resampling.BILINEAR
)

cam_resized = (
    np.array(heatmap).astype(np.float32)
    / 255.0
)


# =========================================================
# CREATE BINARY CANDIDATE MASK
# =========================================================

mask = cam_resized >= CAM_THRESHOLD


# =========================================================
# CLEAN THE MASK
# =========================================================

# Remove isolated noise
mask = ndimage.binary_opening(
    mask,
    structure=np.ones((3, 3))
)

# Fill small holes
mask = ndimage.binary_closing(
    mask,
    structure=np.ones((5, 5))
)

mask = ndimage.binary_fill_holes(mask)


# =========================================================
# FIND CONNECTED REGIONS
# =========================================================

labeled_mask, number_of_regions = ndimage.label(
    mask
)

objects = ndimage.find_objects(
    labeled_mask
)


regions = []


for region_id, region_slice in enumerate(
    objects,
    start=1
):

    if region_slice is None:
        continue

    region_pixels = (
        labeled_mask[region_slice] == region_id
    )

    pixel_count = int(
        region_pixels.sum()
    )

    # Ignore tiny regions
    if pixel_count < MIN_REGION_PIXELS:
        continue

    y_slice, x_slice = region_slice

    x_min = x_slice.start
    x_max = x_slice.stop - 1

    y_min = y_slice.start
    y_max = y_slice.stop - 1

    # Coordinates of pixels belonging to region
    ys, xs = np.where(
        labeled_mask == region_id
    )

    centroid_x = float(xs.mean())
    centroid_y = float(ys.mean())

    regions.append({
        "id": region_id,
        "pixel_area": pixel_count,
        "centroid_x": centroid_x,
        "centroid_y": centroid_y,
        "x_min": x_min,
        "y_min": y_min,
        "x_max": x_max,
        "y_max": y_max,
    })


# Sort largest region first
regions.sort(
    key=lambda r: r["pixel_area"],
    reverse=True
)


# =========================================================
# CREATE MASK IMAGE
# =========================================================

mask_image = (
    mask.astype(np.uint8) * 255
)

mask_image = Image.fromarray(
    mask_image
)

mask_output = (
    OUTPUT_DIR /
    "candidate_mask.png"
)

mask_image.save(mask_output)


# =========================================================
# DRAW DETECTED REGIONS
# =========================================================

result_image = original_image.copy()

draw = ImageDraw.Draw(
    result_image
)


for region in regions:

    x_min = region["x_min"]
    y_min = region["y_min"]
    x_max = region["x_max"]
    y_max = region["y_max"]

    # Draw bounding box
    draw.rectangle(
        [
            x_min,
            y_min,
            x_max,
            y_max
        ],
        outline=(255, 0, 0),
        width=3
    )

    # Draw centroid
    cx = int(region["centroid_x"])
    cy = int(region["centroid_y"])

    radius = 5

    draw.ellipse(
        [
            cx - radius,
            cy - radius,
            cx + radius,
            cy + radius
        ],
        fill=(255, 0, 0)
    )


result_output = (
    OUTPUT_DIR /
    "candidate_regions.jpg"
)

result_image.save(
    result_output
)


# =========================================================
# CREATE RED MASK OVERLAY
# =========================================================

overlay = original_image.convert(
    "RGBA"
)

red_layer = Image.new(
    "RGBA",
    original_image.size,
    (255, 0, 0, 0)
)

red_pixels = np.zeros(
    (
        original_height,
        original_width,
        4
    ),
    dtype=np.uint8
)

red_pixels[:, :, 0] = 255
red_pixels[:, :, 3] = (
    mask.astype(np.uint8) * 100
)

red_layer = Image.fromarray(
    red_pixels,
    "RGBA"
)

overlay = Image.alpha_composite(
    overlay,
    red_layer
)

overlay_output = (
    OUTPUT_DIR /
    "spill_region_overlay.png"
)

overlay.save(
    overlay_output
)


# =========================================================
# PRINT RESULTS
# =========================================================

print()
print("CANDIDATE SPILL REGIONS")
print("========================")

if not regions:

    print(
        "No significant candidate region found."
    )

else:

    for region in regions:

        print()
        print(
            f"Region {region['id']}"
        )

        print(
            "Pixel area:",
            region["pixel_area"]
        )

        print(
            "Centroid:",
            f"({region['centroid_x']:.1f}, "
            f"{region['centroid_y']:.1f})"
        )

        print(
            "Bounding box:",
            f"x={region['x_min']}, "
            f"y={region['y_min']}, "
            f"x2={region['x_max']}, "
            f"y2={region['y_max']}"
        )


# =========================================================
# SAVE SUMMARY
# =========================================================

summary_file = (
    OUTPUT_DIR /
    "spill_region_summary.txt"
)

with open(
    summary_file,
    "w",
    encoding="utf-8"
) as f:

    f.write(
        "MARITIME OIL SPILL REGION ANALYSIS\n"
    )

    f.write(
        "==================================\n\n"
    )

    f.write(
        f"Input image: {image_path}\n"
    )

    f.write(
        f"Predicted class: "
        f"{CLASS_NAMES[predicted_class]}\n"
    )

    f.write(
        f"Oil probability: "
        f"{oil_probability * 100:.2f}%\n"
    )

    f.write(
        f"CAM threshold: "
        f"{CAM_THRESHOLD}\n\n"
    )

    for region in regions:

        f.write(
            f"Region {region['id']}\n"
        )

        f.write(
            f"Pixel area: "
            f"{region['pixel_area']}\n"
        )

        f.write(
            f"Centroid: "
            f"({region['centroid_x']:.1f}, "
            f"{region['centroid_y']:.1f})\n"
        )

        f.write(
            f"Bounding box: "
            f"x={region['x_min']}, "
            f"y={region['y_min']}, "
            f"x2={region['x_max']}, "
            f"y2={region['y_max']}\n\n"
        )


print()
print("FILES CREATED")
print("=============")
print(mask_output)
print(result_output)
print(overlay_output)
print(summary_file)

print()
print("Spill-region extraction complete!")