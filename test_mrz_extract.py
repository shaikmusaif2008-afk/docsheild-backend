import re
from rapidocr_onnxruntime import RapidOCR

ocr = RapidOCR()
result, _ = ocr("data/uploads/CASE-2026-F296_56be.jpeg")

lines = [text.strip() for box, text, score in result]
scores = [score for box, text, score in result]

print("Total lines extracted:", len(lines))
for l in lines:
    print("  ->", l)

# Test MRZ line extraction
mrz_lines = []
for l in lines:
    cleaned = l.replace(" ", "").upper()
    if "<" in cleaned and len(cleaned) >= 25:
        mrz_lines.append(cleaned)

print("\nDetected MRZ candidates:", mrz_lines)
