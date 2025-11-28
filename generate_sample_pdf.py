"""
Generate a sample invoice PDF for testing the extraction pipeline.

This creates a simple invoice PDF with a table structure that can be used
to test all the modules without needing to download external PDFs.
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
import os


def create_sample_invoice(filename="sample_invoice.pdf"):
    """
    Create a sample invoice PDF with table structure.
    
    Args:
        filename: Output filename for the PDF
    """
    # Create PDF
    doc = SimpleDocTemplate(filename, pagesize=letter)
    story = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#2c3e50'),
        alignment=TA_CENTER,
        spaceAfter=30
    )
    
    # Header
    title = Paragraph("INVOICE", title_style)
    story.append(title)
    story.append(Spacer(1, 0.3*inch))
    
    # Invoice Info
    info_style = styles['Normal']
    invoice_info = [
        ["Invoice #:", "INV-2025-001"],
        ["Date:", "November 28, 2025"],
        ["Due Date:", "December 28, 2025"],
    ]
    
    info_table = Table(info_info, colWidths=[2*inch, 3*inch])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.grey),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.5*inch))
    
    # Bill To
    bill_to = Paragraph("<b>Bill To:</b><br/>Acme Corporation<br/>123 Business Street<br/>City, State 12345", info_style)
    story.append(bill_to)
    story.append(Spacer(1, 0.5*inch))
    
    # Line Items Table
    data = [
        ['Description', 'Quantity', 'Unit Price', 'Amount'],
        ['Professional Services - Consulting', '10', '$150.00', '$1,500.00'],
        ['Software Development Services', '20', '$175.00', '$3,500.00'],
        ['Technical Support - Monthly', '1', '$500.00', '$500.00'],
        ['Project Management', '15', '$125.00', '$1,875.00'],
        ['Quality Assurance Testing', '8', '$100.00', '$800.00'],
    ]
    
    # Create table
    table = Table(data, colWidths=[3.5*inch, 1*inch, 1.2*inch, 1.2*inch])
    
    # Style the table
    table.setStyle(TableStyle([
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        
        # Data rows
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
        ('ALIGN', (3, 1), (3, -1), 'RIGHT'),
        
        # Grid
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        
        # Alternating row colors
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#ecf0f1')]),
    ]))
    
    story.append(table)
    story.append(Spacer(1, 0.5*inch))
    
    # Totals
    totals_data = [
        ['Subtotal:', '$8,175.00'],
        ['Tax (10%):', '$817.50'],
        ['Total Amount:', '$8,992.50'],
    ]
    
    totals_table = Table(totals_data, colWidths=[5*inch, 1.5*inch])
    totals_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -2), 'Helvetica'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor('#2c3e50')),
        ('LINEABOVE', (1, -1), (1, -1), 2, colors.HexColor('#2c3e50')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    story.append(totals_table)
    story.append(Spacer(1, 0.5*inch))
    
    # Footer
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.grey,
        alignment=TA_CENTER
    )
    footer = Paragraph("Thank you for your business!<br/>Payment terms: Net 30 days", footer_style)
    story.append(footer)
    
    # Build PDF
    doc.build(story)
    print(f"✓ Created sample invoice: {filename}")
    return filename


def create_multi_page_invoice(filename="sample_invoice_multipage.pdf"):
    """Create a multi-page invoice for testing."""
    doc = SimpleDocTemplate(filename, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()
    
    # Page 1
    title = Paragraph("INVOICE - Page 1", styles['Heading1'])
    story.append(title)
    story.append(Spacer(1, 0.3*inch))
    
    # First page items
    data1 = [
        ['Description', 'Quantity', 'Unit Price', 'Amount'],
        ['Item 1 - Product A', '5', '$100.00', '$500.00'],
        ['Item 2 - Product B', '3', '$150.00', '$450.00'],
        ['Item 3 - Product C', '2', '$200.00', '$400.00'],
    ]
    
    table1 = Table(data1, colWidths=[3.5*inch, 1*inch, 1.2*inch, 1.2*inch])
    table1.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ]))
    story.append(table1)
    
    # Page break
    from reportlab.platypus import PageBreak
    story.append(PageBreak())
    
    # Page 2
    title2 = Paragraph("INVOICE - Page 2 (Continued)", styles['Heading1'])
    story.append(title2)
    story.append(Spacer(1, 0.3*inch))
    
    data2 = [
        ['Description', 'Quantity', 'Unit Price', 'Amount'],
        ['Item 4 - Service D', '10', '$75.00', '$750.00'],
        ['Item 5 - Service E', '8', '$125.00', '$1,000.00'],
    ]
    
    table2 = Table(data2, colWidths=[3.5*inch, 1*inch, 1.2*inch, 1.2*inch])
    table2.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ]))
    story.append(table2)
    story.append(Spacer(1, 0.5*inch))
    
    # Total
    total = Paragraph("<b>Grand Total: $3,100.00</b>", styles['Normal'])
    story.append(total)
    
    doc.build(story)
    print(f"✓ Created multi-page invoice: {filename}")
    return filename


def main():
    """Generate sample PDFs."""
    print("Generating sample invoice PDFs...")
    print("=" * 60)
    
    # Check if reportlab is installed
    try:
        import reportlab
    except ImportError:
        print("✗ reportlab not installed")
        print("\nInstalling reportlab...")
        import subprocess
        subprocess.check_call(['pip', 'install', 'reportlab'])
        print("✓ reportlab installed")
    
    # Generate single-page invoice
    file1 = create_sample_invoice("sample_invoice.pdf")
    
    # Generate multi-page invoice
    file2 = create_multi_page_invoice("sample_invoice_multipage.pdf")
    
    print("\n" + "=" * 60)
    print("✓ Sample PDFs created successfully!")
    print("\nYou can now test with:")
    print(f"  python preprocess.py {file1}")
    print(f"  python preprocess.py {file2}")
    print("\nOr test the full API with these files.")
    
    # Show absolute paths
    import os
    print("\nFull paths:")
    print(f"  {os.path.abspath(file1)}")
    print(f"  {os.path.abspath(file2)}")


if __name__ == "__main__":
    main()
