from pathlib import Path
from PIL import Image
from collections import Counter


DATA_DIR = Path("data/raw")

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}


def analyze_class(class_name):
    folder = DATA_DIR / class_name

    dimensions = Counter()
    modes = Counter()
    corrupted = []

    image_files = [
        path for path in folder.iterdir()
        if path.suffix.lower() in IMAGE_EXTENSIONS
    ]

    print("\n" + "=" * 60)
    print(f"CLASS: {class_name}")
    print("=" * 60)
    print(f"Images found: {len(image_files)}")

    for image_path in image_files:
        try:
            with Image.open(image_path) as image:
                dimensions[image.size] += 1
                modes[image.mode] += 1

        except Exception as error:
            corrupted.append((image_path.name, str(error)))

    print("\nImage dimensions:")
    for dimension, count in dimensions.most_common():
        print(f"  {dimension}: {count}")

    print("\nImage modes:")
    for mode, count in modes.most_common():
        print(f"  {mode}: {count}")

    print(f"\nCorrupted images: {len(corrupted)}")

    if corrupted:
        print("\nFirst corrupted files:")
        for filename, error in corrupted[:10]:
            print(f"  {filename}")
            print(f"    {error}")


def main():
    print("=" * 60)
    print("MARITIME OIL SPILL IMAGE ANALYSIS")
    print("=" * 60)

    analyze_class("oil_spill")
    analyze_class("clean_area")


if __name__ == "__main__":
    main()