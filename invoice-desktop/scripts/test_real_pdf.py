# -*- coding: utf-8 -*-
"""用真实样例发票 PDF 测试加载 + 排版 + 渲染，输出 PNG 供人工检查。"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)

from app.core.pdf_engine import load_invoices
from app.core.layout import layout_pages, render_page

SAMPLE = r"D:\PycharmProjects\dzfp\样例发票.pdf"
SAMPLE2 = r"D:\PycharmProjects\dzfp\样例发票(1).pdf"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)

paths = [p for p in (SAMPLE, SAMPLE2) if os.path.exists(p)]
invoices, errors = load_invoices(paths)
print(f"加载 {len(paths)} 个 PDF → 发票 {len(invoices)} 张, 错误 {errors}")

for i, inv in enumerate(invoices):
    print(f"  发票{i}: {inv.name} {inv.pixmap.width()}x{inv.pixmap.height()} aspect={inv.aspect:.3f}")

pages = layout_pages(invoices, per_page=2)
for pg in pages:
    img = render_page(pg, dpi=150, show_cutline=True)
    f = os.path.join(OUT, f"page_{pg.index+1}.png")
    img.save(f)
    print(f"  渲染页{pg.index+1} → {f} ({img.width()}x{img.height()})")

print("REAL PDF TEST DONE")