"""
Create a more realistic invoice PDF using an actual image-based approach.
This version creates a raster-based invoice that will work better with OCR.
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_ocr_friendly_invoice(filename="sample_invoice_ocr.pdf"):
    """
    Create an OCR-friendly invoice PDF using PIL to render as raster image.
    """
    # Create a white canvas (letter size at 300 DPI)
    width, height = 2550, 3300
    img = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(img)
    
    # Try to use a system font, fallback to default
    try:
        title_font = ImageFont.truetype("arial.ttf", 80)
        header_font = ImageFont.truetype("arial.ttf", 50)
        text_font = ImageFont.truetype("arial.ttf", 40)
        small_font = ImageFont.truetype("arial.ttf", 35)
    except:
        # Fallback to default font
        title_font = ImageFont.load_default()
        header_font = ImageFont.load_default()
        text_font = ImageFont.load_default()
        small_font = ImageFont.load_default()
    
    y = 150
    
    # Title
    draw.text((width//2, y), "INVOICE", fill='black', font=title_font, anchor='mm')
    y += 120
    
    # Invoice details
    draw.text((200, y), "Invoice #: INV-2025-001", fill='black', font=text_font)
    y += 60
    draw.text((200, y), "Date: November 28, 2025", fill='black', font=text_font)
    y += 60
    draw.text((200, y), "Due Date: December 28, 2025", fill='black', font=text_font)
    y += 120
    
    # Company details
    draw.text((200, y), "ACME Corporation", fill='black', font=header_font)
    y += 60
    draw.text((200, y), "123 Business Street", fill='black', font=text_font)
    y += 50
    draw.text((200, y), "New York, NY 10001", fill='black', font=text_font)
    y += 100
    
    # Table header with heavy border
    table_top = y
    table_left = 200
    table_width = 2150
    row_height = 80
    
    # Draw thick table border (5 pixels)
    for i in range(5):
        draw.rectangle([table_left-i, table_top-i, table_left+table_width+i, table_top+6*row_height+i], outline='black')
    
    # Column positions
    col1_x = table_left + 50
    col2_x = table_left + 1200
    col3_x = table_left + 1600
    col4_x = table_left + 1950
    
    # Header row with thick bottom border
    draw.text((col1_x, table_top + 25), "Description", fill='black', font=header_font)
    draw.text((col2_x, table_top + 25), "Quantity", fill='black', font=header_font)
    draw.text((col3_x, table_top + 25), "Unit Price", fill='black', font=header_font)
    draw.text((col4_x, table_top + 25), "Amount", fill='black', font=header_font)
    
    # Draw thick horizontal line after header
    for i in range(3):
        draw.line([table_left, table_top + row_height + i, table_left + table_width, table_top + row_height + i], fill='black', width=1)
    
    # Draw thick vertical lines for columns
    for i in range(3):
        draw.line([col2_x - 50 + i, table_top, col2_x - 50 + i, table_top + 6*row_height], fill='black', width=1)
        draw.line([col3_x - 50 + i, table_top, col3_x - 50 + i, table_top + 6*row_height], fill='black', width=1)
        draw.line([col4_x - 50 + i, table_top, col4_x - 50 + i, table_top + 6*row_height], fill='black', width=1)
    
    # Data rows
    items = [
        ("Professional Services - Consulting", "40", "125.00", "5000.00"),
        ("Software License - Annual", "5", "450.00", "2250.00"),
        ("Hardware - Server Equipment", "2", "650.00", "1300.00"),
        ("Training Services", "8", "95.50", "764.00"),
        ("Support Package - Premium", "12", "56.50", "678.50"),
    ]
    
    current_y = table_top + row_height
    for desc, qty, unit_price, amount in items:
        current_y += row_height
        draw.text((col1_x, current_y + 15), desc, fill='black', font=text_font)
        draw.text((col2_x, current_y + 15), qty, fill='black', font=text_font)
        draw.text((col3_x, current_y + 15), f"${unit_price}", fill='black', font=text_font)
        draw.text((col4_x, current_y + 15), f"${amount}", fill='black', font=text_font)
        
        # Draw horizontal line after each row
        for i in range(2):
            draw.line([table_left, current_y + row_height + i, table_left + table_width, current_y + row_height + i], fill='black', width=1)
    
    # Total row with bold border
    current_y += row_height
    for i in range(4):
        draw.line([table_left, current_y + i, table_left + table_width, current_y + i], fill='black', width=1)
    
    draw.text((col3_x, current_y + 20), "TOTAL:", fill='black', font=header_font)
    draw.text((col4_x, current_y + 20), "$9,992.50", fill='black', font=header_font)
    
    # Footer
    y = current_y + 180
    draw.text((200, y), "Payment Terms: Net 30 days", fill='black', font=text_font)
    y += 60
    draw.text((200, y), "Thank you for your business!", fill='black', font=text_font)
    
    # Save as PDF
    img.save(filename, "PDF", resolution=300.0, quality=95)
    print(f"Created: {filename}")
    print(f"  Total: $9,992.50")
    print(f"  Items: 5 line items")
    print(f"  Size: {os.path.getsize(filename):,} bytes")
    return os.path.abspath(filename)


if __name__ == "__main__":
    print("=" * 70)
    print("GENERATING OCR-FRIENDLY INVOICE PDF")
    print("=" * 70)
    print()
    
    path = create_ocr_friendly_invoice()
    
    print()
    print("=" * 70)
    print("Test this PDF with:")
    print(f"  python preprocess.py {os.path.basename(path)}")
    print(f"  python test_full_extraction.py  # (edit to use this file)")
    print("=" * 70)
