# -*- coding: utf-8 -*-
"""GUI 无窗口冒烟测试：用 offscreen 平台实例化主窗口并加载发票预览。

用法: QT_QPA_PLATFORM=offscreen python scripts/ui_smoke_test.py
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QUrl
from PySide6.QtGui import QColor, QImage, QGuiApplication, QPixmap
from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)

from app.core.invoice import Invoice
from app.gui.main_window import MainWindow

win = MainWindow()

# 模拟两张发票
img = QImage(800, 1100, QImage.Format_RGB32)
img.fill(QColor("lightgray"))
inv = Invoice("模拟发票.png", QPixmap.fromImage(img))
img2 = QImage(800, 1100, QImage.Format_RGB32)
img2.fill(QColor("lightgray"))
inv2 = Invoice("模拟发票2.png", QPixmap.fromImage(img2))
win.invoices.append(inv)
win.invoices.append(inv2)

print("窗口创建 OK")
print("发票数:", len(win.invoices))

win._rebuild_preview()
print("预览页数:", win.preview_layout.count(), "| 打印按钮启用:", win.print_btn.isEnabled())

# 改 1 张模式
win.rb1.setChecked(True)
win._rebuild_preview()
print("1张模式预览 OK")

# 等待后台更新检查线程结束（否则退出时 QThread destroyed crash）
# 更新检查带 20s 网络超时，等 30s 兜底
if win._update_thread is not None and win._update_thread.isRunning():
    win._update_thread.wait(30000)
app.processEvents()
print("UI SMOKE OK")