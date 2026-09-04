import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / "backend"
FRONTEND_DIR = BASE_DIR / "frontend"

# Check if running in Vercel Serverless environment
IS_VERCEL = bool(
    os.getenv("VERCEL") or 
    os.getenv("VERCEL_ENV") or 
    os.getenv("AWS_LAMBDA_FUNCTION_NAME") or 
    os.getenv("LAMBDA_TASK_ROOT")
)

if IS_VERCEL:
    DATA_DIR = Path("/tmp/docshield_data")
else:
    DATA_DIR = BASE_DIR / "data"

UPLOADS_DIR = DATA_DIR / "uploads"
REPORTS_DIR = DATA_DIR / "reports"
SAMPLES_DIR = DATA_DIR / "samples"
DB_PATH = DATA_DIR / "securescreen.db"

# Ensure runtime directories exist safely
try:
    for folder in [DATA_DIR, UPLOADS_DIR, REPORTS_DIR, SAMPLES_DIR]:
        folder.mkdir(parents=True, exist_ok=True)
        
    # In Vercel environment, copy sample files to /tmp/docshield_data/samples if available
    if IS_VERCEL:
        local_samples = BASE_DIR / "data" / "samples"
        if local_samples.exists():
            import shutil
            for s_file in local_samples.glob("*.*"):
                dst = SAMPLES_DIR / s_file.name
                if not dst.exists():
                    shutil.copyfile(s_file, dst)
except Exception as e:
    print(f"Directory initialization notice: {e}")

# Security & JWT
SECRET_KEY = os.getenv("SECURESCREEN_SECRET_KEY", "securescreen-ai-sih26188-jwt-super-secret-key-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 12  # 12 hours

# Operational Settings
CURRENT_SYSTEM_DATE = "2026-09-02"  # Local system reference date
PASSPORT_VALIDITY_MIN_DAYS = 180  # 6-month validity rule

# Risk Thresholds
RISK_THRESHOLD_LOW = 30
RISK_THRESHOLD_MEDIUM = 60

# Module Weights for Explainable Risk Engine
WEIGHT_TAMPERING = 0.35
WEIGHT_FACE_MATCH = 0.25
WEIGHT_VALIDATION = 0.20
WEIGHT_WATCHLIST_DB = 0.15
WEIGHT_OCR_CONFIDENCE = 0.05
