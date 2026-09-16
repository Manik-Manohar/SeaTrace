from pathlib import Path

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse


# ---------------------------------------------------------
# Project paths
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DASHBOARD_FILE = PROJECT_ROOT / "deploy" / "dashboard" / "index.html"
UPLOAD_DIR = PROJECT_ROOT / "data" / "uploads"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------

app = FastAPI(
    title="SeaTrace",
    description="Maritime oil-spill detection, drift analysis and vessel attribution platform",
    version="1.0.0",
)


# ---------------------------------------------------------
# Dashboard
# ---------------------------------------------------------

@app.get("/", include_in_schema=False)
def dashboard():
    """
    Serve the SeaTrace investigation dashboard.
    """
    if not DASHBOARD_FILE.exists():
        return {
            "success": False,
            "message": "SeaTrace dashboard file not found.",
        }

    return FileResponse(
        path=DASHBOARD_FILE,
        media_type="text/html",
    )


@app.get("/dashboard", include_in_schema=False)
def dashboard_alias():
    """
    Alternate route for the SeaTrace investigation dashboard.
    """
    return dashboard()


# ---------------------------------------------------------
# Health check
# ---------------------------------------------------------

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "SeaTrace",
    }


# ---------------------------------------------------------
# SAR image upload
# ---------------------------------------------------------

@app.post("/api/sar/upload")
async def upload_sar_image(file: UploadFile = File(...)):
    """
    Upload a SAR image for processing.
    """

    allowed_extensions = {
        ".png",
        ".jpg",
        ".jpeg",
        ".tif",
        ".tiff",
    }

    if not file.filename:
        return {
            "success": False,
            "message": "No filename was provided.",
        }

    file_extension = Path(file.filename).suffix.lower()

    if file_extension not in allowed_extensions:
        return {
            "success": False,
            "message": (
                "Unsupported file type. "
                "Please upload PNG, JPG, JPEG, TIF, or TIFF."
            ),
        }

    # Prevent directory traversal by keeping only the filename
    safe_filename = Path(file.filename).name

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