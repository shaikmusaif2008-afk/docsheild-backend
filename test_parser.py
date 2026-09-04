import re
import json
from rapidocr_onnxruntime import RapidOCR

ocr = RapidOCR()
result, elapse = ocr("data/uploads/CASE-2026-F296_56be.jpeg")

boxes_and_texts = []
raw_lines = []
for box, text, score in result:
    raw_lines.append(text)
    boxes_and_texts.append({"box": box, "text": text, "score": float(score)})

full_text = "\n".join(raw_lines)
print("Raw full text length:", len(full_text))

# 1. Extract MRZ
mrz1 = None
mrz2 = None
for item in boxes_and_texts:
    t = item["text"].replace(" ", "").upper()
    if t.startswith("P<") or t.startswith("V<") or t.startswith("I<"):
        mrz1 = t
    elif mrz1 and "<" in t and len(t) >= 20 and not mrz2:
        mrz2 = t

print("MRZ Line 1:", mrz1)
print("MRZ Line 2:", mrz2)

# 2. Extract Document Number
doc_number = None
# From MRZ
if mrz2:
    doc_number = mrz2[0:9].replace("<", "").strip()

# Or from VIZ regex
if not doc_number:
    match_doc = re.search(r'([A-Z][0-9]{7,8})', full_text)
    if match_doc:
        doc_number = match_doc.group(1)

print("Document Number:", doc_number)

# 3. Extract Full Name
full_name = None
if mrz1:
    names_raw = mrz1[5:].split("<<")
    surname = names_raw[0].replace("<", " ").strip()
    given = names_raw[1].replace("<", " ").strip() if len(names_raw) > 1 else ""
    full_name = f"{given} {surname}".strip() if given else surname

if not full_name:
    # Try finding Surname and Given Name in raw text
    for i, line in enumerate(raw_lines):
        if "Surname" in line and i + 1 < len(raw_lines):
            surname = raw_lines[i+1].strip()
        if "Given" in line and i + 1 < len(raw_lines):
            given = raw_lines[i+1].strip()

print("Full Name:", full_name)

# 4. Extract Nationality
nationality = "IND" if "IND" in full_text or "INDIAN" in full_text else "Not detected"
if mrz1 and len(mrz1) >= 5:
    nationality = mrz1[2:5].replace("<", "")

print("Nationality:", nationality)

# 5. Extract DOB, Issue Date, Expiry Date
dates = re.findall(r'(\d{2}[\/\-\.]\d{2}[\/\-\.]\d{4})', full_text)
print("Extracted Dates:", dates)

# 6. Extract Gender
gender = "Not detected"
if mrz2 and len(mrz2) >= 21:
    g_char = mrz2[20]
    gender = "Male" if g_char == "M" else "Female" if g_char == "F" else "Not detected"
elif re.search(r'\b(M|MALE)\b', full_text, re.I):
    gender = "Male"
elif re.search(r'\b(F|FEMALE)\b', full_text, re.I):
    gender = "Female"

print("Gender:", gender)
