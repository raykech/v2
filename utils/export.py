import tkinter as tk
from tkinter import filedialog, messagebox
import os
from datetime import datetime
import re

try:
    import pandas as pd
except ImportError:
    pd = None

try:
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib import colors
    reportlab_available = True

    # Arial fontunu bulmaya çalış, bulamazsan varsayılanı kullan
    try:
        fonts_path = os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), 'Fonts')
        arial_path = os.path.join(fonts_path, 'arial.ttf')
        arialbd_path = os.path.join(fonts_path, 'arialbd.ttf')

        if os.path.exists(arial_path) and os.path.exists(arialbd_path):
            pdfmetrics.registerFont(TTFont('Arial', arial_path))
            pdfmetrics.registerFont(TTFont('Arial-Bold', arialbd_path))
            FONT_NAME = 'Arial'
        else:
            FONT_NAME = 'Helvetica'
    except Exception:
        FONT_NAME = 'Helvetica'

except ImportError:
    reportlab_available = False

def _export_to_excel(df, file_path):
    if not pd:
        messagebox.showerror("Hata", "Excel'e aktarmak için 'pandas' ve 'openpyxl' kütüphaneleri gereklidir.\nLütfen 'pip install pandas openpyxl' komutu ile kurun.")
        return
    try:
        df.to_excel(file_path, index=False)
        messagebox.showinfo("Başarılı", f"Veri başarıyla '{os.path.basename(file_path)}' dosyasına aktarıldı.")
    except Exception as e:
        messagebox.showerror("Excel Aktarma Hatası", f"Dosya oluşturulurken bir hata oluştu:\n{e}")

def _export_to_pdf(df, file_path, title):
    if not reportlab_available:
        messagebox.showerror("Hata", "PDF'e aktarmak için 'reportlab' kütüphanesi gereklidir.\nLütfen 'pip install reportlab' komutu ile kurun.")
        return

    try:
        doc = SimpleDocTemplate(file_path, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        styles = getSampleStyleSheet()
        
        # Mevcut stilleri eklemek yerine özelliklerini güncelle
        styles.add(ParagraphStyle(name='Header', fontName=FONT_NAME, fontSize=14, alignment=1, spaceAfter=20))
        normal_style = styles['Normal']
        normal_style.fontName = FONT_NAME
        normal_style.fontSize = 9

        elements = [Paragraph(title, styles['Header'])]
        
        data = [df.columns.to_list()] + df.values.tolist()
        
        table = Table(data, repeatRows=1)
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4a69bd")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), FONT_NAME + '-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), FONT_NAME),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ])
        table.setStyle(style)
        
        # Sütun genişliklerini ayarla
        col_widths = [len(str(x)) for x in df.columns]
        for row in df.itertuples(index=False):
            for i, cell in enumerate(row):
                col_widths[i] = max(col_widths[i], len(str(cell)))
        
        # Genişlikleri A4'e sığacak şekilde oranla
        total_width = sum(col_widths)
        page_width = A4[0] - 60 # Kenar boşlukları
        ratio = page_width / total_width if total_width > 0 else 1
        table._argW = [w * ratio * 0.95 for w in col_widths] # Biraz daha boşluk bırak

        elements.append(table)
        doc.build(elements)
        messagebox.showinfo("Başarılı", f"Veri başarıyla '{os.path.basename(file_path)}' dosyasına aktarıldı.")

    except Exception as e:
        messagebox.showerror("PDF Aktarma Hatası", f"Dosya oluşturulurken bir hata oluştu:\n{e}")

def _parse_numeric_value(value):
    """
    Para formatındaki veya binlik ayraçlı sayıları float'a çevirmeye çalışır.
    Başarısız olursa orijinal değeri döndürür.
    """
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        try:
            # "1.234,56 TL" -> 1234.56
            return float(value.replace(" TL", "").replace(".", "").replace(",", "."))
        except (ValueError, TypeError):
            return value # Sayıya çevrilemezse orijinal metni koru
    return value

def export_treeview_data(tree, report_title, format_type):
    if not tree.get_children():
        messagebox.showwarning("Uyarı", "Aktarılacak veri bulunmuyor.", parent=tree)
        return

    columns = [tree.heading(col)["text"] for col in tree["columns"] if tree.column(col, "width") > 0]
    column_ids = [col for col in tree["columns"] if tree.column(col, "width") > 0]
    
    data = []
    for item in tree.get_children():
        values = tree.item(item)['values']
        row_data = {tree["columns"][i]: (values[i] if i < len(values) else "") for i in range(len(tree["columns"]))}
        
        # Excel için sayısal değerleri temizle
        if format_type == 'excel':
            processed_row = [_parse_numeric_value(row_data.get(col_id, "")) for col_id in column_ids]
            data.append(processed_row)
        else: # PDF için formatlı kalsın
            data.append([row_data.get(col_id, "") for col_id in column_ids])

    df = pd.DataFrame(data, columns=columns)

    file_types = [('Excel Dosyası', '*.xlsx')] if format_type == 'excel' else [('PDF Dosyası', '*.pdf')]
    default_ext = '.xlsx' if format_type == 'excel' else '.pdf'
    
    # Otomatik dosya adı oluştur
    s_report_title = re.sub(r'[^\w\s-]', '', report_title).strip().replace(' ', '_')
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    initial_filename = f"{timestamp}_{s_report_title}"

    file_path = filedialog.asksaveasfilename(title=f"{report_title} Olarak Kaydet", initialfile=initial_filename, defaultextension=default_ext, filetypes=file_types)
    if not file_path: return

    if format_type == 'excel':
        _export_to_excel(df, file_path)
    elif format_type == 'pdf':
        _export_to_pdf(df, file_path, report_title)