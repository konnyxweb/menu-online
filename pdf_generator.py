import io
import os
import qrcode
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle,
    Image, KeepTogether, NextPageTemplate
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT


def _generate_qr_image_stream(url_text):
    """Genera un código QR en memoria (BytesIO PNG) listo para incrustar en ReportLab."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(url_text or 'http://localhost:5000/')
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0f172a", back_color="#ffffff")
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf


def build_menu_pdf(settings, menu_grouped, base_dir, fallback_url='http://localhost:5000/'):
    """
    Genera un PDF compacto, elegante y listo para imprimir en 2 columnas dinámicas,
    con encabezado del negocio, rubros agrupados, tipografía equilibrada y código QR al cierre.
    """
    buffer = io.BytesIO()
    page_w, page_h = letter  # 612 x 792 pt

    margin_x = 0.45 * inch
    margin_top = 0.42 * inch
    margin_bottom = 0.48 * inch
    col_gap = 0.28 * inch

    usable_w = page_w - (2 * margin_x)
    col_w = (usable_w - col_gap) / 2.0

    # Paleta sobria y legible para impresión de menú
    navy = colors.HexColor('#0f172a')
    accent = colors.HexColor('#0369a1')
    slate = colors.HexColor('#475569')
    light_line = colors.HexColor('#cbd5e1')
    soft_bg = colors.HexColor('#f8fafc')

    styles = getSampleStyleSheet()
    style_title = ParagraphStyle(
        'MenuTitle', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=16, leading=19,
        textColor=navy, alignment=TA_LEFT
    )
    style_tagline = ParagraphStyle(
        'MenuTagline', parent=styles['Normal'],
        fontName='Helvetica-Oblique', fontSize=8.5, leading=11,
        textColor=accent, alignment=TA_LEFT
    )
    style_contact = ParagraphStyle(
        'MenuContact', parent=styles['Normal'],
        fontName='Helvetica', fontSize=7.5, leading=10,
        textColor=slate, alignment=TA_LEFT
    )
    style_cat_title = ParagraphStyle(
        'CatTitle', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=10.5, leading=13,
        textColor=accent, spaceBefore=6, spaceAfter=2,
        keepWithNext=True
    )
    style_cat_desc = ParagraphStyle(
        'CatDesc', parent=styles['Normal'],
        fontName='Helvetica-Oblique', fontSize=7.3, leading=9.5,
        textColor=slate, spaceAfter=4,
        keepWithNext=True
    )
    style_prod_name = ParagraphStyle(
        'ProdName', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=8.7, leading=10.5,
        textColor=navy
    )
    style_prod_price = ParagraphStyle(
        'ProdPrice', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=8.7, leading=10.5,
        textColor=navy, alignment=TA_RIGHT
    )
    style_prod_desc = ParagraphStyle(
        'ProdDesc', parent=styles['Normal'],
        fontName='Helvetica', fontSize=7.4, leading=9.2,
        textColor=slate
    )
    style_qr_title = ParagraphStyle(
        'QrTitle', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=8.5, leading=11,
        textColor=navy
    )
    style_qr_note = ParagraphStyle(
        'QrNote', parent=styles['Normal'],
        fontName='Helvetica', fontSize=7.3, leading=9.5,
        textColor=slate
    )

    # Preparar datos del negocio
    rest_name = settings.get('restaurant_name') or 'Menú Online'
    tagline = settings.get('tagline') or ''
    phone = settings.get('phone') or ''
    address = settings.get('address') or ''
    hours = settings.get('hours') or ''
    instagram = settings.get('instagram') or ''
    currency = settings.get('currency_symbol') or '$'
    public_url = (settings.get('public_url') or '').strip() or fallback_url
    footer_note = settings.get('pdf_footer_note') or 'Escanea el código QR para consultar nuestro menú digital actualizado.'

    logo_rel = (settings.get('logo_path') or '').lstrip('/')
    logo_abs = os.path.join(base_dir, logo_rel) if logo_rel else ''
    has_logo = bool(logo_abs and os.path.isfile(logo_abs))

    header_height = 1.05 * inch if has_logo else 0.85 * inch

    def draw_first_page(canvas, doc):
        canvas.saveState()
        top_y = page_h - margin_top

        text_x = margin_x
        if has_logo:
            try:
                logo_size = 0.78 * inch
                canvas.drawImage(
                    logo_abs, margin_x, top_y - logo_size,
                    width=logo_size, height=logo_size,
                    preserveAspectRatio=True, mask='auto'
                )
                text_x = margin_x + logo_size + 12
            except Exception:
                text_x = margin_x

        text_w = (page_w - margin_x) - text_x
        # Dibujar título, eslogan y contacto
        p_name = Paragraph(rest_name.upper(), style_title)
        _, h_name = p_name.wrap(text_w, 40)
        p_name.drawOn(canvas, text_x, top_y - h_name)

        cur_y = top_y - h_name - 2
        if tagline:
            p_tag = Paragraph(tagline, style_tagline)
            _, h_tag = p_tag.wrap(text_w, 30)
            p_tag.drawOn(canvas, text_x, cur_y - h_tag)
            cur_y -= (h_tag + 3)

        contact_parts = [x for x in [
            f"Tel: {phone}" if phone else "",
            address,
            hours,
            f"IG: {instagram}" if instagram else ""
        ] if x]
        if contact_parts:
            p_cont = Paragraph("  ·  ".join(contact_parts), style_contact)
            _, h_cont = p_cont.wrap(text_w, 30)
            p_cont.drawOn(canvas, text_x, cur_y - h_cont)

        # Línea divisoria elegante debajo del encabezado
        line_y = page_h - margin_top - header_height + 6
        canvas.setStrokeColor(accent)
        canvas.setLineWidth(1.2)
        canvas.line(margin_x, line_y, page_w - margin_x, line_y)

        # Pie discreto de página
        _draw_page_footer(canvas, doc)
        canvas.restoreState()

    def draw_later_pages(canvas, doc):
        canvas.saveState()
        top_y = page_h - margin_top
        canvas.setFont('Helvetica-Bold', 9)
        canvas.setFillColor(navy)
        canvas.drawString(margin_x, top_y - 10, rest_name.upper())
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(slate)
        canvas.drawRightString(page_w - margin_x, top_y - 10, "Menú / Carta")
        canvas.setStrokeColor(light_line)
        canvas.setLineWidth(0.75)
        canvas.line(margin_x, top_y - 16, page_w - margin_x, top_y - 16)
        _draw_page_footer(canvas, doc)
        canvas.restoreState()

    def _draw_page_footer(canvas, doc):
        canvas.setFont('Helvetica', 7)
        canvas.setFillColor(slate)
        canvas.drawString(margin_x, 0.25 * inch, f"{rest_name} · {phone}" if phone else rest_name)
        canvas.drawRightString(page_w - margin_x, 0.25 * inch, f"Pág. {doc.page}")

    # Frames de 2 columnas para la primera página y las siguientes
    first_body_h = page_h - margin_top - header_height - margin_bottom
    later_body_h = page_h - margin_top - 0.35 * inch - margin_bottom

    frame_p1_left = Frame(margin_x, margin_bottom, col_w, first_body_h, leftPadding=0, rightPadding=0, topPadding=2, bottomPadding=0, id='p1_l')
    frame_p1_right = Frame(margin_x + col_w + col_gap, margin_bottom, col_w, first_body_h, leftPadding=0, rightPadding=0, topPadding=2, bottomPadding=0, id='p1_r')

    frame_later_left = Frame(margin_x, margin_bottom, col_w, later_body_h, leftPadding=0, rightPadding=0, topPadding=2, bottomPadding=0, id='pl_l')
    frame_later_right = Frame(margin_x + col_w + col_gap, margin_bottom, col_w, later_body_h, leftPadding=0, rightPadding=0, topPadding=2, bottomPadding=0, id='pl_r')

    doc = BaseDocTemplate(buffer, pagesize=letter, title=f"Menú - {rest_name}")
    doc.addPageTemplates([
        PageTemplate(id='FirstPage', frames=[frame_p1_left, frame_p1_right], onPage=draw_first_page),
        PageTemplate(id='LaterPages', frames=[frame_later_left, frame_later_right], onPage=draw_later_pages)
    ])

    story = [NextPageTemplate('LaterPages')]

    for cat in menu_grouped:
        cat_name = cat.get('name', 'Categoría')
        cat_desc = cat.get('description', '')
        products = cat.get('products', [])
        if not products:
            continue

        # Encabezado del rubro con línea sutil
        cat_header_table = Table(
            [[Paragraph(cat_name.upper(), style_cat_title)]],
            colWidths=[col_w]
        )
        cat_header_table.setStyle(TableStyle([
            ('LINEBELOW', (0, 0), (-1, -1), 0.9, accent),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        story.append(cat_header_table)

        if cat_desc:
            story.append(Paragraph(cat_desc, style_cat_desc))
        else:
            story.append(Spacer(1, 3))

        for p in products:
            pname = p.get('name', '')
            pdesc = p.get('description', '')
            pprice = float(p.get('price') or 0.0)
            price_str = f"{currency}{pprice:,.2f}"

            row_table = Table(
                [[Paragraph(pname, style_prod_name), Paragraph(price_str, style_prod_price)]],
                colWidths=[col_w * 0.74, col_w * 0.26]
            )
            row_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ]))

            item_elements = [row_table]
            if pdesc:
                item_elements.append(Paragraph(pdesc, style_prod_desc))
            item_elements.append(Spacer(1, 4))

            story.append(KeepTogether(item_elements))

        story.append(Spacer(1, 6))

    # Bloque de Cierre con Código QR al final del menú
    qr_custom_rel = (settings.get('qr_custom_path') or '').lstrip('/')
    qr_custom_abs = os.path.join(base_dir, qr_custom_rel) if qr_custom_rel else ''
    if qr_custom_abs and os.path.isfile(qr_custom_abs):
        qr_img = Image(qr_custom_abs, width=0.82 * inch, height=0.82 * inch)
    else:
        qr_stream = _generate_qr_image_stream(public_url)
        qr_img = Image(qr_stream, width=0.82 * inch, height=0.82 * inch)

    qr_text_block = [
        Paragraph("MENÚ DIGITAL ONLINE", style_qr_title),
        Spacer(1, 2),
        Paragraph(footer_note, style_qr_note),
        Spacer(1, 2),
        Paragraph(f"<b>Web:</b> {public_url}", style_qr_note),
    ]
    qr_card = Table(
        [[qr_img, qr_text_block]],
        colWidths=[0.9 * inch, col_w - 0.9 * inch - 8]
    )
    qr_card.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), soft_bg),
        ('BOX', (0, 0), (-1, -1), 0.75, light_line),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(Spacer(1, 8))
    story.append(KeepTogether([qr_card]))

    doc.build(story)
    buffer.seek(0)
    return buffer
