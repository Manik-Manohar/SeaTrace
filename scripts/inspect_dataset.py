from pathlib import Path
from zipfile import ZipFile

DATASET_DIR = Path(r"C:\Users\Manik Manohar\Downloads\Oil_Spill_DataSet\data")

ZIP_FILES = [
    DATASET_DIR / "Oil Spill.zip",
    DATASET_DIR / "Clean Area.zip",
]


def inspect_zip(zip_path):
    print("\n" + "=" * 60)
    print(f"FILE: {zip_path.name}")
    print("=" * 60)

    if not zip_path.exists():
        print("ERROR: File not found")
        return

    with ZipFile(zip_path, "r") as zip_file:
        files = [
            name
            for name in zip_file.namelist()
            if name.lower().endswith((".jpg", ".jpeg", ".png", ".tif", ".tiff"))
        ]

        print(f"Image count: {len(files)}")

        print("\nFirst 10 images:")
        for name in files[:10]:
            print(f"  {name}")


def main():
    print("MARITIME OIL SPILL DATASET INSPECTION")

    for zip_file in ZIP_FILES:
        inspect_zip(zip_file)


if __name__ == "__main__":
    main()