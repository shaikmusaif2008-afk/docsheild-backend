# SecureScreen AI — AI-Based Identity & Document Screening Platform
### Prototype Implementation for SIH Problem Statement 26188

SecureScreen AI is an enterprise-grade, AI-assisted decision-support platform built for authorized border-security and immigration personnel. It evaluates travel and identity credentials across multi-stage forensic AI pipelines: optical character recognition (OCR) with character-level confidence, deterministic and database validation, Error Level Analysis (ELA) tampering detection, facial biometric verification, explainable composite risk scoring, and cryptographically chained audit logging.

---

## 🚀 Quick Start Instructions

### 1. Requirements
- Python 3.10+
- Installed packages: `fastapi`, `uvicorn`, `opencv-python`, `pillow`, `reportlab`, `numpy`, `pyjwt`

### 2. Launch the Application
```bash
python run.py
```
The server will initialize the SQLite database, generate sample test documents, and serve the application at:
👉 **`http://localhost:8000`**

### 3. Demo Credentials
| Role | Work ID / Username | Password |
| :--- | :--- | :--- |
| **Senior Screening Officer** | `officer.sharma` | `password123` |
| **Airport Biometrics Specialist** | `officer.patel` | `password123` |
| **Border Command Supervisor** | `inspector.kumar` | `password123` |

*(You can also use the 1-click Demo Officer buttons on the login screen)*

---

## 🎯 3 Built-in Demonstration Scenarios for SIH Evaluators

| Scenario | Document | Persona | Expected Findings | Overall Risk Score | Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Scenario 1** | Genuine Passport | Johnathan Edward Doe | • >98% OCR confidence<br/>• ICAO 9303 checksums passed<br/>• Clean ELA gradient<br/>• 94.8% Face match | **14 / 100** (LOW) | `VERIFIED`<br/>*(Cleared for entry)* |
| **Scenario 2** | Tampered Visa | Alex K. Vance | • Spliced photo boundary detected<br/>• Altered expiry year (2029) font anomaly<br/>• Stolen folio hit in Demo DB<br/>• 31.4% Face mismatch | **82 / 100** (HIGH) | `HIGH RISK`<br/>*(Secondary inspection)* |
| **Scenario 3** | Expired National ID | Maria Elena Gomez | • Expired in 2023 (< Current Date 2026)<br/>• Physical typography intact<br/>• Demo Watchlist expiry match | **58 / 100** (MEDIUM) | `REVIEW REQUIRED`<br/>*(Consular referral)* |
| **Scenario 4** | Custom Upload | Any Document / Photo | • Live real-time OCR extraction<br/>• Interactive ELA heatmap toggle<br/>• Live Webcam biometric comparison | **Dynamic** | **Interactive Review** |

---

## 🏛️ System Architecture

```
                       Frontend (React/Tailwind/Lucide/Canvas)
                                        │
                                        ▼
                             FastAPI REST API Layer
                                        │
                                        ▼
                           Screening Orchestrator
       ┌──────────────────┬─────────────────┬──────────────────┬─────────────────┐
       ▼                  ▼                 ▼                  ▼                 ▼
   OCR Engine      Validation Engine  Tampering AI       Face Biometrics    Risk Engine
 (Tesseract/CV)   (ICAO 9303 Check)     (ELA & CV)     (Cosine Similarity) (Explainable)
       └──────────────────┴─────────────────┼──────────────────┴─────────────────┘
                                            ▼
                           Tamper-Evident Audit Trail
                         (SHA-256 Chained Block Ledger)
                                            │
                                            ▼
                           SQLite Database & PDF Dossier
```

---

## 🛡️ Key Features & SIH 26188 Compliance

1. **OCR Extraction with Confidence**:
   - Parses Full Name, Doc No, Nationality, DOB, Gender, Issue Date, Expiry Date, MRZ lines.
   - Provides confidence percentages per field and allows officer corrections.
2. **Deterministic & Watchlist Validation**:
   - ICAO 9303 7-3-1 weight check digit algorithms.
   - Logical date validation ($DOB < Issue < Expiry > Today$) & 6-month validity rule.
   - Cross-referencing against Demo Border Watchlist database.
3. **Core AI Forensic Tampering Detection**:
   - Real Error Level Analysis (ELA) heatmap computed via JPEG compression differential.
   - Bounding box annotations over suspicious photo boundaries, text alterations, and stamp anomalies.
4. **Facial Biometric Verification**:
   - Auto-crops portrait from document and compares against live webcam capture or photo.
   - Calculates similarity score, quality metrics, and texture liveness assessment.
5. **Explainable AI Risk Engine**:
   - Weighted composite formula: Tampering (35%), Face Match (25%), Validation (20%), Watchlist (15%), OCR (5%).
   - Transparent factor breakdown with point attribution.
6. **Immutable Audit Trail**:
   - Append-only event ledger with parent SHA-256 hash chaining ($H_n = \text{SHA256}(H_{n-1} + \text{Payload})$).
7. **Official PDF Dossier Export**:
   - High-security printable PDF report with case barcodes, forensic summaries, officer signature stamps, and audit block hashes.
