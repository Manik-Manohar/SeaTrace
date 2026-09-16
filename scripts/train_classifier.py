from pathlib import Path

import torch
from torch import nn, optim
from torch.utils.data import DataLoader
from torchvision import datasets, models, transforms


# --------------------------------------------------
# SETTINGS
# --------------------------------------------------

DATA_DIR = Path("data/processed")

IMAGE_SIZE = 224
BATCH_SIZE = 32
EPOCHS = 10
LEARNING_RATE = 0.0001

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

MODEL_DIR = Path("models")
MODEL_DIR.mkdir(parents=True, exist_ok=True)

BEST_MODEL_PATH = MODEL_DIR / "oil_spill_classifier.pth"


# --------------------------------------------------
# IMAGE TRANSFORMS
# --------------------------------------------------

train_transforms = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.RandomHorizontalFlip(),
    transforms.RandomVerticalFlip(),
    transforms.RandomRotation(10),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225],
    ),
])

val_test_transforms = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225],
    ),
])


# --------------------------------------------------
# LOAD DATASET
# --------------------------------------------------

train_dataset = datasets.ImageFolder(
    DATA_DIR / "train",
    transform=train_transforms,
)

val_dataset = datasets.ImageFolder(
    DATA_DIR / "val",
    transform=val_test_transforms,
)

test_dataset = datasets.ImageFolder(
    DATA_DIR / "test",
    transform=val_test_transforms,
)


train_loader = DataLoader(
    train_dataset,
    batch_size=BATCH_SIZE,
    shuffle=True,
    num_workers=0,
)

val_loader = DataLoader(
    val_dataset,
    batch_size=BATCH_SIZE,
    shuffle=False,
    num_workers=0,
)

test_loader = DataLoader(
    test_dataset,
    batch_size=BATCH_SIZE,
    shuffle=False,
    num_workers=0,
)


# --------------------------------------------------
# DISPLAY DATASET INFORMATION
# --------------------------------------------------

print("=" * 60)
print("MARITIME OIL SPILL CLASSIFIER")
print("=" * 60)

print(f"Device: {DEVICE}")
print(f"Training images: {len(train_dataset)}")
print(f"Validation images: {len(val_dataset)}")
print(f"Test images: {len(test_dataset)}")

print(f"Classes: {train_dataset.classes}")
print(f"Class mapping: {train_dataset.class_to_idx}")


# --------------------------------------------------
# CREATE MODEL
# --------------------------------------------------

print("\nLoading pretrained ResNet-18...")

weights = models.ResNet18_Weights.DEFAULT
model = models.resnet18(weights=weights)

# Replace the final classification layer
number_of_features = model.fc.in_features

model.fc = nn.Linear(
    number_of_features,
    2,
)

model = model.to(DEVICE)


# --------------------------------------------------
# LOSS AND OPTIMIZER
# --------------------------------------------------

criterion = nn.CrossEntropyLoss()

optimizer = optim.Adam(
    model.parameters(),
    lr=LEARNING_RATE,
)


# --------------------------------------------------
# TRAINING
# --------------------------------------------------

best_val_accuracy = 0.0

print("\nStarting training...")
print("-" * 60)

for epoch in range(EPOCHS):

    # ------------------------------
    # TRAIN
    # ------------------------------

    model.train()

    running_loss = 0.0
    correct = 0
    total = 0

    for images, labels in train_loader:

        images = images.to(DEVICE)
        labels = labels.to(DEVICE)

        optimizer.zero_grad()

        outputs = model(images)

        loss = criterion(outputs, labels)

        loss.backward()

        optimizer.step()

        running_loss += loss.item()

        _, predicted = torch.max(outputs, 1)

        total += labels.size(0)
        correct += (predicted == labels).sum().item()

    train_loss = running_loss / len(train_loader)
    train_accuracy = 100 * correct / total

    # ------------------------------
    # VALIDATION
    # ------------------------------

    model.eval()

    val_correct = 0
    val_total = 0
    val_loss_total = 0.0

    with torch.no_grad():

        for images, labels in val_loader:

            images = images.to(DEVICE)
            labels = labels.to(DEVICE)

            outputs = model(images)

            loss = criterion(outputs, labels)

            val_loss_total += loss.item()

            _, predicted = torch.max(outputs, 1)

            val_total += labels.size(0)
            val_correct += (predicted == labels).sum().item()

    val_loss = val_loss_total / len(val_loader)
    val_accuracy = 100 * val_correct / val_total

    print(
        f"Epoch [{epoch + 1}/{EPOCHS}] "
        f"| Train Loss: {train_loss:.4f} "
        f"| Train Acc: {train_accuracy:.2f}% "
        f"| Val Loss: {val_loss:.4f} "
        f"| Val Acc: {val_accuracy:.2f}%"
    )

    # Save best model
    if val_accuracy > best_val_accuracy:

        best_val_accuracy = val_accuracy

        torch.save(
            model.state_dict(),
            BEST_MODEL_PATH,
        )

        print(
            f"  ✓ Best model saved "
            f"(validation accuracy: {val_accuracy:.2f}%)"
        )


# --------------------------------------------------
# FINAL TEST
# --------------------------------------------------

print("\n" + "=" * 60)
print("FINAL TEST")
print("=" * 60)

# Load best model
model.load_state_dict(
    torch.load(
        BEST_MODEL_PATH,
        map_location=DEVICE,
    )
)

model.eval()

test_correct = 0
test_total = 0

with torch.no_grad():

    for images, labels in test_loader:

        images = images.to(DEVICE)
        labels = labels.to(DEVICE)

        outputs = model(images)

        _, predicted = torch.max(outputs, 1)

        test_total += labels.size(0)
        test_correct += (predicted == labels).sum().item()

test_accuracy = 100 * test_correct / test_total

print(f"Test Accuracy: {test_accuracy:.2f}%")
print(f"Best Validation Accuracy: {best_val_accuracy:.2f}%")

print("\nModel saved to:")
print(BEST_MODEL_PATH)

print("\nTraining complete.")