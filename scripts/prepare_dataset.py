from pathlib import Path
from zipfile import ZipFile
import shutil


# Original dataset location
SOURCE_DIR = Path(
    r"C:\Users\Manik Manohar\Downloads\Oil_Spill_DataSet\data"
)

# Our project's data directory
PROJECT_DATA = Path("data/raw")

OIL_ZIP = SOURCE_DIR / "Oil Spill.zip"
CLEAN_ZIP = SOURCE_DIR / "Clean Area.zip"


def extract_images(zip_path, destination):
    print(f"\nExtracting: {zip_path.name}")

    destination.mkdir(parents=True, exist_ok=True)

    with ZipFile(zip_path, "r") as zip_file:
        image_files = [
            name
            for name in zip_file.namelist()
            if name.lower().endswith(
                (".jpg", ".jpeg", ".png", ".tif", ".tiff")
            )
        ]

        print(f"Found {len(image_files)} images")

        for index, image_name in enumerate(image_files, start=1):
            source = zip_file.open(image_name)

            filename = Path(image_name).name
            output_path = destination / filename

            with output_path.open("wb") as output:
                shutil.copyfileobj(source, output)

            if index % 250 == 0:
                print(f"Extracted {index}/{len(image_files)}")


def main():
    print("=" * 60)
    print("MARITIME OIL SPILL DATASET PREPARATION")
    print("=" * 60)

    extract_images(
        OIL_ZIP,
        PROJECT_DATA / "oil_spill"
    )

    extract_images(
        CLEAN_ZIP,
        PROJECT_DATA / "clean_area"
    )

    print("\nDataset extraction complete.")

    oil_count = len(list((PROJECT_DATA / "oil_spill").glob("*")))
    clean_count = len(list((PROJECT_DATA / "clean_area").glob("*")))

    print(f"Oil Spill images: {oil_count}")
    print(f"Clean Area images: {clean_count}")


if __name__ == "__main__":
    main()