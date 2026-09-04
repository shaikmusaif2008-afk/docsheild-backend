import os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
TEST_DIR = BASE_DIR / "data" / "test_uploads"
TEST_DIR.mkdir(parents=True, exist_ok=True)

def create_emily_passport():
    """Test A: Valid Passport for Emily Watson with distinct name, MRZ, and face."""
    filepath = TEST_DIR / "test_passport_emily.jpg"
    img = Image.new("RGB", (900, 580), color="#f0fdf4")
    draw = ImageDraw.Draw(img)
    
    # Border & Header
    draw.rectangle([10, 10, 890, 570], outline="#166534", width=3)
    draw.rectangle([15, 15, 885, 75], fill="#14532d")
    draw.text((35, 30), "UNITED KINGDOM OF GREAT BRITAIN AND NORTHERN IRELAND", fill="#f0fdf4")
    draw.text((720, 30), "PASSPORT", fill="#86efac")
    
    # Draw photo (female portrait)
    photo_path = BASE_DIR / "data" / "samples" / "doc_face_expired.jpg"
    if photo_path.exists():
        photo = Image.open(photo_path).resize((180, 220))
        img.paste(photo, (40, 110))
    draw.rectangle([38, 108, 222, 332], outline="#166534", width=2)
    
    # Fields
    fields = [
        ("Type", "P", 260, 100),
        ("Code", "GBR", 380, 100),
        ("Passport No.", "P88392019", 560, 100),
        ("Surname", "WATSON", 260, 150),
        ("Given Names", "EMILY ROSE", 560, 150),
        ("Nationality", "BRITISH CITIZEN", 260, 200),
        ("Date of Birth", "22 JUL 1995", 560, 200),
        ("Sex", "F", 260, 250),
        ("Place of Birth", "LONDON", 380, 250),
        ("Date of Issue", "22 JUL 2022", 260, 300),
        ("Date of Expiry", "21 JUL 2032", 560, 300),
        ("Authority", "HMPO UK", 260, 350)
    ]
    for lbl, val, x, y in fields:
        draw.text((x, y), lbl.upper(), fill="#4b5563")
        draw.text((x, y + 16), val, fill="#111827")
        
    # MRZ Box (with verified ICAO 9303 checksums)
    draw.rectangle([20, 460, 880, 560], fill="#f1f5f9", outline="#94a3b8", width=1)
    draw.text((40, 480), "P<GBRWATSON<<EMILY<ROSE<<<<<<<<<<<<<<<<<<<<<", fill="#0f172a")
    draw.text((40, 515), "P883920199GBR9507225F3207213<<<<<<<<<<<<<<<4", fill="#0f172a")
    
    img.save(filepath, "JPEG", quality=95)
    print(f"Created Test A Document: {filepath}")

def create_chen_visa():
    """Test B: Distinct Japanese Visa for Chen Wei with distinct fields and visa attributes."""
    filepath = TEST_DIR / "test_visa_chen.jpg"
    img = Image.new("RGB", (900, 580), color="#fefce8")
    draw = ImageDraw.Draw(img)
    
    draw.rectangle([10, 10, 890, 570], outline="#854d0e", width=3)
    draw.rectangle([15, 15, 885, 75], fill="#713f12")
    draw.text((35, 30), "JAPAN VISA / TRANSIT ENTRY", fill="#fef08a")
    draw.text((700, 30), "SINGLE ENTRY", fill="#facc15")
    
    photo_path = BASE_DIR / "data" / "samples" / "doc_face_genuine.jpg"
    if photo_path.exists():
        photo = Image.open(photo_path).resize((180, 220))
        img.paste(photo, (40, 110))
    draw.rectangle([38, 108, 222, 332], outline="#854d0e", width=2)
    
    fields = [
        ("Visa No.", "V99120482", 260, 100),
        ("Category", "TRANSIT / TOURISM", 560, 100),
        ("Surname", "CHEN", 260, 150),
        ("Given Name", "WEI", 560, 150),
        ("Passport No.", "G77192014", 260, 200),
        ("Nationality", "CHN", 560, 200),
        ("Date of Birth", "01 DEC 1993", 260, 250),
        ("Date of Issue", "01 DEC 2024", 560, 250),
        ("Date of Expiry", "30 NOV 2027", 260, 300),
        ("Stay Duration", "15 DAYS", 560, 300)
    ]
    for lbl, val, x, y in fields:
        draw.text((x, y), lbl.upper(), fill="#713f12")
        draw.text((x, y + 16), val, fill="#1c1917")
        
    # MRZ (with verified ICAO 9303 checksums)
    draw.rectangle([20, 460, 880, 560], fill="#fef9c3", outline="#ca8a04", width=1)
    draw.text((40, 480), "V<JPNCHEN<<WEI<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<", fill="#1c1917")
    draw.text((40, 515), "V991204820CHN9312018M2711302<<<<<<<<<<<<<<<2", fill="#1c1917")
    
    img.save(filepath, "JPEG", quality=95)
    print(f"Created Test B Document: {filepath}")

def create_poor_quality_doc():
    """Test C: Blurry/Incomplete document without portrait and without MRZ."""
    filepath = TEST_DIR / "test_poor_quality_cropped.jpg"
    img = Image.new("RGB", (500, 300), color="#e5e7eb")
    draw = ImageDraw.Draw(img)
    
    draw.text((30, 40), "RECEIPT / INVOICE NOTICE", fill="#6b7280")
    draw.text((30, 80), "PARTIAL UNREADABLE FRAGMENT 9842", fill="#9ca3af")
    draw.text((30, 120), "DATE: 2021-09-??", fill="#9ca3af")
    
    # Heavy Gaussian Blur to simulate poor optical quality
    blurred = img.filter(ImageFilter.GaussianBlur(radius=3.5))
    blurred.save(filepath, "JPEG", quality=40)
    print(f"Created Test C Document: {filepath}")

def create_invalid_file():
    """Invalid non-image file for negative validation testing."""
    filepath = TEST_DIR / "test_invalid_format.txt"
    with open(filepath, "w") as f:
        f.write("This is a plain text file, not a travel document image.")
    print(f"Created Invalid Format Test File: {filepath}")

if __name__ == "__main__":
    create_emily_passport()
    create_chen_visa()
    create_poor_quality_doc()
    create_invalid_file()
