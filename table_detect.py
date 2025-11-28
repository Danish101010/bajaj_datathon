"""
Table detection module for invoice extraction.

Uses OpenCV morphological operations to detect table structures,
extract table regions, and segment them into rows and columns.
"""

import os
from typing import List, Tuple, Dict

import numpy as np
import cv2


def detect_tables(img_bgr: np.ndarray, min_table_area: int = 3000) -> List[Dict]:
    """
    Detect table structures in a preprocessed BGR image.
    
    Uses morphological operations to extract horizontal and vertical lines,
    combines them to find table regions, and returns table information.
    
    Args:
        img_bgr: Preprocessed BGR image
        min_table_area: Minimum area (pixels) to consider as a table
    
    Returns:
        List of dictionaries, each containing:
            - 'bbox': (x, y, w, h) bounding box coordinates
            - 'table_mask': Binary mask of the table structure
            - 'table_roi': Cropped BGR image of the table region
    
    Raises:
        ValueError: If input image is invalid
    """
    if img_bgr is None or img_bgr.size == 0:
        raise ValueError("Input image is invalid or empty")
    
    # Convert to grayscale
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    
    # Apply adaptive thresholding for better edge detection
    thresh = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        11,
        3
    )
    
    # Extract horizontal lines (reduced kernel size for thinner lines)
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1))
    horizontal_mask = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)
    
    # Extract vertical lines (reduced kernel size for thinner lines)
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 25))
    vertical_mask = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, vertical_kernel, iterations=2)
    
    # Combine horizontal and vertical masks
    table_mask = cv2.add(horizontal_mask, vertical_mask)
    
    # Close small gaps in the table structure
    closing_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    table_mask = cv2.morphologyEx(table_mask, cv2.MORPH_CLOSE, closing_kernel, iterations=5)
    
    # Dilate to connect nearby components
    dilate_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (10, 10))
    table_mask = cv2.dilate(table_mask, dilate_kernel, iterations=2)
    
    # Find contours of table regions
    contours, _ = cv2.findContours(table_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    tables = []
    
    for contour in contours:
        # Get bounding box
        x, y, w, h = cv2.boundingRect(contour)
        area = w * h
        
        # Filter by minimum area
        if area < min_table_area:
            continue
        
        # Extract table region
        table_roi = img_bgr[y:y+h, x:x+w].copy()
        
        # Create binary mask for this specific table
        single_table_mask = np.zeros(table_mask.shape, dtype=np.uint8)
        cv2.drawContours(single_table_mask, [contour], -1, 255, -1)
        single_table_mask = single_table_mask[y:y+h, x:x+w]
        
        table_info = {
            'bbox': (x, y, w, h),
            'table_mask': single_table_mask,
            'table_roi': table_roi
        }
        
        tables.append(table_info)
    
    # Save debug visualization if enabled
    _save_table_debug_visualization(img_bgr, tables)
    
    return tables


def segment_table_into_rows_and_cols(
    table_mask: np.ndarray,
    min_row_height: int = 12,
    min_col_width: int = 10
) -> Dict[str, List[Tuple[int, int]]]:
    """
    Segment a table mask into rows and columns using projection analysis.
    
    Computes horizontal and vertical projections to identify row and column
    boundaries in the table structure.
    
    Args:
        table_mask: Binary mask of table structure (2D numpy array)
        min_row_height: Minimum height (pixels) for a valid row
        min_col_width: Minimum width (pixels) for a valid column
    
    Returns:
        Dictionary containing:
            - 'rows': List of (start, end) tuples for row ranges
            - 'cols': List of (start, end) tuples for column ranges
    
    Raises:
        ValueError: If table_mask is invalid
    """
    if table_mask is None or table_mask.size == 0:
        raise ValueError("Table mask is invalid or empty")
    
    if len(table_mask.shape) != 2:
        raise ValueError("Table mask must be a 2D array")
    
    # Ensure binary mask
    if table_mask.dtype != np.uint8:
        table_mask = table_mask.astype(np.uint8)
    
    # Compute horizontal projection (for rows)
    horizontal_proj = np.sum(table_mask > 0, axis=1)
    
    # Compute vertical projection (for columns)
    vertical_proj = np.sum(table_mask > 0, axis=0)
    
    # Find row segments (lower threshold for thinner lines)
    rows = _find_segments_from_projection(
        horizontal_proj,
        min_width=min_row_height,
        threshold_frac=0.05
    )
    
    # Find column segments (lower threshold for thinner lines)
    cols = _find_segments_from_projection(
        vertical_proj,
        min_width=min_col_width,
        threshold_frac=0.05
    )
    
    return {
        'rows': rows,
        'cols': cols
    }


def _find_segments_from_projection(
    proj: np.ndarray,
    min_width: int,
    threshold_frac: float = 0.1
) -> List[Tuple[int, int]]:
    """
    Find segments (rows or columns) from a projection histogram.
    
    Identifies continuous regions where projection values exceed a threshold,
    treating these as row or column segments.
    
    Args:
        proj: 1D projection array (horizontal or vertical)
        min_width: Minimum width/height for a valid segment
        threshold_frac: Fraction of max projection to use as threshold (0-1)
    
    Returns:
        List of (start, end) tuples representing segment boundaries
    """
    if proj.size == 0:
        return []
    
    # Calculate threshold
    max_val = np.max(proj)
    if max_val == 0:
        return []
    
    threshold = max_val * threshold_frac
    
    # Find regions above threshold
    above_threshold = proj > threshold
    
    segments = []
    in_segment = False
    start = 0
    
    for i in range(len(above_threshold)):
        if above_threshold[i] and not in_segment:
            # Start of new segment
            start = i
            in_segment = True
        elif not above_threshold[i] and in_segment:
            # End of segment
            end = i
            if end - start >= min_width:
                segments.append((start, end))
            in_segment = False
    
    # Handle case where segment extends to end
    if in_segment:
        end = len(above_threshold)
        if end - start >= min_width:
            segments.append((start, end))
    
    return segments


def _save_table_debug_visualization(img_bgr: np.ndarray, tables: List[Dict]) -> None:
    """
    Save debug visualization of detected tables if DEBUG=true.
    
    Args:
        img_bgr: Original BGR image
        tables: List of detected table dictionaries
    """
    debug_enabled = os.environ.get('DEBUG', '').lower() == 'true'
    
    if not debug_enabled or not tables:
        return
    
    try:
        # Create visualization image
        vis_img = img_bgr.copy()
        
        for idx, table in enumerate(tables):
            x, y, w, h = table['bbox']
            
            # Draw bounding box
            cv2.rectangle(vis_img, (x, y), (x + w, y + h), (0, 255, 0), 3)
            
            # Add label
            label = f"Table {idx + 1}"
            cv2.putText(
                vis_img,
                label,
                (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )
            
            # Segment into rows and draw row lines
            table_mask = table['table_mask']
            segments = segment_table_into_rows_and_cols(table_mask)
            
            for row_start, row_end in segments['rows']:
                # Draw row separator lines (in table coordinates)
                cv2.line(
                    vis_img,
                    (x, y + row_start),
                    (x + w, y + row_start),
                    (255, 0, 0),
                    1
                )
        
        # Save visualization
        os.makedirs('/tmp', exist_ok=True)
        output_path = f"/tmp/table_debug_{len(tables)}_tables.png"
        cv2.imwrite(output_path, vis_img)
        print(f"Table debug visualization saved: {output_path}")
        
    except Exception as e:
        print(f"Warning: Failed to save debug visualization: {str(e)}")


def test_segment_function():
    """
    Test the row/column segmentation function with a sample mask.
    """
    print("Testing table segmentation...")
    
    # Create a simple test mask with table structure
    # Simulate a 100x100 table with horizontal and vertical lines
    mask = np.zeros((100, 100), dtype=np.uint8)
    
    # Add horizontal lines (rows)
    mask[10:12, :] = 255  # Row separator
    mask[30:32, :] = 255  # Row separator
    mask[50:52, :] = 255  # Row separator
    mask[70:72, :] = 255  # Row separator
    mask[90:92, :] = 255  # Row separator
    
    # Add vertical lines (columns)
    mask[:, 20:22] = 255  # Column separator
    mask[:, 40:42] = 255  # Column separator
    mask[:, 60:62] = 255  # Column separator
    mask[:, 80:82] = 255  # Column separator
    
    print(f"Test mask shape: {mask.shape}")
    print(f"Non-zero pixels: {np.count_nonzero(mask)}")
    
    # Segment the table
    segments = segment_table_into_rows_and_cols(mask, min_row_height=5, min_col_width=5)
    
    print(f"\nDetected {len(segments['rows'])} rows:")
    for i, (start, end) in enumerate(segments['rows']):
        print(f"  Row {i + 1}: lines {start}-{end} (height: {end - start})")
    
    print(f"\nDetected {len(segments['cols'])} columns:")
    for i, (start, end) in enumerate(segments['cols']):
        print(f"  Column {i + 1}: lines {start}-{end} (width: {end - start})")
    
    print("\nTest complete!")


if __name__ == "__main__":
    test_segment_function()
