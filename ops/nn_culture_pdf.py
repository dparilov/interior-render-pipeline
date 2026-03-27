#!/usr/bin/env python3
"""
Создание PDF с культурными событиями Нижнего Новгорода
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
import os

OUTPUT_PATH = '/home/dima/.openclaw/workspace/NN_Culture_May_2026.pdf'

# Регистрируем шрифт с кириллицей
FONT_PATHS = [
    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
]

def register_fonts():
    if os.path.exists('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'):
        pdfmetrics.registerFont(TTFont('DejaVu', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
        pdfmetrics.registerFont(TTFont('DejaVuBold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
        return 'DejaVu', 'DejaVuBold'
    return 'Helvetica', 'Helvetica-Bold'

def create_pdf():
    font, font_bold = register_fonts()
    
    c = canvas.Canvas(OUTPUT_PATH, pagesize=A4)
    width, height = A4
    
    y = height - 2*cm
    
    # Заголовок
    c.setFont(font_bold, 18)
    c.setFillColor(HexColor('#0078D7'))
    c.drawString(2*cm, y, "Культурные события Нижнего Новгорода")
    y -= 0.8*cm
    c.setFont(font_bold, 14)
    c.drawString(2*cm, y, "16-19 мая 2026")
    y -= 1.5*cm
    
    # Секция: Выставки
    c.setFont(font_bold, 14)
    c.setFillColor(HexColor('#333333'))
    c.drawString(2*cm, y, "🎨 ВЫСТАВКИ")
    y -= 0.8*cm
    
    c.setFont(font_bold, 11)
    c.setFillColor(HexColor('#0078D7'))
    c.drawString(2*cm, y, "Нижегородский государственный художественный музей (НГХМ)")
    y -= 0.5*cm
    
    c.setFont(font, 10)
    c.setFillColor(HexColor('#333333'))
    
    items = [
        "• «Виктор Васнецов. Радость праведных. Религиозная живопись и графика»",
        "• «Готический ампир. Мистические образы старины»",
        "• «МАГИЯ ПРОСТРАНСТВА: Эдуард и Евгений Гороховские»",
        "• Русское искусство первой половины XX века — постоянная экспозиция",
        "📍 Стрелка, дом 21 | Вт-Ср 10:00-18:00, Чт 12:00-20:00, Пт-Вс 11:00-19:00",
    ]
    for item in items:
        c.drawString(2.5*cm, y, item)
        y -= 0.45*cm
    
    y -= 0.5*cm
    c.setFont(font_bold, 11)
    c.setFillColor(HexColor('#0078D7'))
    c.drawString(2*cm, y, "Пакгаузы на Стрелке (Выставочный пакгауз)")
    y -= 0.5*cm
    
    c.setFont(font, 10)
    c.setFillColor(HexColor('#333333'))
    items = [
        "• Культурный центр с выставками НГХМ",
        "• Уникальная архитектура — ажурные металлические конструкции XIX века",
        "📍 ул. Стрелка, 21",
    ]
    for item in items:
        c.drawString(2.5*cm, y, item)
        y -= 0.45*cm
    
    y -= 0.5*cm
    c.setFont(font_bold, 11)
    c.setFillColor(HexColor('#0078D7'))
    c.drawString(2*cm, y, "Галерея Vekarta")
    y -= 0.5*cm
    
    c.setFont(font, 10)
    c.setFillColor(HexColor('#333333'))
    c.drawString(2.5*cm, y, "• «Климт, вдохновлённый Ван Гогом, Моне, Матиссом» — постоянная экспозиция")
    y -= 0.7*cm
    
    c.setFont(font_bold, 11)
    c.setFillColor(HexColor('#0078D7'))
    c.drawString(2*cm, y, "Усадьба Рукавишниковых")
    y -= 0.5*cm
    
    c.setFont(font, 10)
    c.setFillColor(HexColor('#333333'))
    items = [
        "• Экспозиция о Николае I и его роли в истории Нижнего Новгорода",
        "• Интерьеры купеческого палаццо",
        "📍 150-300 ₽",
    ]
    for item in items:
        c.drawString(2.5*cm, y, item)
        y -= 0.45*cm
    
    y -= 0.5*cm
    c.setFont(font_bold, 11)
    c.setFillColor(HexColor('#0078D7'))
    c.drawString(2*cm, y, "Арсенал (центр современного искусства)")
    y -= 0.5*cm
    
    c.setFont(font, 10)
    c.setFillColor(HexColor('#333333'))
    items = [
        "• «Город как графика. Нижний Новгород на картах и гравюрах XVI–XXI веков»",
        "📍 Кремль | Вт-Вс 12:00-20:00",
    ]
    for item in items:
        c.drawString(2.5*cm, y, item)
        y -= 0.45*cm
    
    y -= 0.5*cm
    c.setFont(font_bold, 11)
    c.setFillColor(HexColor('#0078D7'))
    c.drawString(2*cm, y, "Никольская башня Кремля")
    y -= 0.5*cm
    
    c.setFont(font, 10)
    c.setFillColor(HexColor('#333333'))
    c.drawString(2.5*cm, y, "• Выставка о средневековом городе и его быте | 150-250 ₽")
    y -= 1*cm
    
    # Секция: Другие места
    c.setFont(font_bold, 14)
    c.setFillColor(HexColor('#333333'))
    c.drawString(2*cm, y, "🎭 ДРУГИЕ КУЛЬТУРНЫЕ МЕСТА")
    y -= 0.8*cm
    
    c.setFont(font, 10)
    c.setFillColor(HexColor('#333333'))
    items = [
        "• Музей ГАЗ — история Горьковского автозавода (100-250 ₽)",
        "• Музей «Кварки» — интерактивный научный музей (400-500 ₽)",
        "• Музей советского быта — ретро-экспозиция (150-300 ₽)",
    ]
    for item in items:
        c.drawString(2.5*cm, y, item)
        y -= 0.5*cm
    
    y -= 1*cm
    
    # Примечание
    c.setFont(font_bold, 11)
    c.setFillColor(HexColor('#888888'))
    c.drawString(2*cm, y, "⚠️ Рекомендации:")
    y -= 0.5*cm
    
    c.setFont(font, 9)
    items = [
        "Афиши на конкретные даты 16-19 мая пока не опубликованы.",
        "Ближе к дате проверьте:",
        "• afisha.yandex.ru/nizhny-novgorod",
        "• nn.kudago.com",
        "• artmuseumnn.ru",
    ]
    for item in items:
        c.drawString(2.5*cm, y, item)
        y -= 0.4*cm
    
    # Футер
    c.setFont(font, 8)
    c.setFillColor(HexColor('#AAAAAA'))
    c.drawString(2*cm, 1.5*cm, "Подготовлено: 26 марта 2026")
    
    c.save()
    print(f"✅ PDF создан: {OUTPUT_PATH}")

if __name__ == '__main__':
    create_pdf()
