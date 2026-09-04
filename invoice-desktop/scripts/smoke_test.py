# -*- coding: utf-8 -*-
"""无 GUI 冒烟测试：验证排版 + 渲染引擎可跑。"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# QPixmap/QPainter 等必须在 QGuiApplication 实例存在时才能安全使用
from PySide6.QtGui import QGuiApplication
_app = QGuiApplication(sys.argv)

from PySide6.QtGui import QPixmap, QColor
from app.core.invoice import Invoice
from app.core.layout import layout_pages, render_page, _mm_to_px

pm = QPixmap(800, 1100)
pm.fill(QColor("lightgray"))
inv = Invoice("test.png", pm)
invoices = [inv, inv, inv]

pages = layout_pages(invoices, per_page=2)
assert len(pages) == 2, len(pages)
assert len(pages[0].items) == 2
assert len(pages[1].items) == 1
assert [it.cut_before for it in pages[0].items] == [False, True]

img = render_page(pages[0], dpi=300)
print("pages:", len(pages))
print("page0 items:", len(pages[0].items), "cut_before:", [it.cut_before for it in pages[0].items])
print("render 300dpi image:", img.width(), "x", img.height())
print("mm_to_px(210mm@96):", _mm_to_px(210, 96))
print("SMOKE OK")