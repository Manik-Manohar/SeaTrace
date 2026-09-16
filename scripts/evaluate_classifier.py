from pathlib import Path

import torch
from torch import nn
from torch.utils.data import DataLoader
from torchvision import datasets, models, transforms

from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    accuracy_score,
)


# --------------------------------------------------
# SETTINGS
# --------------------------------------------------

DATA_DIR = Path("data/processed")
MODEL_PATH = Path("models/oil_spill_classifier.pth")

IMAGE_SIZE = 224
BATCH_SIZE = 32

DEVICE = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)


# --------------------------------------------------
# IMAGE TRANSFORM
# --------------------------------------------------

transform = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225],
    ),
])


# --------------------------------------------------
# LOAD TEST DATA
# --------------------------------------------------

test_dataset = datasets.ImageFolder(
    DATA_DIR / "test",
    transform=transform,
)

test_loader = DataLoader(
    test_dataset,
    batch_size=BATCH_SIZE,
    shuffle=False,
    num_workers=0,
)


# --------------------------------------------------
# LOAD MODEL
# --------------------------------------------------

print("=" * 60)
print("OIL SPILL CLASSIFIER EVALUATION")
print("=" * 60)

print(f"Device: {DEVICE}")
print(f"Test images: {len(test_dataset)}")
print(f"Classes: {test_dataset.classes}")
print(f"Class mapping: {test_dataset.class_to_idx}")

model = models.resnet18(weights=None)

number_of_features = model.fc.in_features

model.fc = nn.Linear(
    number_of_features,
    2,
)

model.load_state_dict(
    torch.load(
        MODEL_PATH,
        map_location=DEVICE,
    )
)

model = model.to(DEVICE)
model.eval()


# --------------------------------------------------
# RUN PREDICTIONS
# --------------------------------------------------

all_labels = []
all_predictions = []

with torch.no_grad():

    for images, labels in test_loader:

        images = images.to(DEVICE)

        outputs = model(images)

        _, predictions = torch.max(outputs, 1)

        all_labels.extend(labels.numpy())
        all_predictions.extend(predictions.cpu().numpy())


# --------------------------------------------------
# ACCURACY
# --------------------------------------------------

accuracy = accuracy_score(
    all_labels,
    all_predictions,
)

print("\n" + "=" * 60)
print("ACCURACY")
print("=" * 60)

print(f"Test Accuracy: {accuracy * 100:.2f}%")


# --------------------------------------------------
# CONFUSION MATRIX
# --------------------------------------------------

matrix = confusion_matrix(
    all_labels,
    all_predictions,
)

print("\n" + "=" * 60)
print("CONFUSION MATRIX")
print("=" * 60)

print("Rows = Actual")
print("Columns = Predicted")

print("\n                 Predicted")
print("               Clean  Oil")
print(
    f"Actual Clean   {matrix[0][0]:5d}  {matrix[0][1]:5d}"
)
print(
    f"Actual Oil     {matrix[1][0]:5d}  {matrix[1][1]:5d}"
)


# --------------------------------------------------
# CLASSIFICATION REPORT
# --------------------------------------------------

print("\n" + "=" * 60)
print("CLASSIFICATION REPORT")
print("=" * 60)

report = classification_report(
    all_labels,
    all_predictions,
    target_names=test_dataset.classes,
    digits=4,
)

print(report)


# --------------------------------------------------
# OIL SPILL METRICS
# --------------------------------------------------

oil_spill_class = test_dataset.class_to_idx["oil_spill"]

oil_true_positive = matrix[
    oil_spill_class,
    oil_spill_class
]

oil_false_negative = matrix[
    oil_spill_class,
    1 - oil_spill_class
]

oil_false_positive = matrix[
    1 - oil_spill_class,
    oil_spill_class
]

oil_precision = (
    oil_true_positive /
    (oil_true_positive + oil_false_positive)
    if (oil_true_positive + oil_false_positive) > 0
    else 0
)

oil_recall = (
    oil_true_positive /
    (oil_true_positive + oil_false_negative)
    if (oil_true_positive + oil_false_negative) > 0
    else 0
)

oil_f1 = (
    2 * oil_precision * oil_recall /
    (oil_precision + oil_recall)
    if (oil_precision + oil_recall) > 0
    else 0
)

print("\n" + "=" * 60)
print("OIL SPILL PERFORMANCE")
print("=" * 60)

print(f"Precision: {oil_precision * 100:.2f}%")
print(f"Recall:    {oil_recall * 100:.2f}%")
print(f"F1 Score:  {oil_f1 * 100:.2f}%")

print("\nEvaluation complete.")