"""
PDF generation service for receipts
"""
import io
import os
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import VerticalBarChart
from django.http import HttpResponse
from django.conf import settings
from django.core.files.base import ContentFile


class ReceiptPDFService:
    """Service for generating PDF receipts"""
    
    def __init__(self):
        self.page_size = A4
        self.margin = 0.75 * inch
        
    def generate_receipt_pdf(self, order, receipt, download=False):
        """
        Generate PDF receipt for an order
        Returns HttpResponse with PDF content
        """
        # Create a file-like buffer to receive PDF data
        buffer = io.BytesIO()
        
        # Create the PDF object, using the buffer as its "file"
        doc = SimpleDocTemplate(
            buffer,
            pagesize=self.page_size,
            rightMargin=self.margin,
            leftMargin=self.margin,
            topMargin=self.margin,
            bottomMargin=self.margin
        )
        
        # Container for the 'Flowable' objects
        elements = []
        
        # Get system configuration
        from system_settings.models import SystemConfiguration
        config = SystemConfiguration.get_config()
        
        # Define styles
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#2c3e50')
        )
        
        company_style = ParagraphStyle(
            'CompanyStyle',
            parent=styles['Normal'],
            fontSize=16,
            alignment=TA_CENTER,
            spaceAfter=6
        )
        
        receipt_title_style = ParagraphStyle(
            'ReceiptTitle',
            parent=styles['Heading2'],
            fontSize=18,
            spaceAfter=20,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#34495e')
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=6
        )
        
        bold_style = ParagraphStyle(
            'CustomBold',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=6,
            fontName='Helvetica-Bold'
        )
        
        # Company header
        company_name = config.company_name or "A&F Laundry Services"
        elements.append(Paragraph(company_name, title_style))
        
        if config.company_address:
            elements.append(Paragraph(config.company_address, company_style))
        
        contact_info = []
        if config.company_phone:
            contact_info.append(f"Phone: {config.company_phone}")
        if config.company_email:
            contact_info.append(f"Email: {config.company_email}")
        
        if contact_info:
            elements.append(Paragraph(" | ".join(contact_info), company_style))
        
        elements.append(Spacer(1, 20))
        
        # Receipt title
        elements.append(Paragraph("RECEIPT", receipt_title_style))
        
        # Receipt and order information
        info_data = [
            ['Receipt Number:', receipt.receipt_number],
            ['Order Number:', order.order_number],
            ['Date:', order.created_at.strftime('%B %d, %Y at %I:%M %p')],
            ['Customer:', order.customer.name],
            ['Status:', order.get_status_display()],
        ]
        
        if order.customer.phone:
            info_data.append(['Phone:', order.customer.phone])
        
        if order.expected_completion:
            info_data.append(['Expected Completion:', order.expected_completion.strftime('%B %d, %Y at %I:%M %p')])
        
        info_table = Table(info_data, colWidths=[2*inch, 4*inch])
        info_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        elements.append(info_table)
        elements.append(Spacer(1, 20))
        
        # Order items header
        elements.append(Paragraph("ORDER DETAILS", bold_style))
        elements.append(Spacer(1, 10))
        
        # Items table
        items_data = [['Service', 'Pieces', 'Unit Price', 'Total']]
        
        total_pieces = 0
        for line in order.lines.all():
            unit_price = line.line_total / line.pieces if line.pieces > 0 else 0
            items_data.append([
                line.service.name,
                str(line.pieces),
                f"{config.currency_symbol}{unit_price:.2f}",
                f"{config.currency_symbol}{line.line_total:.2f}"
            ])
            total_pieces += line.pieces
        
        items_table = Table(items_data, colWidths=[3*inch, 1*inch, 1.5*inch, 1.5*inch])
        items_table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            
            # Data rows
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            
            # Grid
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            
            # Alternating row colors
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ]))
        
        elements.append(items_table)
        elements.append(Spacer(1, 20))
        
        # Summary
        summary_data = [
            ['Total Pieces:', str(total_pieces)],
            ['Subtotal:', f"{config.currency_symbol}{order.subtotal:.2f}"],
        ]
        
        if order.discount_amount and order.discount_amount > 0:
            summary_data.append(['Discount:', f"-{config.currency_symbol}{order.discount_amount:.2f}"])
        
        summary_data.extend([
            ['', ''],  # Empty row for spacing
            ['TOTAL:', f"{config.currency_symbol}{order.total_amount:.2f}"],
            ['Payment Method:', order.payment_method.name],
        ])
        
        summary_table = Table(summary_data, colWidths=[4*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -2), 'Helvetica'),
            ('FONTNAME', (0, -2), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -3), 11),
            ('FONTSIZE', (0, -2), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, -2), (-1, -1), 10),
            ('LINEABOVE', (0, -2), (-1, -2), 2, colors.black),
        ]))
        
        elements.append(summary_table)
        
        # Notes and special instructions
        if order.notes or order.special_instructions:
            elements.append(Spacer(1, 20))
            
            if order.notes:
                elements.append(Paragraph("<b>Notes:</b>", bold_style))
                elements.append(Paragraph(order.notes, normal_style))
                
            if order.special_instructions:
                elements.append(Paragraph("<b>Special Instructions:</b>", bold_style))
                elements.append(Paragraph(order.special_instructions, normal_style))
        
        # Footer
        elements.append(Spacer(1, 30))
        
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=10,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#7f8c8d')
        )
        
        elements.append(Paragraph("Thank you for your business!", footer_style))
        elements.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", footer_style))
        
        # Build PDF
        doc.build(elements)
        
        # Get the value of the BytesIO buffer and return it as HttpResponse
        buffer.seek(0)
        pdf_data = buffer.getvalue()
        buffer.close()
        
        # Create response
        filename = f"receipt_{receipt.receipt_number}_{order.order_number}.pdf"
        
        if download:
            response = HttpResponse(pdf_data, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
        else:
            response = HttpResponse(pdf_data, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="{filename}"'
        
        return response
    
    def generate_receipt_pdf_bytes(self, order, receipt):
        """
        Generate PDF receipt and return bytes for WhatsApp sharing
        """
        # Create a file-like buffer to receive PDF data
        buffer = io.BytesIO()
        
        # Create the PDF object, using the buffer as its "file"
        doc = SimpleDocTemplate(
            buffer,
            pagesize=self.page_size,
            rightMargin=self.margin,
            leftMargin=self.margin,
            topMargin=self.margin,
            bottomMargin=self.margin
        )
        
        # Container for the 'Flowable' objects
        elements = []
        
        # Get system configuration
        from system_settings.models import SystemConfiguration
        config = SystemConfiguration.get_config()
        
        # Define styles (simplified for smaller PDF)
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=20,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#2c3e50')
        )
        
        # Build simplified PDF content
        company_name = config.company_name or "A&F Laundry Services"
        elements.append(Paragraph(company_name, title_style))
        elements.append(Paragraph(f"Receipt: {receipt.receipt_number}", styles['Heading2']))
        elements.append(Paragraph(f"Order: {order.order_number}", styles['Normal']))
        elements.append(Paragraph(f"Customer: {order.customer.name}", styles['Normal']))
        elements.append(Paragraph(f"Total: {config.currency_symbol}{order.total_amount:.2f}", styles['Heading3']))
        
        # Build PDF
        doc.build(elements)
        
        # Get the PDF data
        buffer.seek(0)
        pdf_bytes = buffer.read()
        buffer.close()
        
        return pdf_bytes
    
    def generate_barcode_image(self, barcode_data):
        """
        Generate a barcode image for the receipt
        """
        # Create a barcode drawing
        barcode_width = 200
        barcode_height = 100
        
        drawing = Drawing(barcode_width, barcode_height)
        barcode = VerticalBarChart()
        barcode.data = [[int(x) for x in barcode_data.split('-')]]
        barcode.width = barcode_width
        barcode.height = barcode_height
        barcode.x = 0
        barcode.y = 0
        
        drawing.add(barcode)
        
        # Save to a BytesIO stream
        buffer = io.BytesIO()
        renderPDF.drawToString(drawing, buffer)
        buffer.seek(0)
        
        return buffer.getvalue()
    
    def add_image_to_pdf(self, pdf_buffer, image_data, x, y, width, height):
        """
        Add an image to the PDF at the specified position
        """
        from reportlab.pdfgen import canvas
        
        # Create a temporary file for the image
        temp_image_file = os.path.join(settings.MEDIA_ROOT, 'temp_image.jpg')
        
        # Save the image data to the temporary file
        with open(temp_image_file, 'wb') as f:
            f.write(image_data)
        
        # Create a PDF canvas from the buffer
        pdf_canvas = canvas.Canvas(pdf_buffer)
        
        # Draw the image on the PDF canvas
        pdf_canvas.drawImage(temp_image_file, x, y, width, height)
        
        # Save the PDF canvas
        pdf_canvas.save()
        
        # Remove the temporary image file
        os.remove(temp_image_file)
    
    def generate_receipt_image(self, order, receipt, width=800, height=1200):
        """
        Generate a receipt image (PNG) for WhatsApp sharing
        Returns image bytes
        """
        # Get system configuration
        from system_settings.models import SystemConfiguration
        config = SystemConfiguration.get_config()
        
        # Create image
        img = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(img)
        
        # Define fonts (fallback to default if custom fonts not available)
        try:
            title_font = ImageFont.truetype('/System/Library/Fonts/Arial Bold.ttf', 32)
            header_font = ImageFont.truetype('/System/Library/Fonts/Arial Bold.ttf', 24)
            normal_font = ImageFont.truetype('/System/Library/Fonts/Arial.ttf', 18)
            small_font = ImageFont.truetype('/System/Library/Fonts/Arial.ttf', 14)
        except:
            title_font = ImageFont.load_default()
            header_font = ImageFont.load_default()
            normal_font = ImageFont.load_default()
            small_font = ImageFont.load_default()
        
        # Colors
        primary_color = '#2c3e50'
        secondary_color = '#7f8c8d'
        success_color = '#27ae60'
        
        # Starting position
        y_pos = 50
        margin = 50
        
        # Helper function to get text dimensions and center it
        def draw_centered_text(text, y, font, fill):
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            x = (width - text_width) // 2
            draw.text((x, y), text, font=font, fill=fill)
        
        def draw_right_aligned_text(text, y, font, fill):
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            x = width - margin - text_width
            draw.text((x, y), text, font=font, fill=fill)
        
        # Company name and header
        company_name = config.company_name or "A&F Laundry Services"
        draw_centered_text(company_name, y_pos, title_font, primary_color)
        y_pos += 60
        
        # Company info
        if config.company_address:
            draw_centered_text(config.company_address, y_pos, small_font, secondary_color)
            y_pos += 25
        if config.company_phone:
            draw_centered_text(f"Phone: {config.company_phone}", y_pos, small_font, secondary_color)
            y_pos += 25
        if config.company_email:
            draw_centered_text(f"Email: {config.company_email}", y_pos, small_font, secondary_color)
            y_pos += 40
        
        # Receipt title
        draw_centered_text("RECEIPT", y_pos, header_font, primary_color)
        y_pos += 50
        
        # Draw separator line
        draw.line([(margin, y_pos), (width-margin, y_pos)], fill=primary_color, width=2)
        y_pos += 30
        
        # Receipt details
        details = [
            ("Receipt Number:", receipt.receipt_number),
            ("Order Number:", order.order_number),
            ("Date:", order.created_at.strftime("%b %d, %Y %H:%M")),
            ("Customer:", order.customer.name),
        ]
        
        if order.customer.phone:
            details.append(("Phone:", order.customer.phone))
        
        details.extend([
            ("Status:", order.get_status_display()),
        ])
        
        if order.expected_completion:
            details.append(("Expected Completion:", order.expected_completion.strftime("%b %d, %Y %H:%M")))
        
        for label, value in details:
            draw.text((margin, y_pos), label, font=normal_font, fill=primary_color)
            draw_right_aligned_text(str(value), y_pos, normal_font, 'black')
            y_pos += 30
        
        y_pos += 20
        
        # Order details header
        draw_centered_text("ORDER DETAILS", y_pos, header_font, primary_color)
        y_pos += 40
        
        # Draw separator line
        draw.line([(margin, y_pos), (width-margin, y_pos)], fill=primary_color, width=2)
        y_pos += 20
        
        # Order lines
        from orders.models import OrderLine
        lines = OrderLine.objects.filter(order=order)
        
        for line in lines:
            # Service name
            draw.text((margin, y_pos), line.service.name, font=normal_font, fill=primary_color)
            y_pos += 25
            
            # Pieces and price
            pieces_text = f"{line.pieces} piece{'s' if line.pieces != 1 else ''}"
            draw.text((margin + 20, y_pos), pieces_text, font=small_font, fill=secondary_color)
            
            price_text = f"{config.currency_symbol}{line.line_total:.2f}"
            draw_right_aligned_text(price_text, y_pos, normal_font, success_color)
            y_pos += 40
        
        # Summary
        y_pos += 20
        draw.line([(margin, y_pos), (width-margin, y_pos)], fill=primary_color, width=2)
        y_pos += 30
        
        # Calculate totals
        total_pieces = sum(line.pieces for line in lines)
        
        summary_items = [
            ("Total Pieces:", str(total_pieces)),
            ("Subtotal:", f"{config.currency_symbol}{order.subtotal:.2f}"),
        ]
        
        if order.discount_amount and order.discount_amount > 0:
            summary_items.append(("Discount:", f"-{config.currency_symbol}{order.discount_amount:.2f}"))
        
        for label, value in summary_items:
            draw.text((margin, y_pos), label, font=normal_font, fill='black')
            draw_right_aligned_text(value, y_pos, normal_font, 'black')
            y_pos += 30
        
        # Total (highlighted)
        y_pos += 10
        draw.rectangle([(margin-10, y_pos-5), (width-margin+10, y_pos+35)], outline=primary_color, width=2)
        draw.text((margin, y_pos+10), "TOTAL:", font=header_font, fill=primary_color)
        total_text = f"{config.currency_symbol}{order.total_amount:.2f}"
        draw_right_aligned_text(total_text, y_pos+10, header_font, success_color)
        y_pos += 60
        
        # Payment method
        draw.text((margin, y_pos), "Payment Method:", font=normal_font, fill='black')
        draw_right_aligned_text(order.payment_method.name, y_pos, normal_font, 'black')
        y_pos += 40
        
        # Notes if any
        if order.notes or order.special_instructions:
            y_pos += 20
            draw_centered_text("NOTES", y_pos, header_font, primary_color)
            y_pos += 30
            
            if order.notes:
                draw.text((margin, y_pos), "Notes:", font=normal_font, fill=primary_color)
                y_pos += 25
                # Wrap text for notes
                note_lines = self._wrap_text(order.notes, normal_font, width - 2*margin)
                for line in note_lines:
                    draw.text((margin, y_pos), line, font=small_font, fill='black')
                    y_pos += 20
                y_pos += 10
            
            if order.special_instructions:
                draw.text((margin, y_pos), "Special Instructions:", font=normal_font, fill=primary_color)
                y_pos += 25
                instruction_lines = self._wrap_text(order.special_instructions, normal_font, width - 2*margin)
                for line in instruction_lines:
                    draw.text((margin, y_pos), line, font=small_font, fill='black')
                    y_pos += 20
        
        # Footer
        y_pos = height - 100
        draw_centered_text("Thank you for your business!", y_pos, header_font, primary_color)
        y_pos += 30
        
        generated_text = f"Generated: {receipt.generated_at.strftime('%b %d, %Y %H:%M')}"
        draw_centered_text(generated_text, y_pos, small_font, secondary_color)
        
        # Convert to bytes
        buffer = io.BytesIO()
        img.save(buffer, format='PNG', quality=95, optimize=True)
        buffer.seek(0)
        return buffer.getvalue()
    
    def _wrap_text(self, text, font, max_width):
        """Helper method to wrap text for image generation"""
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            # For simplicity, estimate width (this could be improved with actual text measurement)
            if len(test_line) * 8 < max_width:  # Rough estimate
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines
