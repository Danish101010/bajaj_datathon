# Architecture Overview

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                           CLIENT REQUEST                             │
│                    POST /extract-bill-data                           │
│                  {"document": "https://...pdf"}                      │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        FastAPI Server (app.py)                       │
│                         Port 8000 / Uvicorn                          │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
        ┌────────────────────────────────────────────┐
        │     Step 1: Download PDF from URL          │
        │         (requests library)                 │
        └────────────┬───────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────────────────────────┐
        │  Step 2: Convert PDF to Images (300 DPI)   │
        │     preprocess.convert_pdf_bytes_to_images │
        │         (pdf2image + poppler)              │
        └────────────┬───────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────────────────┐
│              FOR EACH PAGE (Multi-page Processing)                  │
└────────────────────────────────────────────────────────────────────┘
                     │
    ┌────────────────┼────────────────┐
    │                │                │
    ▼                ▼                ▼
┌─────────┐    ┌─────────┐    ┌─────────┐
│ Page 1  │    │ Page 2  │    │ Page N  │
└────┬────┘    └────┬────┘    └────┬────┘
     │              │              │
     └──────────────┴──────────────┘
                    │
                    ▼
        ┌───────────────────────────────┐
        │ Step 3a: Preprocess Image     │
        │   - Deskew (minAreaRect)      │
        │   - Illumination correction   │
        │   - CLAHE enhancement          │
        │ preprocess.deskew_and_illum   │
        └───────────┬───────────────────┘
                    │
                    ▼
        ┌───────────────────────────────┐
        │ Step 3b: Detect Tables        │
        │   - Horizontal line mask      │
        │   - Vertical line mask        │
        │   - Combine & find contours   │
        │ table_detect.detect_tables    │
        └───────────┬───────────────────┘
                    │
                    ▼
        ┌───────────────────────────────┐
        │ Step 3c: Segment Table        │
        │   - Horizontal projection     │
        │   - Vertical projection       │
        │   - Row/column boundaries     │
        │ table_detect.segment_table    │
        └───────────┬───────────────────┘
                    │
                    ▼
        ┌───────────────────────────────┐
        │ Step 3d: OCR Each Cell        │
        │   - Tesseract extraction      │
        │   - Confidence scoring        │
        │   - Amount parsing            │
        │ ocr_cells.ocr_image_to_tokens │
        └───────────┬───────────────────┘
                    │
                    ▼
        ┌───────────────────────────────┐
        │ Step 3e: Assemble Candidates  │
        │   - Build line item dicts     │
        │   - Extract descriptions      │
        │   - Identify amounts          │
        │ candidates.assemble_from_table│
        └───────────┬───────────────────┘
                    │
                    └───────────────┐
                                    │
            ┌───────────────────────┘
            │ (Collect all pages)
            ▼
┌────────────────────────────────────────────────────────────────────┐
│                    ALL PAGES COLLECTED                              │
│              List of candidate line items                           │
└────────────────────────────┬───────────────────────────────────────┘
                             │
                             ▼
        ┌────────────────────────────────────────┐
        │  Step 4: Merge Wrapped Rows            │
        │    - Detect continuation lines         │
        │    - Merge by proximity + alignment    │
        │  candidates.merge_wrapped_rows         │
        └────────────┬───────────────────────────┘
                     │
                     ▼
        ┌────────────────────────────────────────┐
        │  Step 5: Filter Headers/Footers        │
        │    - Template matching across pages    │
        │    - Remove repeated regions           │
        │  dedupe.repeated_header_footer_filter  │
        └────────────┬───────────────────────────┘
                     │
                     ▼
        ┌────────────────────────────────────────┐
        │  Step 6: Deduplicate Candidates        │
        │    - Canonicalize descriptions         │
        │    - Fuzzy match (ratio ≥ 88)          │
        │    - Group similar items               │
        │  dedupe.deduplicate_candidates         │
        └────────────┬───────────────────────────┘
                     │
                     ▼
        ┌────────────────────────────────────────┐
        │  Step 7: Extract Reported Total        │
        │    - OCR bottom of last page           │
        │    - Regex pattern matching            │
        │    - Find "Total:", "Grand Total:"     │
        │  app.extract_reported_total            │
        └────────────┬───────────────────────────┘
                     │
                     ▼
        ┌────────────────────────────────────────┐
        │  Step 8: ILP Reconciliation            │
        │    - Create duplicate groups           │
        │    - Formulate ILP problem             │
        │    - Maximize confidence               │
        │    - Match reported total              │
        │  reconcile.ilp_reconcile (PuLP + CBC)  │
        └────────────┬───────────────────────────┘
                     │
                     ▼
        ┌────────────────────────────────────────┐
        │  Step 9: Build Response                │
        │    - Group by page                     │
        │    - Calculate metrics                 │
        │    - Generate warnings                 │
        │    - Flag manual review                │
        │  app.build_response                    │
        └────────────┬───────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         JSON RESPONSE                                │
│  {                                                                   │
│    "is_success": true,                                               │
│    "data": {                                                         │
│      "pagewise_line_items": {...},                                   │
│      "total_item_count": 15,                                         │
│      "reconciled_amount": 1234.50,                                   │
│      "reported_total": 1230.00,                                      │
│      "deviation": 4.50,                                              │
│      "requires_manual_review": false,                                │
│      "warnings": []                                                  │
│    }                                                                 │
│  }                                                                   │
└─────────────────────────────────────────────────────────────────────┘
```

## Module Dependencies

```
app.py
  ├── preprocess.py
  │   ├── pdf2image
  │   ├── PIL (Pillow)
  │   ├── numpy
  │   └── opencv (cv2)
  │
  ├── table_detect.py
  │   ├── numpy
  │   └── opencv (cv2)
  │
  ├── ocr_cells.py
  │   ├── numpy
  │   ├── opencv (cv2)
  │   ├── PIL (Pillow)
  │   └── pytesseract
  │
  ├── candidates.py
  │   ├── numpy
  │   ├── opencv (cv2)
  │   └── ocr_cells.py
  │
  ├── dedupe.py
  │   ├── numpy
  │   ├── opencv (cv2)
  │   └── rapidfuzz
  │
  └── reconcile.py
      └── pulp
```

## Data Flow

```
PDF Bytes
    ↓
PIL Images (RGB)
    ↓
NumPy Arrays (BGR)
    ↓
Preprocessed Images
    ↓
Table Regions (bbox, mask, roi)
    ↓
Row/Column Segments
    ↓
Cell Images
    ↓
OCR Tokens (text, confidence, bbox)
    ↓
Candidate Line Items (id, desc, amount, conf, page, bbox)
    ↓
Merged Candidates
    ↓
Filtered Candidates (no headers/footers)
    ↓
Deduped Candidates
    ↓
ILP Selected Items
    ↓
Structured JSON Response
```

## Key Algorithms

### 1. Table Detection (Morphological)
```
Input Image → Grayscale → Adaptive Threshold
    ↓
Horizontal Kernel (40x1) → Open → Horizontal Mask
    ↓
Vertical Kernel (1x40) → Open → Vertical Mask
    ↓
Combine Masks → Close → Dilate → Find Contours → Tables
```

### 2. Row/Column Segmentation (Projection)
```
Binary Mask → Horizontal Projection (sum across width)
    ↓
Find peaks → Identify row boundaries
    ↓
Binary Mask → Vertical Projection (sum across height)
    ↓
Find peaks → Identify column boundaries
```

### 3. Fuzzy Deduplication (RapidFuzz)
```
Candidate A ──┐
              ├─→ token_set_ratio(A, B) ≥ 88?
Candidate B ──┘
              ↓
         Round(Amount A) == Round(Amount B)?
              ↓
           Same Group
```

### 4. ILP Reconciliation (PuLP)
```
Variables:
  x_i ∈ {0,1} for each candidate i
  z = |selected_total - reported_total|

Objective:
  Maximize: Σ(conf_i × x_i) - 10 × z

Constraints:
  1. Σ(amount_i × x_i) - reported_total = z_plus - z_minus
  2. z = z_plus + z_minus ≤ tolerance
  3. Σ(x_j in duplicate_group) ≤ 1

Solver: CBC (COIN-OR Branch and Cut)
```

## Error Handling Flow

```
Try:
  Execute pipeline
    ↓
Catch specific exceptions:
  ├── requests.Timeout → HTTP 408
  ├── requests.RequestException → HTTP 400
  ├── ValueError (validation) → HTTP 400
  └── General Exception → HTTP 500
    ↓
Return: {"is_success": false, "error": "message"}
```

## Debug Mode

When `DEBUG=true`:
```
Each step saves intermediate images to /tmp:
  - page_N_preprocessed.png
  - debug_page_N.png
  - table_debug_N_tables.png

Logs show detailed progress:
  - Download size
  - Page count
  - Table count per page
  - Row/col counts
  - Candidate counts
  - Dedup results
  - ILP status
```

---

**Architecture Type**: Pipeline (Sequential with parallel page processing)
**Pattern**: ETL (Extract-Transform-Load)
**Scalability**: Horizontal (can process multiple requests in parallel)
**Performance**: I/O bound (PDF download, disk operations)
