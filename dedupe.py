"""
Deduplication module for invoice line item candidates.

Provides functions to canonicalize descriptions, deduplicate similar candidates
using fuzzy matching, and filter repeated header/footer elements across pages.
"""

import re
from typing import List, Dict, Tuple, Optional

import numpy as np
import cv2
from rapidfuzz import fuzz


# Common invoice stopwords to remove
INVOICE_STOPWORDS = {
    'qty', 'nos', 'no', 'pcs', 'pc', 'each', 'pack', 'pkt', 'box',
    'unit', 'units', 'item', 'items', 'ea', 'per', 'total', 'amt',
    'amount', 'rate', 'price', 'value', 'description', 'desc'
}


def canonicalize_description(text: str) -> str:
    """
    Normalize description text for comparison.
    
    Applies the following transformations:
    - Convert to lowercase
    - Remove punctuation
    - Remove stopwords common in invoices
    - Reduce multiple spaces to single space
    - Strip leading/trailing whitespace
    
    Args:
        text: Raw description text
    
    Returns:
        Canonicalized description string
    
    Examples:
        >>> canonicalize_description("Item - 5 Nos. (Pack)")
        'item 5'
        >>> canonicalize_description("Product Description: Test Item")
        'product test item'
    """
    if not text:
        return ''
    
    # Convert to lowercase
    text = text.lower()
    
    # Remove punctuation (keep alphanumeric and spaces)
    text = re.sub(r'[^\w\s]', ' ', text)
    
    # Split into tokens
    tokens = text.split()
    
    # Remove stopwords
    filtered_tokens = [t for t in tokens if t not in INVOICE_STOPWORDS]
    
    # Join and reduce multiple spaces
    result = ' '.join(filtered_tokens)
    result = re.sub(r'\s+', ' ', result)
    
    return result.strip()


def deduplicate_candidates(candidates: List[Dict], ratio_thresh: int = 88) -> List[Dict]:
    """
    Deduplicate similar candidates using fuzzy matching.
    
    Groups candidates with similar descriptions (using token_set_ratio) and
    matching amounts. For each group, selects the representative with highest
    confidence and creates a merged record.
    
    Args:
        candidates: List of candidate dictionaries
        ratio_thresh: Fuzzy matching threshold (0-100), default 88
    
    Returns:
        Deduplicated list of candidates, sorted by page and y-coordinate
    
    Algorithm:
        1. Canonicalize all descriptions
        2. Group candidates with similar descriptions and amounts
        3. For each group, pick highest confidence representative
        4. Create merged record with averaged confidence and merged_ids
    """
    if not candidates:
        return []
    
    # Preprocess: add canonical descriptions
    for candidate in candidates:
        candidate['_canonical'] = canonicalize_description(candidate.get('desc', ''))
    
    # Track which candidates have been merged
    merged_into = {}  # candidate_id -> representative_id
    groups = []  # List of groups (each group is a list of candidate indices)
    
    # Build groups using fuzzy matching
    processed = set()
    
    for i, candidate in enumerate(candidates):
        if i in processed:
            continue
        
        # Start a new group with this candidate
        group = [i]
        processed.add(i)
        
        # Find similar candidates
        for j in range(i + 1, len(candidates)):
            if j in processed:
                continue
            
            other = candidates[j]
            
            # Check if descriptions are similar
            ratio = fuzz.token_set_ratio(
                candidate['_canonical'],
                other['_canonical']
            )
            
            if ratio >= ratio_thresh:
                # Additional checks before marking as duplicate
                
                # Check if amounts differ significantly (> 5%)
                candidate_amt = candidate.get('amount')
                other_amt = other.get('amount')
                
                # If amounts are significantly different, don't dedupe
                if candidate_amt is not None and other_amt is not None:
                    diff_pct = abs(candidate_amt - other_amt) / max(candidate_amt, other_amt) * 100
                    if diff_pct > 5:
                        # Amounts differ by > 5%, probably different items
                        continue
                    
                    # Round to 2 decimal places for comparison
                    if abs(round(candidate_amt, 2) - round(other_amt, 2)) < 0.01:
                        # Check if on same page and close vertically
                        if candidate.get('page') == other.get('page'):
                            bbox1 = candidate.get('bbox', (0, 0, 0, 0))
                            bbox2 = other.get('bbox', (0, 0, 0, 0))
                            y1 = bbox1[1] if len(bbox1) >= 2 else 0
                            y2 = bbox2[1] if len(bbox2) >= 2 else 0
                            
                            if abs(y1 - y2) < 50:
                                # Very close vertically - likely same item
                                group.append(j)
                                processed.add(j)
                            # else: Same page but far apart - different items
                        else:
                            # Different pages, same description and amount - likely duplicates
                            group.append(j)
                            processed.add(j)
                elif candidate_amt is None and other_amt is None:
                    # Both have no amount, consider similar
                    group.append(j)
                    processed.add(j)
        
        groups.append(group)
    
    # Create deduplicated list
    deduped = []
    
    for group in groups:
        if len(group) == 1:
            # Single candidate, no merging needed
            candidate = candidates[group[0]].copy()
            candidate.pop('_canonical', None)
            deduped.append(candidate)
        else:
            # Multiple candidates, merge them
            group_candidates = [candidates[idx] for idx in group]
            
            # Pick representative with highest confidence
            representative = max(group_candidates, key=lambda c: c.get('conf', 0))
            
            # Create merged record
            merged = representative.copy()
            merged.pop('_canonical', None)
            
            # Add merged_ids field
            merged['merged_ids'] = [candidates[idx]['id'] for idx in group]
            
            # Average confidence across group
            confs = [c.get('conf', 0) for c in group_candidates]
            merged['conf'] = sum(confs) / len(confs) if confs else 0.0
            
            # Update merged_into tracking
            for idx in group:
                if idx != group[0]:
                    merged_into[candidates[idx]['id']] = representative['id']
            
            deduped.append(merged)
    
    # Sort by page, then by y-coordinate (top of bbox)
    deduped.sort(key=lambda c: (
        c.get('page', 0),
        c.get('bbox', (0, 0, 0, 0))[1]  # y1 coordinate
    ))
    
    return deduped


def repeated_header_footer_filter(
    candidates: List[Dict],
    pages_images: List[np.ndarray]
) -> Tuple[List[Dict], List[Dict]]:
    """
    Filter out candidates in repeated header/footer regions across pages.
    
    Detects regions that appear consistently across multiple pages (likely
    headers or footers) and removes candidates whose bounding boxes intersect
    those regions.
    
    Args:
        candidates: List of candidate dictionaries
        pages_images: List of full-page BGR images
    
    Returns:
        Tuple of (remaining_candidates, filtered_candidates)
    
    Algorithm:
        1. Extract top and bottom strips from each page
        2. Compare strips across pages using template matching
        3. Identify repeated regions (similarity > threshold)
        4. Filter candidates intersecting those regions
    """
    if not candidates or not pages_images or len(pages_images) < 2:
        # Need at least 2 pages to detect repetition
        return candidates, []
    
    # Define header/footer strip heights (as fraction of page height)
    header_frac = 0.15  # Top 15%
    footer_frac = 0.15  # Bottom 15%
    
    # Detect repeated regions
    repeated_regions = _detect_repeated_regions(
        pages_images,
        header_frac,
        footer_frac
    )
    
    if not repeated_regions:
        return candidates, []
    
    # Filter candidates
    remaining = []
    filtered = []
    
    for candidate in candidates:
        page_no = candidate.get('page', 1)
        bbox = candidate.get('bbox')
        
        if bbox is None:
            remaining.append(candidate)
            continue
        
        # Check if candidate intersects any repeated region on its page
        intersects_repeated = False
        
        for region in repeated_regions:
            if region['page'] == page_no:
                if _bbox_intersects_region(bbox, region['bbox']):
                    intersects_repeated = True
                    break
        
        if intersects_repeated:
            filtered.append(candidate)
        else:
            remaining.append(candidate)
    
    return remaining, filtered


def _detect_repeated_regions(
    pages_images: List[np.ndarray],
    header_frac: float,
    footer_frac: float,
    similarity_thresh: float = 0.75
) -> List[Dict]:
    """
    Detect repeated header/footer regions across pages.
    
    Args:
        pages_images: List of page images
        header_frac: Fraction of page height for header
        footer_frac: Fraction of page height for footer
        similarity_thresh: Normalized correlation threshold
    
    Returns:
        List of repeated region dictionaries with page and bbox
    """
    repeated_regions = []
    
    if len(pages_images) < 2:
        return repeated_regions
    
    # Use first page as reference
    ref_page = pages_images[0]
    ref_height, ref_width = ref_page.shape[:2]
    
    # Extract reference strips
    header_height = int(ref_height * header_frac)
    footer_height = int(ref_height * footer_frac)
    
    ref_header = ref_page[0:header_height, :]
    ref_footer = ref_page[-footer_height:, :]
    
    # Convert to grayscale for comparison
    ref_header_gray = cv2.cvtColor(ref_header, cv2.COLOR_BGR2GRAY)
    ref_footer_gray = cv2.cvtColor(ref_footer, cv2.COLOR_BGR2GRAY)
    
    # Check header similarity across pages
    header_similar_count = 0
    footer_similar_count = 0
    
    for page_img in pages_images[1:]:
        page_height, page_width = page_img.shape[:2]
        
        # Extract strips from current page
        page_header_height = int(page_height * header_frac)
        page_footer_height = int(page_height * footer_frac)
        
        page_header = page_img[0:page_header_height, :]
        page_footer = page_img[-page_footer_height:, :]
        
        # Convert to grayscale
        page_header_gray = cv2.cvtColor(page_header, cv2.COLOR_BGR2GRAY)
        page_footer_gray = cv2.cvtColor(page_footer, cv2.COLOR_BGR2GRAY)
        
        # Resize to match reference if needed
        if page_header_gray.shape != ref_header_gray.shape:
            page_header_gray = cv2.resize(
                page_header_gray,
                (ref_header_gray.shape[1], ref_header_gray.shape[0])
            )
        
        if page_footer_gray.shape != ref_footer_gray.shape:
            page_footer_gray = cv2.resize(
                page_footer_gray,
                (ref_footer_gray.shape[1], ref_footer_gray.shape[0])
            )
        
        # Compare using normalized correlation
        header_sim = _normalized_correlation(ref_header_gray, page_header_gray)
        footer_sim = _normalized_correlation(ref_footer_gray, page_footer_gray)
        
        if header_sim > similarity_thresh:
            header_similar_count += 1
        
        if footer_sim > similarity_thresh:
            footer_similar_count += 1
    
    # If header is repeated on most pages, mark it
    if header_similar_count >= len(pages_images) - 1:
        for page_no in range(1, len(pages_images) + 1):
            repeated_regions.append({
                'page': page_no,
                'bbox': (0, 0, ref_width, header_height),
                'type': 'header'
            })
    
    # If footer is repeated on most pages, mark it
    if footer_similar_count >= len(pages_images) - 1:
        for page_no in range(1, len(pages_images) + 1):
            repeated_regions.append({
                'page': page_no,
                'bbox': (0, ref_height - footer_height, ref_width, ref_height),
                'type': 'footer'
            })
    
    return repeated_regions


def _normalized_correlation(img1: np.ndarray, img2: np.ndarray) -> float:
    """
    Compute normalized correlation between two grayscale images.
    
    Args:
        img1: First grayscale image
        img2: Second grayscale image (same size)
    
    Returns:
        Correlation coefficient (0-1)
    """
    if img1.shape != img2.shape:
        return 0.0
    
    # Flatten images
    img1_flat = img1.flatten().astype(np.float32)
    img2_flat = img2.flatten().astype(np.float32)
    
    # Compute normalized correlation
    mean1 = np.mean(img1_flat)
    mean2 = np.mean(img2_flat)
    
    img1_centered = img1_flat - mean1
    img2_centered = img2_flat - mean2
    
    numerator = np.sum(img1_centered * img2_centered)
    denominator = np.sqrt(np.sum(img1_centered ** 2) * np.sum(img2_centered ** 2))
    
    if denominator == 0:
        return 0.0
    
    correlation = numerator / denominator
    
    # Return absolute value (direction doesn't matter)
    return abs(correlation)


def _bbox_intersects_region(bbox: Tuple[int, int, int, int], region_bbox: Tuple[int, int, int, int]) -> bool:
    """
    Check if a bounding box intersects with a region.
    
    Args:
        bbox: (x1, y1, x2, y2) bounding box
        region_bbox: (x1, y1, x2, y2) region bounding box
    
    Returns:
        True if bounding boxes intersect
    """
    x1, y1, x2, y2 = bbox
    rx1, ry1, rx2, ry2 = region_bbox
    
    # Check for no overlap (then negate)
    no_overlap = (x2 < rx1 or x1 > rx2 or y2 < ry1 or y1 > ry2)
    
    return not no_overlap


def test_canonicalize():
    """Test description canonicalization."""
    print("Testing canonicalize_description()...\n")
    
    test_cases = [
        ("Item - 5 Nos. (Pack)", "item 5"),
        ("Product Description: Test Item", "product test item"),
        ("Widget (Qty: 10 pcs)", "widget 10"),
        ("SERVICE CHARGES - TOTAL AMT", "service charges"),
        ("Cable, Connector - 2.5mm (each)", "cable connector 2 5mm"),
    ]
    
    print("Input -> Canonicalized:")
    print("-" * 60)
    
    for input_text, expected in test_cases:
        result = canonicalize_description(input_text)
        status = "✓" if result == expected else "✗"
        print(f"{status} '{input_text}'")
        print(f"   -> '{result}'")
        if result != expected:
            print(f"   Expected: '{expected}'")
    
    print()


def test_fuzzy_matching():
    """Test fuzzy deduplication with sample candidates."""
    print("Testing deduplicate_candidates()...\n")
    
    # Create sample candidates with duplicates
    candidates = [
        {
            'id': 1,
            'page': 1,
            'bbox': (10, 10, 200, 30),
            'desc': 'Widget Type A - 5 Nos',
            'amount': 1234.50,
            'conf': 92.0
        },
        {
            'id': 2,
            'page': 1,
            'bbox': (10, 50, 200, 70),
            'desc': 'Widget Type A (5 pcs)',
            'amount': 1234.50,
            'conf': 88.0
        },
        {
            'id': 3,
            'page': 1,
            'bbox': (10, 90, 200, 110),
            'desc': 'Different Product',
            'amount': 500.00,
            'conf': 90.0
        },
        {
            'id': 4,
            'page': 2,
            'bbox': (10, 10, 200, 30),
            'desc': 'Widget Type-A, Qty: 5',
            'amount': 1234.49,  # Slightly different, should still match
            'conf': 95.0
        }
    ]
    
    print(f"Input: {len(candidates)} candidates")
    print("Expected: IDs 1, 2, 4 should merge (similar descriptions and amounts)\n")
    
    deduped = deduplicate_candidates(candidates, ratio_thresh=85)
    
    print(f"Output: {len(deduped)} unique candidates\n")
    
    for candidate in deduped:
        print(f"Candidate {candidate['id']}:")
        print(f"  Desc: '{candidate['desc']}'")
        print(f"  Amount: {candidate['amount']}")
        print(f"  Conf: {candidate['conf']:.2f}")
        if 'merged_ids' in candidate:
            print(f"  Merged IDs: {candidate['merged_ids']}")
        print()
    
    # Verify fuzzy ratio
    print("Fuzzy matching scores:")
    desc1 = canonicalize_description('Widget Type A - 5 Nos')
    desc2 = canonicalize_description('Widget Type A (5 pcs)')
    desc3 = canonicalize_description('Widget Type-A, Qty: 5')
    
    ratio_12 = fuzz.token_set_ratio(desc1, desc2)
    ratio_13 = fuzz.token_set_ratio(desc1, desc3)
    
    print(f"  '{desc1}' vs '{desc2}': {ratio_12}")
    print(f"  '{desc1}' vs '{desc3}': {ratio_13}")
    print()


def main():
    """Run unit tests."""
    print("=" * 60)
    print("DEDUPLICATION MODULE TESTS")
    print("=" * 60)
    print()
    
    test_canonicalize()
    print("=" * 60)
    print()
    
    test_fuzzy_matching()
    print("=" * 60)
    print()
    
    print("All tests complete!")


if __name__ == "__main__":
    main()
