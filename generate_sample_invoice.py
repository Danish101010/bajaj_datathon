"""
Generate a sample invoice PDF for testing the extraction pipeline.

This script creates a realistic invoice PDF with tables, line items,
and various text elements to test OCR and extraction capabilities.
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
import os


def create_sample_invoice(filename="sample_invoice.pdf"):
    """
    Create a sample invoice PDF with realistic structure.
    
    Args:
        filename: Output filename for the PDF
    """
    # Create the PDF document
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch
    )
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#333333'),
        alignment=TA_LEFT
    )
    
    # Company Header
    elements.append(Paragraph("ACME CORPORATION", title_style))
    elements.append(Paragraph("123 Business Street, Suite 100", header_style))
    elements.append(Paragraph("New York, NY 10001", header_style))
    elements.append(Paragraph("Phone: (555) 123-4567 | Email: info@acme.com", header_style))
    elements.append(Spacer(1, 0.3*inch))
    
    # Invoice Title
    invoice_title = ParagraphStyle(
        'InvoiceTitle',
        parent=styles['Heading2'],
        fontSize=18,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=20,
        alignment=TA_CENTER
    )
    elements.append(Paragraph("INVOICE", invoice_title))
    elements.append(Spacer(1, 0.2*inch))
    
    # Invoice Details Table
    invoice_details = [
        ['Invoice Number:', 'INV-2025-001234'],
        ['Invoice Date:', 'November 28, 2025'],
        ['Due Date:', 'December 28, 2025'],
        ['Customer ID:', 'CUST-5678']
    ]
    
    details_table = Table(invoice_details, colWidths=[2*inch, 3*inch])
    details_table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), 'Helvetica', 10),
        ('FONT', (0, 0), (0, -1), 'Helvetica-Bold', 10),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#333333')),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(details_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Bill To Section
    bill_to_style = ParagraphStyle(
        'BillTo',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor('#333333')
    )
    elements.append(Paragraph("<b>Bill To:</b>", bill_to_style))
    elements.append(Paragraph("Tech Solutions Inc.", bill_to_style))
    elements.append(Paragraph("456 Client Avenue", bill_to_style))
    elements.append(Paragraph("Boston, MA 02101", bill_to_style))
    elements.append(Spacer(1, 0.3*inch))
    
    # Line Items Table
    line_items = [
        ['Item', 'Description', 'Qty', 'Rate', 'Amount'],
        ['1', 'Professional Services - Software Development', '40', '$150.00', '$6,000.00'],
        ['2', 'Consulting Services - System Architecture', '20', '$200.00', '$4,000.00'],
        ['3', 'Technical Support - Monthly Package', '1', '$500.00', '$500.00'],
        ['4', 'Cloud Hosting Services', '1', '$250.00', '$250.00'],
        ['5', 'Software License - Enterprise Edition', '5', '$100.00', '$500.00'],
    ]
    
    items_table = Table(
        line_items,
        colWidths=[0.5*inch, 3.5*inch, 0.6*inch, 1*inch, 1.2*inch]
    )
    
    items_table.setStyle(TableStyle([
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 11),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        
        # Data rows
        ('FONT', (0, 1), (-1, -1), 'Helvetica', 10),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#333333')),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Item number
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),    # Description
        ('ALIGN', (2, 1), (2, -1), 'CENTER'),  # Qty
        ('ALIGN', (3, 1), (3, -1), 'RIGHT'),   # Rate
        ('ALIGN', (4, 1), (4, -1), 'RIGHT'),   # Amount
        
        # Borders
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#cccccc')),
        ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#2c3e50')),
        
        # Padding
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        
        # Alternating row colors
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
    ]))
    
    elements.append(items_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Totals Table
    totals = [
        ['Subtotal:', '$11,250.00'],
        ['Tax (8%):', '$900.00'],
        ['Discount:', '-$150.00'],
        ['Total Amount:', '$12,000.00']
    ]
    
    totals_table = Table(totals, colWidths=[4.8*inch, 1.5*inch])
    totals_table.setStyle(TableStyle([
        ('FONT', (0, 0), (0, 2), 'Helvetica', 10),
        ('FONT', (0, 3), (0, 3), 'Helvetica-Bold', 12),
        ('FONT', (1, 0), (1, 2), 'Helvetica', 10),
        ('FONT', (1, 3), (1, 3), 'Helvetica-Bold', 12),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#333333')),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('LINEABOVE', (0, 3), (-1, 3), 2, colors.HexColor('#2c3e50')),
        ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor('#e8f4f8')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    elements.append(totals_table)
    elements.append(Spacer(1, 0.4*inch))
    
    # Payment Terms
    terms_style = ParagraphStyle(
        'Terms',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#666666')
    )
    elements.append(Paragraph("<b>Payment Terms:</b> Net 30 days", terms_style))
    elements.append(Paragraph("<b>Payment Methods:</b> Bank Transfer, Check, Credit Card", terms_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Footer
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#999999'),
        alignment=TA_CENTER
    )
    elements.append(Spacer(1, 0.3*inch))
    elements.append(Paragraph("Thank you for your business!", footer_style))
    elements.append(Paragraph("For questions about this invoice, contact: accounts@acme.com", footer_style))
    
    # Build PDF
    doc.build(elements)
    print(f"✓ Sample invoice created: {filename}")


def create_multi_page_invoice(filename="sample_invoice_multipage.pdf"):
    """
    Create a multi-page invoice for testing pagination.
    """
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Header
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=20, alignment=TA_CENTER)
    elements.append(Paragraph("ACME CORPORATION - DETAILED INVOICE", title_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Many line items to span multiple pages
    line_items = [['Item', 'Description', 'Qty', 'Rate', 'Amount']]
    
    for i in range(1, 51):
        line_items.append([
            str(i),
            f'Product/Service Item {i} - Description',
            '1',
            f'${100 + i * 10}.00',
            f'${100 + i * 10}.00'
        ])
    
    items_table = Table(line_items, colWidths=[0.5*inch, 3.5*inch, 0.6*inch, 1*inch, 1.2*inch])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 10),
        ('FONT', (0, 1), (-1, -1), 'Helvetica', 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN', (2, 0), (4, -1), 'RIGHT'),
    ]))
    
    elements.append(items_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Total
    total_amount = sum(100 + i * 10 for i in range(1, 51))
    totals = [['Grand Total:', f'${total_amount:,.2f}']]
    totals_table = Table(totals, colWidths=[5*inch, 1.3*inch])
    totals_table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), 'Helvetica-Bold', 12),
        ('ALIGN', (0, 0), (0, 0), 'RIGHT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
    ]))
    elements.append(totals_table)
    
    doc.build(elements)
    print(f"✓ Multi-page invoice created: {filename}")


def main():
    """Generate sample invoice PDFs."""
    print("Generating sample invoice PDFs for testing...")
    print("=" * 60)
    
    try:
        # Check if reportlab is installed
        import reportlab
        print(f"Using reportlab version: {reportlab.Version}")
        print()
    except ImportError:
        print("Error: reportlab not installed")
        print("Install with: pip install reportlab")
        return 1
    
    # Generate single-page invoice
    create_sample_invoice("sample_invoice.pdf")
    
    # Generate multi-page invoice
    create_multi_page_invoice("sample_invoice_multipage.pdf")
    
    print()
    print("=" * 60)
    print("✓ Sample PDFs generated successfully!")
    print()
    print("Generated files:")
    print("  1. sample_invoice.pdf (single page, realistic invoice)")
    print("  2. sample_invoice_multipage.pdf (50 items, multi-page)")
    print()
    print("Test with:")
    print("  python preprocess.py sample_invoice.pdf")
    print("  python app.py")
    print("  # Then use the API with these files")
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
