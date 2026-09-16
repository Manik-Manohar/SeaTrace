from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from PIL import Image
from torchvision import models, transforms


# ---------------------------------------------------------
# PATHS
# ---------------------------------------------------------

MODEL_PATH = Path("models/oil_spill_classifier.pth")

TEST_DIR = Path("data/processed/test/oil_spill")

OUTPUT_DIR = Path("data/results/gradcam")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------

IMAGE_SIZE = 224

CLASS_NAMES = ["clean_area", "oil_spill"]
OIL_CLASS_INDEX = 1


# ---------------------------------------------------------
# DEVICE
# ---------------------------------------------------------

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

print("Device:", device)


# ---------------------------------------------------------
# LOAD MODEL
# ---------------------------------------------------------

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


# ---------------------------------------------------------
# IMAGE TRANSFORM
# ---------------------------------------------------------

transform = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])


# ---------------------------------------------------------
# GRAD-CAM STORAGE
# ---------------------------------------------------------

activations = None
gradients = None


def forward_hook(module, input, output):
    global activations
    activations = output.detach()


def backward_hook(module, grad_input, grad_output):
    global gradients
    gradients = grad_output[0].detach()


# ResNet-18 final convolutional layer
target_layer = model.layer3[-1].conv2

target_layer.register_forward_hook(forward_hook)
target_layer.register_full_backward_hook(backward_hook)


# ---------------------------------------------------------
# SELECT TEST IMAGE
# ---------------------------------------------------------

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
print("Test image:")
print(image_path)


# ---------------------------------------------------------
# LOAD IMAGE
# ---------------------------------------------------------

original_image = Image.open(image_path).convert("RGB")

input_tensor = transform(original_image)
input_tensor = input_tensor.unsqueeze(0).to(device)


# ---------------------------------------------------------
# MODEL PREDICTION
# ---------------------------------------------------------

model.zero_grad()

output = model(input_tensor)

probabilities = torch.softmax(output, dim=1)

predicted_class = torch.argmax(probabilities, dim=1).item()

confidence = probabilities[0][predicted_class].item()

print()
print("Prediction:")
print("Class:", CLASS_NAMES[predicted_class])
print("Confidence:", f"{confidence * 100:.2f}%")


# ---------------------------------------------------------
# GRAD-CAM
# ---------------------------------------------------------

target_score = output[0, predicted_class]

target_score.backward()


# Get gradients and activations
weights = gradients.mean(
    dim=(2, 3),
    keepdim=True
)

cam = (weights * activations).sum(dim=1)

cam = torch.relu(cam)

cam = cam.squeeze().cpu().numpy()


# Normalize CAM
cam_min = cam.min()
cam_max = cam.max()

if cam_max - cam_min > 1e-8:
    cam = (cam - cam_min) / (cam_max - cam_min)
else:
    cam = np.zeros_like(cam)


# ---------------------------------------------------------
# RESIZE HEATMAP
# ---------------------------------------------------------

original_width, original_height = original_image.size

heatmap = Image.fromarray(
    np.uint8(cam * 255)
)

heatmap = heatmap.resize(
    (original_width, original_height),
    Image.Resampling.BILINEAR
)

heatmap_array = np.array(heatmap).astype(np.float32) / 255.0


# ---------------------------------------------------------
# CREATE COLOR HEATMAP
# ---------------------------------------------------------

# Simple blue -> red heatmap
red = heatmap_array * 255

green = (
    np.clip(
        1 - np.abs(heatmap_array - 0.5) * 2,
        0,
        1
    )
    * 255
)

blue = (1 - heatmap_array) * 255

heatmap_rgb = np.stack(
    [red, green, blue],
    axis=2
).astype(np.uint8)

heatmap_image = Image.fromarray(
    heatmap_rgb
)


# ---------------------------------------------------------
# CREATE OVERLAY
# ---------------------------------------------------------

original_array = np.array(original_image).astype(np.float32)

heatmap_array_rgb = np.array(
    heatmap_image
).astype(np.float32)

overlay_array = (
    0.55 * original_array +
    0.45 * heatmap_array_rgb
)

overlay_array = np.clip(
    overlay_array,
    0,
    255
).astype(np.uint8)

overlay_image = Image.fromarray(
    overlay_array
)


# ---------------------------------------------------------
# SAVE RESULTS
# ---------------------------------------------------------

original_output = OUTPUT_DIR / "original.jpg"
heatmap_output = OUTPUT_DIR / "heatmap.png"
overlay_output = OUTPUT_DIR / "overlay.png"

original_image.save(original_output)
heatmap_image.save(heatmap_output)
overlay_image.save(overlay_output)


# ---------------------------------------------------------
# FINISH
# ---------------------------------------------------------

print()
print("Grad-CAM complete!")
print()
print("Files created:")
print(original_output)
print(heatmap_output)
print(overlay_output)