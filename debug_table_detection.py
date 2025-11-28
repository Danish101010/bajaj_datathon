"""
Debug script to test table detection on the sample PDF.
"""

import cv2
import numpy as np
from preprocess import convert_pdf_bytes_to_images, deskew_and_illum_correction
from table_detect import detect_tables
import os

# Enable debug mode
os.environ['DEBUG'] = 'true'

print("=" * 70)
print("TABLE DETECTION DEBUG")
print("=" * 70)

# Load PDF
print("\n1. Loading sample_invoice.pdf...")
with open('sample_invoice.pdf', 'rb') as f:
    pdf_bytes = f.read()

# Convert to images
print("2. Converting PDF to images...")
images = convert_pdf_bytes_to_images(pdf_bytes)
print(f"   Converted {len(images)} page(s)")

# Process first page
print("\n3. Preprocessing page 1...")
img = deskew_and_illum_correction(images[0])
print(f"   Preprocessed shape: {img.shape}")

# Detect tables
print("\n4. Detecting tables...")
tables = detect_tables(img)
print(f"   Found {len(tables)} table(s)")

if tables:
    for i, table in enumerate(tables):
        bbox = table['bbox']
        area = bbox[2] * bbox[3]
        print(f"\n   Table {i+1}:")
        print(f"     BBox: x={bbox[0]}, y={bbox[1]}, w={bbox[2]}, h={bbox[3]}")
        print(f"     Area: {area:,} pixels")
else:
    print("\n   ⚠ No tables detected!")
    print("\n   This means the table lines are not strong enough for detection.")
    print("   Possible issues:")
    print("   - PDF table borders are too thin")
    print("   - Table uses vector graphics instead of raster lines")
    print("   - Preprocessing removed too much detail")

# Save debug visualization
print("\n5. Saving debug visualization...")
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
thresh = cv2.adaptiveThreshold(
    gray, 255,
    cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
    cv2.THRESH_BINARY_INV,
    15, 5
)

# Extract lines
h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
h_mask = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, h_kernel, iterations=2)

v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
v_mask = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, v_kernel, iterations=2)

combined = cv2.add(h_mask, v_mask)

# Save intermediate images
cv2.imwrite('/tmp/debug_01_original.png', img)
cv2.imwrite('/tmp/debug_02_threshold.png', thresh)
cv2.imwrite('/tmp/debug_03_horizontal_lines.png', h_mask)
cv2.imwrite('/tmp/debug_04_vertical_lines.png', v_mask)
cv2.imwrite('/tmp/debug_05_combined_lines.png', combined)

print("   Saved debug images to /tmp/:")
print("   - debug_01_original.png")
print("   - debug_02_threshold.png")
print("   - debug_03_horizontal_lines.png")
print("   - debug_04_vertical_lines.png")
print("   - debug_05_combined_lines.png")

print("\n" + "=" * 70)
print("Debug complete!")
print("=" * 70)
