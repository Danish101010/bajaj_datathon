"""
OCR wrapper module for text extraction from invoice images.

Provides lightweight wrappers around pytesseract for token-level OCR
and specialized extractors for numeric and amount values.
"""

import re
from typing import List, Dict, Optional

import numpy as np
import pytesseract
from pytesseract import Output
from PIL import Image


def ocr_image_to_tokens(img_bgr: np.ndarray) -> Dict:
    """
    Extract OCR tokens with confidence and position information.
    
    Converts BGR image to RGB, runs Tesseract OCR, and returns structured
    token data including text, confidence, and bounding box coordinates.
    
    Args:
        img_bgr: Input image in BGR format (OpenCV)
    
    Returns:
        Dictionary containing:
            - 'text': Full extracted text
            - 'tokens': List of token dictionaries with text, confidence, and bbox
            - 'avg_conf': Average confidence score across all tokens
    
    Raises:
        ValueError: If image is invalid
        Exception: If OCR processing fails
    """
    if img_bgr is None or img_bgr.size == 0:
        raise ValueError("Input image is invalid or empty")
    
    try:
        # Convert BGR to RGB
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB) if len(img_bgr.shape) == 3 else img_bgr
        pil_image = Image.fromarray(img_rgb)
        
        # Run Tesseract with PSM 6 (assume uniform block of text)
        ocr_data = pytesseract.image_to_data(
            pil_image,
            output_type=Output.DICT,
            config="--psm 6"
        )
        
        # Extract full text
        full_text = pytesseract.image_to_string(pil_image, config="--psm 6")
        
        # Build token list
        tokens = []
        confidences = []
        
        n_boxes = len(ocr_data['text'])
        for i in range(n_boxes):
            text = ocr_data['text'][i].strip()
            conf = int(ocr_data['conf'][i])
            
            # Skip empty tokens and invalid confidence
            if not text or conf < 0:
                continue
            
            token = {
                'text': text,
                'conf': conf,
                'left': int(ocr_data['left'][i]),
                'top': int(ocr_data['top'][i]),
                'width': int(ocr_data['width'][i]),
                'height': int(ocr_data['height'][i])
            }
            
            tokens.append(token)
            confidences.append(conf)
        
        # Calculate average confidence
        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
        
        return {
            'text': full_text.strip(),
            'tokens': tokens,
            'avg_conf': avg_conf
        }
        
    except Exception as e:
        raise Exception(f"OCR processing failed: {str(e)}")


def extract_amount_from_cell_text(text: str) -> Optional[float]:
    """
    Extract numeric amount from text with robust parsing.
    
    Handles various formats including:
    - Currency symbols (₹, $, INR, USD, etc.)
    - Thousand separators (commas)
    - Negative amounts in parentheses: (1,234.56)
    - Debit/Credit notation: Dr/Cr
    - Decimal points
    
    Args:
        text: Input text string potentially containing an amount
    
    Returns:
        Extracted float value, or None if no valid amount found
    
    Examples:
        >>> extract_amount_from_cell_text("Total Amount: ₹1,234.50")
        1234.5
        >>> extract_amount_from_cell_text("(1,200.00)")
        -1200.0
        >>> extract_amount_from_cell_text("$500.75 Cr")
        500.75
    """
    if not text or not isinstance(text, str):
        return None
    
    # Check for debit/credit notation
    is_debit = bool(re.search(r'\bDr\b', text, re.IGNORECASE))
    is_credit = bool(re.search(r'\bCr\b', text, re.IGNORECASE))
    
    # Remove currency symbols and common non-numeric characters
    # Keep: digits, decimal point, comma, parentheses, minus
    cleaned = re.sub(r'[₹$€£¥INR USD EUR GBP JPY Rs\s]', '', text, flags=re.IGNORECASE)
    
    # Check for parentheses notation (negative amounts)
    is_negative = False
    parentheses_match = re.search(r'\(([0-9,\.]+)\)', cleaned)
    if parentheses_match:
        is_negative = True
        cleaned = parentheses_match.group(1)
    
    # Extract numeric pattern: optional minus, digits with optional commas, optional decimal
    pattern = r'-?[0-9]{1,3}(?:,?[0-9]{3})*(?:\.[0-9]+)?'
    matches = re.findall(pattern, cleaned)
    
    if not matches:
        return None
    
    # Take the last (typically most relevant) numeric value
    amount_str = matches[-1]
    
    # Remove commas
    amount_str = amount_str.replace(',', '')
    
    try:
        amount = float(amount_str)
        
        # Apply negative sign if in parentheses
        if is_negative:
            amount = -abs(amount)
        
        # Apply debit as negative (if not already negative)
        if is_debit and amount > 0:
            amount = -amount
        
        return amount
        
    except ValueError:
        return None


def extract_best_numeric_in_row(tokens: List[Dict]) -> Optional[float]:
    """
    Extract the best (last) numeric value from a list of tokens.
    
    Scans through tokens from left to right and returns the last valid
    numeric amount found. Useful for extracting amounts from table rows
    where the amount typically appears at the end.
    
    Args:
        tokens: List of token dictionaries from OCR output
    
    Returns:
        Last numeric value found, or None if no valid numbers exist
    
    Examples:
        >>> tokens = [
        ...     {'text': 'Item', 'conf': 95, 'left': 10, 'top': 10, 'width': 50, 'height': 20},
        ...     {'text': '₹1,234.50', 'conf': 92, 'left': 200, 'top': 10, 'width': 80, 'height': 20}
        ... ]
        >>> extract_best_numeric_in_row(tokens)
        1234.5
    """
    if not tokens:
        return None
    
    last_amount = None
    
    for token in tokens:
        text = token.get('text', '')
        amount = extract_amount_from_cell_text(text)
        
        if amount is not None:
            last_amount = amount
    
    return last_amount


# Import cv2 at module level for type hints and usage
import cv2


def main():
    """
    Test OCR extraction functions with sample strings.
    """
    print("Testing extract_amount_from_cell_text()...\n")
    
    test_cases = [
        "Total Amount: ₹1,234.50",
        "(1,200.00)",
        "$500.75",
        "INR 2,50,000.00",
        "Amount: 1234.56 Dr",
        "Balance: 999.99 Cr",
        "₹ 10,00,000",
        "(234.50) Dr",
        "No amount here",
        "3,456.78 USD",
        "₹15,432.10 Total",
    ]
    
    print("Sample inputs and extracted amounts:")
    print("-" * 60)
    
    for test_str in test_cases:
        result = extract_amount_from_cell_text(test_str)
        status = "✓" if result is not None else "✗"
        print(f"{status} '{test_str:30s}' -> {result}")
    
    print("\n" + "=" * 60)
    print("\nTesting extract_best_numeric_in_row()...\n")
    
    # Simulate tokens from a table row
    sample_tokens = [
        {'text': 'Item', 'conf': 95, 'left': 10, 'top': 10, 'width': 50, 'height': 20},
        {'text': 'Description', 'conf': 93, 'left': 70, 'top': 10, 'width': 100, 'height': 20},
        {'text': 'Qty:', 'conf': 91, 'left': 180, 'top': 10, 'width': 40, 'height': 20},
        {'text': '5', 'conf': 94, 'left': 230, 'top': 10, 'width': 20, 'height': 20},
        {'text': 'Amount:', 'conf': 92, 'left': 260, 'top': 10, 'width': 60, 'height': 20},
        {'text': '₹1,234.50', 'conf': 90, 'left': 330, 'top': 10, 'width': 80, 'height': 20}
    ]
    
    print("Sample row tokens:")
    for token in sample_tokens:
        print(f"  '{token['text']}' at ({token['left']}, {token['top']})")
    
    best_amount = extract_best_numeric_in_row(sample_tokens)
    print(f"\nExtracted best numeric: {best_amount}")
    
    print("\n" + "=" * 60)
    print("\nAdditional test with negative amounts:\n")
    
    negative_tokens = [
        {'text': 'Discount', 'conf': 95, 'left': 10, 'top': 10, 'width': 70, 'height': 20},
        {'text': '(500.00)', 'conf': 92, 'left': 90, 'top': 10, 'width': 70, 'height': 20}
    ]
    
    print("Negative amount tokens:")
    for token in negative_tokens:
        print(f"  '{token['text']}' at ({token['left']}, {token['top']})")
    
    negative_amount = extract_best_numeric_in_row(negative_tokens)
    print(f"\nExtracted amount: {negative_amount}")
    
    print("\n" + "=" * 60)
    print("\nAll tests complete!")


if __name__ == "__main__":
    main()
