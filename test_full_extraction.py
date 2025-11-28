"""
Full end-to-end extraction test on sample_invoice.pdf
"""

import os
from preprocess import convert_pdf_bytes_to_images, deskew_and_illum_correction
from table_detect import detect_tables, segment_table_into_rows_and_cols
from candidates import assemble_candidates_from_table
from dedupe import deduplicate_candidates
from reconcile import ilp_reconcile

os.environ['DEBUG'] = 'true'

print("=" * 70)
print("FULL EXTRACTION TEST - sample_invoice_ocr.pdf")
print("=" * 70)

# Step 1: Load and preprocess
print("\n1. Loading and preprocessing PDF...")
with open('sample_invoice_ocr.pdf', 'rb') as f:
    pdf_bytes = f.read()

images = convert_pdf_bytes_to_images(pdf_bytes)
print(f"   Converted {len(images)} page(s)")

# Process first page
img = deskew_and_illum_correction(images[0])
print(f"   Preprocessed shape: {img.shape}")

# Step 2: Detect tables
print("\n2. Detecting tables...")
tables = detect_tables(img)
print(f"   Found {len(tables)} table(s)")

if not tables:
    print("   ⚠ No tables detected - cannot continue")
    exit(1)

# Use the largest table (by area)
tables_sorted = sorted(tables, key=lambda t: t['bbox'][2] * t['bbox'][3], reverse=True)
main_table = tables_sorted[0]
print(f"   Using largest table: bbox={main_table['bbox']}")

# Step 3: Segment table
print("\n3. Segmenting table into rows and columns...")
segmentation = segment_table_into_rows_and_cols(main_table['table_mask'])
rows = segmentation['rows']
cols = segmentation['cols']
print(f"   Detected {len(rows)} rows, {len(cols)} columns")

if len(rows) == 0 or len(cols) == 0:
    print("   ⚠ Table segmentation failed - no rows or columns detected")
    print("   This means the table structure is not clear enough for morphological analysis")
    exit(1)

# Step 4: Assemble candidates
print("\n4. Assembling candidates from table...")
candidates = assemble_candidates_from_table(
    table_roi_bgr=main_table['table_roi'],
    rows=rows,
    cols=cols,
    page_no=1
)
print(f"   Generated {len(candidates)} candidate(s)")

if candidates:
    for i, cand in enumerate(candidates[:5]):  # Show first 5
        print(f"\n   Candidate {i+1}:")
        print(f"     Desc: '{cand.get('desc', '')}'")
        print(f"     Amount: {cand.get('amount')}")
        print(f"     Conf: {cand.get('conf', 0):.2f}")

# Step 5: Deduplicate
print("\n5. Deduplicating candidates...")
unique_candidates = deduplicate_candidates(candidates)
print(f"   {len(unique_candidates)} unique candidate(s) after deduplication")

# Step 6: Reconcile
print("\n6. Reconciling (no target total)...")
result = ilp_reconcile(unique_candidates, reported_total=None, duplicate_groups=[])
print(f"   Status: {result['status']}")
print(f"   Selected: {len(result['selected_ids'])} items")
print(f"   Total: ${result['reconciled_total']:.2f}")

print("\n" + "=" * 70)
print("Test complete!")
print("=" * 70)
