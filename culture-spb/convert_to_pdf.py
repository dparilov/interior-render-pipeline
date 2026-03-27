#!/usr/bin/env python3
"""Convert SPEC.md to PDF using reportlab."""
import subprocess, sys

# Install reportlab
subprocess.check_call([sys.executable, '-m', 'ensurepip', '--default-pip'], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'reportlab', '-q'])

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import re, os

# Try to register a font that supports Cyrillic
font_paths = [
    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
    '/usr/share/fonts/truetype/freefont/FreeSans.ttf',
]
font_bold_paths = [
    '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
    '/usr/share/fonts/truetype/freefont/FreeSansBold.ttf',
]

font_name = 'Helvetica'
font_bold = 'Helvetica-Bold'

for fp, fbp in zip(font_paths, font_bold_paths):
    if os.path.exists(fp):
        pdfmetrics.registerFont(TTFont('CyrFont', fp))
        font_name = 'CyrFont'
        if os.path.exists(fbp):
            pdfmetrics.registerFont(TTFont('CyrFontBold', fbp))
            font_bold = 'CyrFontBold'
        else:
            font_bold = font_name
        break

spec_path = '/home/dima/.openclaw/workspace-dev/culture-spb/SPEC.md'
pdf_path = '/home/dima/.openclaw/workspace-dev/culture-spb/SPEC.pdf'

with open(spec_path, 'r') as f:
    content = f.read()

doc = SimpleDocTemplate(pdf_path, pagesize=A4,
                        leftMargin=20*mm, rightMargin=20*mm,
                        topMargin=15*mm, bottomMargin=15*mm)

styles = getSampleStyleSheet()

styles.add(ParagraphStyle('MyTitle', fontName=font_bold, fontSize=18, spaceAfter=6*mm, alignment=TA_CENTER))
styles.add(ParagraphStyle('MyH1', fontName=font_bold, fontSize=16, spaceBefore=8*mm, spaceAfter=4*mm, textColor=HexColor('#1a1a2e')))
styles.add(ParagraphStyle('MyH2', fontName=font_bold, fontSize=13, spaceBefore=6*mm, spaceAfter=3*mm, textColor=HexColor('#16213e')))
styles.add(ParagraphStyle('MyH3', fontName=font_bold, fontSize=11, spaceBefore=4*mm, spaceAfter=2*mm, textColor=HexColor('#0f3460')))
styles.add(ParagraphStyle('MyBody', fontName=font_name, fontSize=9, leading=13, spaceAfter=2*mm))
styles.add(ParagraphStyle('MyCode', fontName='Courier', fontSize=7.5, leading=10, spaceAfter=2*mm,
                           backColor=HexColor('#f5f5f5'), leftIndent=5*mm, rightIndent=5*mm))
styles.add(ParagraphStyle('MyMeta', fontName=font_name, fontSize=9, alignment=TA_CENTER, textColor=HexColor('#666666'), spaceAfter=4*mm))
styles.add(ParagraphStyle('MyTableCell', fontName=font_name, fontSize=8, leading=10))
styles.add(ParagraphStyle('MyTableHeader', fontName=font_bold, fontSize=8, leading=10))

story = []

lines = content.split('\n')
i = 0
in_code_block = False
code_buffer = []
in_table = False
table_rows = []

def escape_html(text):
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def format_inline(text):
    text = escape_html(text)
    # Bold
    text = re.sub(r'\*\*(.+?)\*\*', rf'<b>\1</b>', text)
    # Italic
    text = re.sub(r'\*(.+?)\*', rf'<i>\1</i>', text)
    # Inline code
    text = re.sub(r'`(.+?)`', rf'<font face="Courier" size="8">\1</font>', text)
    return text

def flush_table():
    if not table_rows:
        return
    # Build reportlab table
    col_count = len(table_rows[0])
    data = []
    for ri, row in enumerate(table_rows):
        style = 'MyTableHeader' if ri == 0 else 'MyTableCell'
        data.append([Paragraph(format_inline(cell.strip()), styles[style]) for cell in row])
    
    t = Table(data, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#e8e8e8')),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#cccccc')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t)
    story.append(Spacer(1, 3*mm))

while i < len(lines):
    line = lines[i]
    
    # Code blocks
    if line.strip().startswith('```'):
        if in_code_block:
            code_text = '<br/>'.join(escape_html(l) for l in code_buffer)
            story.append(Paragraph(code_text, styles['MyCode']))
            code_buffer = []
            in_code_block = False
        else:
            if in_table:
                flush_table()
                table_rows = []
                in_table = False
            in_code_block = True
        i += 1
        continue
    
    if in_code_block:
        code_buffer.append(line)
        i += 1
        continue
    
    # Table rows
    if '|' in line and line.strip().startswith('|'):
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        # Skip separator rows
        if all(re.match(r'^[-:]+$', c) for c in cells):
            i += 1
            continue
        if not in_table:
            in_table = True
            table_rows = []
        table_rows.append(cells)
        i += 1
        continue
    else:
        if in_table:
            flush_table()
            table_rows = []
            in_table = False
    
    stripped = line.strip()
    
    # Empty line
    if not stripped:
        i += 1
        continue
    
    # Headings
    if stripped.startswith('# ') and not stripped.startswith('## '):
        story.append(Paragraph(format_inline(stripped[2:]), styles['MyTitle']))
        i += 1
        continue
    if stripped.startswith('## '):
        story.append(Paragraph(format_inline(stripped[3:]), styles['MyH1']))
        i += 1
        continue
    if stripped.startswith('### '):
        story.append(Paragraph(format_inline(stripped[4:]), styles['MyH2']))
        i += 1
        continue
    if stripped.startswith('#### '):
        story.append(Paragraph(format_inline(stripped[5:]), styles['MyH3']))
        i += 1
        continue
    
    # Horizontal rule
    if stripped == '---':
        story.append(Spacer(1, 3*mm))
        i += 1
        continue
    
    # List items
    if stripped.startswith('- ') or stripped.startswith('* ') or re.match(r'^\d+\.', stripped):
        bullet = '•' if stripped.startswith('-') or stripped.startswith('*') else stripped.split('.')[0] + '.'
        text = re.sub(r'^[-*]\s+', '', stripped)
        text = re.sub(r'^\d+\.\s+', '', text)
        story.append(Paragraph(f'{bullet} {format_inline(text)}', styles['MyBody']))
        i += 1
        continue
    
    # Regular paragraph
    story.append(Paragraph(format_inline(stripped), styles['MyBody']))
    i += 1

if in_table:
    flush_table()

# Build
doc.build(story)
print(f"PDF saved to {pdf_path}")
