"""
Candidate assembly module for invoice line items.

Assembles candidate line items from detected table structures by OCR-ing
individual cells and applying heuristics to extract descriptions and amounts.
"""

from typing import List, Tuple, Dict, Optional

import numpy as np
import cv2

from ocr_cells import ocr_image_to_tokens, extract_amount_from_cell_text


# Global counter for candidate IDs
_candidate_id_counter = 0


def assemble_candidates_from_table(
    table_roi_bgr: np.ndarray,
    rows: List[Tuple[int, int]],
    cols: List[Tuple[int, int]],
    page_no: int
) -> List[Dict]:
    """
    Assemble candidate line items from a table by OCR-ing individual cells.
    
    For each row, extracts text from each column cell, identifies numeric
    amounts (typically in rightmost columns), and textual descriptions
    (typically in leftmost columns).
    
    Args:
        table_roi_bgr: BGR image of the table region
        rows: List of (start, end) tuples for row boundaries
        cols: List of (start, end) tuples for column boundaries
        page_no: Page number for tracking
    
    Returns:
        List of candidate dictionaries, each containing:
            - 'id': Unique candidate identifier
            - 'page': Page number
            - 'bbox': (x1, y1, x2, y2) bounding box in table coordinates
            - 'raw_cells': List of extracted cell texts
            - 'desc': Description (concatenated non-numeric left cells)
            - 'amount': Extracted numeric amount (or None)
            - 'conf': Average OCR confidence score
    
    Raises:
        ValueError: If input parameters are invalid
    """
    global _candidate_id_counter
    
    if table_roi_bgr is None or table_roi_bgr.size == 0:
        raise ValueError("Table ROI is invalid or empty")
    
    if not rows:
        return []
    
    candidates = []
    
    for row_start, row_end in rows:
        # Validate row bounds
        if row_start < 0 or row_end > table_roi_bgr.shape[0]:
            continue
        
        if row_end - row_start < 5:  # Skip very thin rows
            continue
        
        # Initialize candidate
        _candidate_id_counter += 1
        candidate = {
            'id': _candidate_id_counter,
            'page': page_no,
            'bbox': None,
            'raw_cells': [],
            'desc': '',
            'amount': None,
            'conf': 0.0
        }
        
        cell_texts = []
        cell_confidences = []
        numeric_cells = []
        
        # If no columns defined, treat entire row as single cell
        if not cols:
            cols = [(0, table_roi_bgr.shape[1])]
        
        # Process each cell in the row
        for col_idx, (col_start, col_end) in enumerate(cols):
            # Validate column bounds
            if col_start < 0 or col_end > table_roi_bgr.shape[1]:
                continue
            
            if col_end - col_start < 5:  # Skip very narrow columns
                continue
            
            # Crop cell region
            cell_img = table_roi_bgr[row_start:row_end, col_start:col_end]
            
            if cell_img.size == 0:
                cell_texts.append('')
                continue
            
            # OCR the cell
            try:
                ocr_result = ocr_image_to_tokens(cell_img)
                cell_text = ocr_result['text'].strip()
                cell_conf = ocr_result['avg_conf']
                
                cell_texts.append(cell_text)
                cell_confidences.append(cell_conf)
                
                # Check if cell contains a numeric amount
                amount = extract_amount_from_cell_text(cell_text)
                if amount is not None:
                    numeric_cells.append({
                        'col_idx': col_idx,
                        'amount': amount,
                        'text': cell_text
                    })
                
            except Exception as e:
                # Silently skip failed OCR
                cell_texts.append('')
        
        # Store raw cell texts
        candidate['raw_cells'] = cell_texts
        
        # Calculate average confidence
        if cell_confidences:
            candidate['conf'] = sum(cell_confidences) / len(cell_confidences)
        
        # Extract amount from rightmost numeric cell
        if numeric_cells:
            rightmost_numeric = max(numeric_cells, key=lambda x: x['col_idx'])
            candidate['amount'] = rightmost_numeric['amount']
        
        # Build description from leftmost non-numeric cells
        desc_parts = []
        for col_idx, text in enumerate(cell_texts):
            # Stop at first numeric cell or after collecting sufficient description
            if any(nc['col_idx'] == col_idx for nc in numeric_cells):
                break
            
            if text:
                desc_parts.append(text)
        
        candidate['desc'] = ' '.join(desc_parts).strip()
        
        # Set bounding box (in table coordinates)
        col_start = cols[0][0] if cols else 0
        col_end = cols[-1][1] if cols else table_roi_bgr.shape[1]
        candidate['bbox'] = (col_start, row_start, col_end, row_end)
        
        # Only add candidate if it has some content
        if candidate['desc'] or candidate['amount'] is not None:
            candidates.append(candidate)
    
    return candidates


def merge_wrapped_rows(candidates: List[Dict]) -> List[Dict]:
    """
    Merge wrapped text rows with their parent line items.
    
    Detects and merges candidates that appear to be continuation lines
    (no amount, vertically adjacent, left-aligned) into their parent
    candidates above.
    
    Args:
        candidates: List of candidate dictionaries
    
    Returns:
        Merged list of candidates with wrapped rows consolidated
    
    Algorithm:
        - A candidate is considered a wrapped row if:
          1. It has no amount
          2. It has description text
          3. It is vertically close to previous candidate (< 10px gap)
          4. It is horizontally aligned (left edge within 20px)
    """
    if not candidates:
        return []
    
    merged = []
    skip_next = set()
    
    for i, candidate in enumerate(candidates):
        if i in skip_next:
            continue
        
        # Start with current candidate
        merged_candidate = candidate.copy()
        
        # Look ahead for potential wrapped rows
        j = i + 1
        while j < len(candidates):
            next_candidate = candidates[j]
            
            # Check if next candidate is a wrapped row
            if _is_wrapped_row(merged_candidate, next_candidate):
                # Merge next candidate into current
                merged_candidate = _merge_two_candidates(merged_candidate, next_candidate)
                skip_next.add(j)
                j += 1
            else:
                # No more wrapped rows
                break
        
        merged.append(merged_candidate)
    
    return merged


def _is_wrapped_row(parent: Dict, candidate: Dict) -> bool:
    """
    Determine if candidate is a wrapped continuation of parent.
    
    Args:
        parent: Parent candidate (line item with amount)
        candidate: Potential wrapped row candidate
    
    Returns:
        True if candidate appears to be a wrapped row
    """
    # Must have no amount
    if candidate['amount'] is not None:
        return False
    
    # Must have description text
    if not candidate['desc'] or len(candidate['desc']) < 3:
        return False
    
    # Must be on same page
    if parent['page'] != candidate['page']:
        return False
    
    # Check vertical proximity
    parent_bbox = parent['bbox']
    candidate_bbox = candidate['bbox']
    
    if parent_bbox is None or candidate_bbox is None:
        return False
    
    # parent_bbox: (x1, y1, x2, y2)
    # candidate_bbox: (x1, y1, x2, y2)
    parent_bottom = parent_bbox[3]
    candidate_top = candidate_bbox[1]
    
    vertical_gap = candidate_top - parent_bottom
    
    # Should be vertically adjacent (within 10 pixels)
    if vertical_gap < -5 or vertical_gap > 10:
        return False
    
    # Check horizontal alignment (left edge within 20 pixels)
    parent_left = parent_bbox[0]
    candidate_left = candidate_bbox[0]
    
    horizontal_offset = abs(candidate_left - parent_left)
    
    if horizontal_offset > 20:
        return False
    
    return True


def _merge_two_candidates(parent: Dict, wrapped: Dict) -> Dict:
    """
    Merge a wrapped row into its parent candidate.
    
    Args:
        parent: Parent candidate
        wrapped: Wrapped row candidate to merge
    
    Returns:
        New merged candidate dictionary
    """
    merged = parent.copy()
    
    # Append wrapped description to parent description
    if wrapped['desc']:
        if merged['desc']:
            merged['desc'] += ' ' + wrapped['desc']
        else:
            merged['desc'] = wrapped['desc']
    
    # Extend bounding box to include wrapped row
    if parent['bbox'] and wrapped['bbox']:
        x1 = min(parent['bbox'][0], wrapped['bbox'][0])
        y1 = parent['bbox'][1]  # Keep parent top
        x2 = max(parent['bbox'][2], wrapped['bbox'][2])
        y2 = wrapped['bbox'][3]  # Extend to wrapped bottom
        merged['bbox'] = (x1, y1, x2, y2)
    
    # Combine raw cells (append wrapped cells)
    merged['raw_cells'] = parent['raw_cells'] + wrapped['raw_cells']
    
    # Average confidence scores
    if parent['conf'] > 0 and wrapped['conf'] > 0:
        merged['conf'] = (parent['conf'] + wrapped['conf']) / 2.0
    
    return merged


def main():
    """
    Demonstrate candidate assembly with synthetic examples.
    """
    print("Testing candidate assembly functions...\n")
    print("=" * 60)
    
    # Create a synthetic table ROI (simple white background with black text areas)
    print("\n1. Creating synthetic table image...")
    table_height = 200
    table_width = 400
    table_roi = np.ones((table_height, table_width, 3), dtype=np.uint8) * 255
    
    # Add some dark regions to simulate text
    cv2.rectangle(table_roi, (10, 10), (150, 30), (0, 0, 0), -1)  # Row 1, desc
    cv2.rectangle(table_roi, (300, 10), (380, 30), (0, 0, 0), -1)  # Row 1, amount
    
    cv2.rectangle(table_roi, (10, 50), (150, 70), (0, 0, 0), -1)  # Row 2, desc
    cv2.rectangle(table_roi, (300, 50), (380, 70), (0, 0, 0), -1)  # Row 2, amount
    
    print(f"   Table shape: {table_roi.shape}")
    
    # Define row and column segments
    rows = [
        (5, 35),   # Row 1
        (45, 75),  # Row 2
        (85, 115), # Row 3
    ]
    
    cols = [
        (5, 200),   # Description column
        (210, 290), # Quantity column
        (295, 390), # Amount column
    ]
    
    print(f"   Rows: {len(rows)}")
    print(f"   Cols: {len(cols)}")
    
    # Assemble candidates
    print("\n2. Assembling candidates from table...")
    try:
        candidates = assemble_candidates_from_table(table_roi, rows, cols, page_no=1)
        print(f"   Generated {len(candidates)} candidate(s)")
        
        for candidate in candidates:
            print(f"\n   Candidate {candidate['id']}:")
            print(f"     Page: {candidate['page']}")
            print(f"     BBox: {candidate['bbox']}")
            print(f"     Desc: '{candidate['desc']}'")
            print(f"     Amount: {candidate['amount']}")
            print(f"     Conf: {candidate['conf']:.2f}")
            print(f"     Raw cells: {len(candidate['raw_cells'])} cells")
    
    except Exception as e:
        print(f"   Note: {str(e)}")
    
    print("\n" + "=" * 60)
    print("\n3. Testing merge_wrapped_rows()...")
    
    # Create sample candidates with a wrapped row
    sample_candidates = [
        {
            'id': 1,
            'page': 1,
            'bbox': (10, 10, 390, 30),
            'raw_cells': ['Item 1', '5', '₹1,234.50'],
            'desc': 'Item 1',
            'amount': 1234.50,
            'conf': 92.0
        },
        {
            'id': 2,
            'page': 1,
            'bbox': (10, 32, 390, 45),
            'raw_cells': ['continued description'],
            'desc': 'continued description',
            'amount': None,
            'conf': 88.0
        },
        {
            'id': 3,
            'page': 1,
            'bbox': (10, 60, 390, 80),
            'raw_cells': ['Item 2', '3', '₹500.00'],
            'desc': 'Item 2',
            'amount': 500.00,
            'conf': 90.0
        }
    ]
    
    print(f"   Input: {len(sample_candidates)} candidates")
    print("   Candidate 2 should be merged into Candidate 1 (wrapped row)")
    
    merged = merge_wrapped_rows(sample_candidates)
    print(f"\n   Output: {len(merged)} candidates after merging")
    
    for candidate in merged:
        print(f"\n   Candidate {candidate['id']}:")
        print(f"     Desc: '{candidate['desc']}'")
        print(f"     Amount: {candidate['amount']}")
        print(f"     BBox: {candidate['bbox']}")
    
    print("\n" + "=" * 60)
    print("\nAll tests complete!")
    print("\nNote: Actual OCR would extract real text from images.")
    print("This demo uses synthetic data to show function signatures.")


if __name__ == "__main__":
    main()
