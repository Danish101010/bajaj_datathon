"""
Text-position-based extraction for invoices without strong table lines.

Uses OCR token positions to cluster text into rows and columns,
bypassing morphological table detection entirely.
"""

from typing import List, Dict, Tuple, Optional
import numpy as np
import cv2
from collections import defaultdict

from ocr_cells import ocr_image_to_tokens, extract_amount_from_cell_text


def cluster_tokens_into_rows(tokens: List[Dict], y_threshold: int = 15) -> List[List[Dict]]:
    """
    Cluster OCR tokens into rows based on vertical position.
    
    Args:
        tokens: List of token dictionaries with 'top', 'left', 'width', 'height'
        y_threshold: Maximum y-distance to consider tokens in same row
    
    Returns:
        List of rows, each containing tokens sorted left-to-right
    """
    if not tokens:
        return []
    
    # Sort tokens by y-coordinate (top)
    sorted_tokens = sorted(tokens, key=lambda t: t['top'])
    
    rows = []
    current_row = [sorted_tokens[0]]
    current_y = sorted_tokens[0]['top']
    
    for token in sorted_tokens[1:]:
        token_y = token['top']
        
        # Check if token belongs to current row
        if abs(token_y - current_y) <= y_threshold:
            current_row.append(token)
        else:
            # Sort current row left-to-right and save
            current_row.sort(key=lambda t: t['left'])
            rows.append(current_row)
            
            # Start new row
            current_row = [token]
            current_y = token_y
    
    # Add last row
    if current_row:
        current_row.sort(key=lambda t: t['left'])
        rows.append(current_row)
    
    return rows


def extract_line_item_from_row(row_tokens: List[Dict]) -> Optional[Dict]:
    """
    Extract a line item candidate from a row of tokens.
    
    Looks for description tokens (text) and amount tokens (numeric).
    
    Args:
        row_tokens: List of tokens in a single row, sorted left-to-right
    
    Returns:
        Candidate dictionary or None if no valid amount found
    """
    if not row_tokens:
        return None
    
    # Separate tokens into text and potential amounts
    desc_tokens = []
    amount_candidates = []
    
    for token in row_tokens:
        text = token['text'].strip()
        if not text:
            continue
        
        # Try to extract amount
        amount = extract_amount_from_cell_text(text)
        
        print(f"    DEBUG extract_line: token='{text}' -> amount={amount}")
        
        if amount is not None:
            amount_candidates.append({
                'amount': amount,
                'conf': token['conf'],
                'text': text
            })
        else:
            # Non-numeric text is part of description
            desc_tokens.append(text)
    
    # If no valid amounts found, skip this row
    if not amount_candidates:
        return None
    
    # Filter out trailing zeros (often discount columns)
    # Use the largest non-zero amount, or if all zero, use last amount
    non_zero_amounts = [a for a in amount_candidates if a['amount'] > 0.01]
    
    if non_zero_amounts:
        # Use the rightmost non-zero amount (line total, ignoring discount)
        best_amount = non_zero_amounts[-1]['amount']
    else:
        # All amounts are zero - use the last one
        best_amount = amount_candidates[-1]['amount']
    
    avg_conf = sum(t['conf'] for t in row_tokens) / len(row_tokens)
    
    # Build description from text tokens
    description = ' '.join(desc_tokens).strip()
    
    # Calculate bounding box
    x1 = min(t['left'] for t in row_tokens)
    y1 = min(t['top'] for t in row_tokens)
    x2 = max(t['left'] + t['width'] for t in row_tokens)
    y2 = max(t['top'] + t['height'] for t in row_tokens)
    
    return {
        'desc': description,
        'amount': best_amount,
        'conf': avg_conf,
        'bbox': (x1, y1, x2, y2),
        'raw_cells': [t['text'] for t in row_tokens]
    }


def extract_candidates_text_based(img_bgr: np.ndarray, page_no: int) -> List[Dict]:
    """
    Extract line item candidates using text position clustering.
    
    This bypasses morphological table detection entirely and works
    directly with OCR token positions.
    
    Args:
        img_bgr: Preprocessed BGR image of the invoice page
        page_no: Page number for tracking
    
    Returns:
        List of candidate dictionaries with 'id', 'page', 'desc', 'amount', 'conf', 'bbox'
    """
    # Run OCR on entire page
    ocr_result = ocr_image_to_tokens(img_bgr)
    tokens = ocr_result.get('tokens', [])
    
    print(f"DEBUG: OCR returned {len(tokens)} tokens")
    if tokens:
        print(f"DEBUG: First token: {tokens[0]}")
    
    if not tokens:
        return []
    
    # Filter out low-confidence tokens
    tokens = [t for t in tokens if t['conf'] >= 30.0]
    print(f"DEBUG: After filtering: {len(tokens)} tokens")
    
    # Cluster tokens into rows
    rows = cluster_tokens_into_rows(tokens, y_threshold=20)
    print(f"DEBUG: Clustered into {len(rows)} rows")
    
    # Extract candidates from each row
    candidates = []
    candidate_id = 1
    
    for idx, row in enumerate(rows):
        candidate = extract_line_item_from_row(row)
        print(f"DEBUG: Row {idx}: {len(row)} tokens -> candidate desc='{candidate.get('desc', 'NONE') if candidate else 'NONE'}' amount={candidate.get('amount', 'NONE') if candidate else 'NONE'}")
        
        if candidate:
            # Skip if description is too short (likely header/footer)
            if len(candidate['desc']) < 3:
                continue
            
            # Skip if amount seems unreasonable (filter noise)
            if candidate['amount'] and abs(candidate['amount']) > 999999999:
                continue
            
            # Skip total/summary rows (footer elements)
            desc_lower = candidate['desc'].lower()
            total_keywords = ['total', 'subtotal', 'grand total', 'amount due', 
                            'balance', 'net amount', 'sum', 'category total']
            if any(keyword in desc_lower for keyword in total_keywords):
                continue
            
            candidate['id'] = candidate_id
            candidate['page'] = page_no
            candidates.append(candidate)
            candidate_id += 1
    
    print(f"DEBUG: Returning {len(candidates)} candidates")
    return candidates


def extract_reported_total_text_based(img_bgr: np.ndarray) -> Optional[float]:
    """
    Extract reported total from invoice using text-based approach.
    
    Looks for keywords like "total", "grand total", "amount due" followed by amounts.
    
    Args:
        img_bgr: Preprocessed BGR image
    
    Returns:
        Reported total amount or None
    """
    ocr_result = ocr_image_to_tokens(img_bgr)
    tokens = ocr_result.get('tokens', [])
    
    if not tokens:
        return None
    
    # Keywords that indicate a total amount
    total_keywords = [
        'total', 'grand total', 'amount due', 'net amount',
        'balance due', 'final amount', 'invoice total'
    ]
    
    # Look for keyword followed by amount
    for i, token in enumerate(tokens):
        text_lower = token['text'].lower().strip()
        
        # Check if this token contains a total keyword
        keyword_found = any(kw in text_lower for kw in total_keywords)
        
        if keyword_found:
            # Look for amounts in nearby tokens (same row or next few tokens)
            for j in range(i, min(i + 5, len(tokens))):
                amount = extract_amount_from_cell_text(tokens[j]['text'])
                if amount is not None and amount > 0:
                    return amount
    
    return None


if __name__ == "__main__":
    """Test the text-based extraction on a sample image."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python text_based_extraction.py <image_path>")
        sys.exit(1)
    
    img_path = sys.argv[1]
    img = cv2.imread(img_path)
    
    if img is None:
        print(f"Failed to load image: {img_path}")
        sys.exit(1)
    
    print(f"Processing: {img_path}")
    print(f"Image shape: {img.shape}")
    print("=" * 60)
    
    # Extract candidates
    candidates = extract_candidates_text_based(img, page_no=1)
    
    print(f"\nExtracted {len(candidates)} candidate(s):")
    print("-" * 60)
    
    for cand in candidates:
        print(f"ID {cand['id']}: {cand['desc'][:50]}")
        print(f"  Amount: ${cand['amount']:.2f}" if cand['amount'] else "  Amount: None")
        print(f"  Confidence: {cand['conf']:.1f}%")
        print()
    
    # Extract reported total
    total = extract_reported_total_text_based(img)
    print(f"Reported Total: ${total:.2f}" if total else "Reported Total: None")
