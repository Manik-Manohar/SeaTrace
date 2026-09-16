from pathlib import Path

from fastapi import FastAPI, File, UploadFile


app = FastAPI(
    title="Maritime Oil Spill Intelligence",
    description="AI-powered oil spill detection and vessel attribution platform",
    version="0.1.0",
)


# Folder where uploaded SAR images will be stored
UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/")
def root():
    return {
        "message": "Maritime Oil Spill Intelligence API is running!",
        "status": "online",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
    }


@app.post("/api/sar/upload")
async def upload_sar_image(file: UploadFile = File(...)):
    # Basic file validation
    allowed_extensions = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}

    file_extension = Path(file.filename).suffix.lower()

    if file_extension not in allowed_extensions:
        return {
            "success": False,
            "message": "Unsupported file type. Please upload PNG, JPG, JPEG, TIF, or TIFF.",
        }

    # Create a safe filename
    safe_filename = Path(file.filename).name

    # Save the uploaded file
    destination = UPLOAD_DIR / safe_filename

    contents = await file.read()
    destination.write_bytes(contents)

    return {
        "success": True,
        "message": "SAR image uploaded successfully.",
        "filename": safe_filename,
        "size_bytes": len(contents),
        "path": str(destination),
    }