import sqlite3
import json
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any
from .config import DB_PATH

def get_db_connection():
    conn = sqlite3.connect(str(DB_PATH), timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Officers Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS officers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        full_name TEXT NOT NULL,
        badge_number TEXT NOT NULL,
        department TEXT NOT NULL,
        role TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    # 2. Screening Cases Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS screenings (
        case_id TEXT PRIMARY KEY,
        domain TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        officer_id INTEGER,
        officer_name TEXT NOT NULL,
        doc_type TEXT NOT NULL,
        person_name TEXT,
        doc_number TEXT,
        status TEXT NOT NULL,
        overall_risk_score INTEGER NOT NULL,
        risk_level TEXT NOT NULL,
        extracted_data TEXT,
        validation_data TEXT,
        tampering_data TEXT,
        face_data TEXT,
        risk_factors TEXT,
        officer_decision TEXT,
        officer_notes TEXT,
        doc_image_path TEXT,
        ela_image_path TEXT,
        face_doc_path TEXT,
        face_live_path TEXT
    )
    """)

    # Migration: Add domain if not present
    cursor.execute("PRAGMA table_info(screenings);")
    cols = [col[1] for col in cursor.fetchall()]
    if "domain" not in cols:
        cursor.execute("ALTER TABLE screenings ADD COLUMN domain TEXT;")

    # 3. Cryptographically Chained Audit Trail Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_id TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        event_type TEXT NOT NULL,
        officer_name TEXT NOT NULL,
        details TEXT NOT NULL,
        block_index INTEGER NOT NULL,
        prev_hash TEXT NOT NULL,
        current_hash TEXT NOT NULL
    )
    """)

    # 4. Demo Verification Database Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS demo_watchlist (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doc_number TEXT UNIQUE NOT NULL,
        full_name TEXT NOT NULL,
        nationality TEXT NOT NULL,
        dob TEXT NOT NULL,
        status TEXT NOT NULL,
        reason TEXT,
        alert_level TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()

def compute_audit_hash(block_index: int, prev_hash: str, timestamp: str, case_id: str, event_type: str, details_str: str) -> str:
    payload = f"{block_index}|{prev_hash}|{timestamp}|{case_id}|{event_type}|{details_str}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

def log_audit_event(case_id: str, event_type: str, officer_name: str, details: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get last block
    cursor.execute("SELECT block_index, current_hash FROM audit_logs ORDER BY id DESC LIMIT 1")
    last_block = cursor.fetchone()
    
    if last_block:
        block_index = last_block["block_index"] + 1
        prev_hash = last_block["current_hash"]
    else:
        block_index = 1
        prev_hash = "0" * 64  # Genesis block previous hash
        
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    details_str = json.dumps(details, sort_keys=True)
    current_hash = compute_audit_hash(block_index, prev_hash, timestamp, case_id, event_type, details_str)
    
    cursor.execute("""
    INSERT INTO audit_logs (case_id, timestamp, event_type, officer_name, details, block_index, prev_hash, current_hash)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (case_id, timestamp, event_type, officer_name, details_str, block_index, prev_hash, current_hash))
    
    conn.commit()
    conn.close()
    
    return {
        "block_index": block_index,
        "case_id": case_id,
        "timestamp": timestamp,
        "event_type": event_type,
        "officer_name": officer_name,
        "details": details,
        "prev_hash": prev_hash,
        "current_hash": current_hash
    }

def get_all_audit_logs(case_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if case_id:
        cursor.execute("SELECT * FROM audit_logs WHERE case_id = ? ORDER BY id DESC LIMIT ?", (case_id, limit))
    else:
        cursor.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT ?", (limit,))
        
    rows = cursor.fetchall()
    conn.close()
    
    results = []
    for r in rows:
        results.append({
            "id": r["id"],
            "case_id": r["case_id"],
            "timestamp": r["timestamp"],
            "event_type": r["event_type"],
            "officer_name": r["officer_name"],
            "details": json.loads(r["details"]) if r["details"] else {},
            "block_index": r["block_index"],
            "prev_hash": r["prev_hash"],
            "current_hash": r["current_hash"]
        })
    return results

def verify_audit_integrity() -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM audit_logs ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return {"valid": True, "total_blocks": 0, "message": "Audit log is empty."}
        
    expected_prev = "0" * 64
    for idx, r in enumerate(rows):
        if r["prev_hash"] != expected_prev:
            return {"valid": False, "broken_at_block": r["block_index"], "message": "Previous hash mismatch detected!"}
        
        details_str = r["details"]
        computed = compute_audit_hash(r["block_index"], r["prev_hash"], r["timestamp"], r["case_id"], r["event_type"], details_str)
        if computed != r["current_hash"]:
            return {"valid": False, "broken_at_block": r["block_index"], "message": "Current hash mismatch detected!"}
            
        expected_prev = r["current_hash"]
        
    return {"valid": True, "total_blocks": len(rows), "message": "Cryptographic hash chain is 100% intact & verified."}
