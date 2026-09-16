from pathlib import Path
import random
import shutil


SOURCE_DIR = Path("data/raw")
OUTPUT_DIR = Path("data/processed")

CLASSES = ["oil_spill", "clean_area"]

TRAIN_RATIO = 0.70
VAL_RATIO = 0.15
TEST_RATIO = 0.15

RANDOM_SEED = 42


def split_class(class_name):
    source_folder = SOURCE_DIR / class_name

    images = [
        path
        for path in source_folder.iterdir()
        if path.suffix.lower() in {".jpg", ".jpeg", ".png"}
    ]

    random.shuffle(images)

    total = len(images)

    train_end = int(total * TRAIN_RATIO)
    val_end = train_end + int(total * VAL_RATIO)

    train_images = images[:train_end]
    val_images = images[train_end:val_end]
    test_images = images[val_end:]

    splits = {
        "train": train_images,
        "val": val_images,
        "test": test_images,
    }

    print(f"\n{class_name}")
    print(f"Total: {total}")

    for split_name, split_images in splits.items():

        destination = OUTPUT_DIR / split_name / class_name
        destination.mkdir(parents=True, exist_ok=True)

        for image_path in split_images:
            shutil.copy2(
                image_path,
                destination / image_path.name
            )

        print(f"{split_name}: {len(split_images)}")


def main():

    random.seed(RANDOM_SEED)

    print("=" * 60)
    print("MARITIME OIL SPILL DATASET SPLITTING")
    print("=" * 60)

    for class_name in CLASSES:
        split_class(class_name)

    print("\nDataset split complete.")


if __name__ == "__main__":
    main()