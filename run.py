import uvicorn
import os
import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from backend.database import init_db
from backend.seed_data import seed_database

def main():
    print("=" * 65)
    print("  SECURESCREEN AI — AI-Based Identity & Document Screening System")
    print("  SIH Problem Statement 26188 Prototype")
    print("=" * 65)
    
    print("[1/3] Initializing SQLite database...")
    init_db()
    
    print("[2/3] Seeding demo officers, watchlist records, and sample assets...")
    seed_database()
    
    port = int(os.getenv("PORT", 8000))
    print(f"[3/3] Starting SecureScreen AI Server on http://localhost:{port}")
    print("      -> Login credentials: officer.sharma / password123")
    print("      -> Demo Scenarios: Genuine Passport, Tampered Visa, Expired ID")
    print("=" * 65)
    
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=False)

if __name__ == "__main__":
    main()
