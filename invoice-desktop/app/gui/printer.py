# -*- coding: utf-8 -*-
"""打印模块：QPrinter 渲染 A4 页面，按物理尺寸打印。

关键点：QPrinter 在高分辨率模式下以设备像素为单位（1/1200 英寸或物理 DPI），
用 printer.width()/logicalDpiX() 换算 mm，保证 210×297mm 真实尺寸。
"""
from typing import List

from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QMessageBox, QWidget
from PySide6.QtPrintSupport import QPrinter, QPrintDialog

from ..core.invoice import Invoice
from ..core.layout import PAGE_H_MM, PAGE_W_MM, layout_pages, render_page


def print_pages(parent: QWidget, invoices: List[Invoice], per_page: int, show_cutline: bool):
    """弹出打印对话框，将排版结果按 A4 打印。"""
    if not invoices:
        return

    pages = layout_pages(invoices, per_page=per_page)
    if not pages:
        QMessageBox.information(parent, "提示", "没有可打印的发票。")
        return

    printer = QPrinter(QPrinter.HighResolution)
    printer.setPageSize(QPrinter.A4)
    printer.setPageOrientation(QPrinter.Portrait)
    printer.setFullPage(True)
    printer.setColorMode(QPrinter.Color)
    printer.setDocName("发票排版打印")

    dlg = QPrintDialog(printer, parent)
    if dlg.exec() != QPrintDialog.Accepted:
        return

    painter = QPainter()
    if not painter.begin(printer):
        QMessageBox.warning(parent, "打印", "无法开始打印。")
        return

    painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

    # 设备像素 → mm 换算
    dpi = max(printer.logicalDpiX(), printer.logicalDpiY())
    dev_w = printer.width()      # 设备像素宽
    dev_h = printer.height()
    page_w_mm = dev_w / dpi * 25.4
    page_h_mm = dev_h / dpi * 25.4

    # 内容在纸上的居中偏移
    offset_x_mm = max(0.0, (page_w_mm - PAGE_W_MM) / 2.0)
    offset_y_mm = max(0.0, (page_h_mm - PAGE_H_MM) / 2.0)

    try:
        for i, page in enumerate(pages):
            if i > 0:
                printer.newPage()
            img = render_page(page, dpi=dpi, show_cutline=show_cutline)
            x = offset_x_mm / 25.4 * dpi
            y = offset_y_mm / 25.4 * dpi
            w = PAGE_W_MM / 25.4 * dpi
            h = PAGE_H_MM / 25.4 * dpi
            painter.drawImage(x, y, img, 0, 0, w, h)
    finally:
        painter.end()

    QMessageBox.information(parent, "打印", f"已发送 {len(pages)} 页到打印机。")
