# -*- coding: utf-8 -*-
"""A4 排版引擎：把发票列表排成 A4 页面（每页 2 张半张 / 1 张整页）。

尺寸以「毫米」为单位，渲染时再按目标 DPI 换算像素，保证打印尺寸精确。
"""

from dataclasses import dataclass, field
from typing import List, Optional

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QImage, QPainter, QPen, QPixmap

from .invoice import Invoice

# ---- 页面常量（mm）----
PAGE_W_MM = 210.0
PAGE_H_MM = 297.0

# 发票内容最大尺寸（与 HTML 工具保持一致）
CARD2_MAX_W_MM = 200.0   # 每页 2 张时发票最大宽
CARD2_MAX_H_MM = 142.0   # 每页 2 张时发票最大高
CARD1_MAX_W_MM = 200.0   # 每页 1 张时发票最大宽
CARD1_MAX_H_MM = 285.0   # 每页 1 张时发票最大高

CUTLINE_COLOR = (224, 72, 72)   # 裁剪线红色 #E04848


@dataclass
class LayoutItem:
    """一张发票在页面上的绘制位置（mm 单位，以页面左上角为原点）。"""
    invoice: Invoice
    rect_mm: QRectF              # 绘制矩形（已等比，居中）
    cut_before: bool = False     # 此卡片上方是否需要裁剪线（第 2 张）

    @property
    def x_mm(self) -> float:
        return self.rect_mm.x()

    @property
    def y_mm(self) -> float:
        return self.rect_mm.y()

    @property
    def w_mm(self) -> float:
        return self.rect_mm.width()

    @property
    def h_mm(self) -> float:
        return self.rect_mm.height()


@dataclass
class LayoutPage:
    index: int
    items: List[LayoutItem] = field(default_factory=list)

    @property
    def is_half_mode(self) -> bool:
        """半张模式（每页 2 张）时，画中间裁剪线。"""
        return len(self.items) == 2


def _fit_rect(max_w_mm: float, max_h_mm: float, aspect: float) -> QRectF:
    """给定最大宽高和一个纵横比，返回居中的等比矩形（从原点算，中心对齐）。"""
    if aspect <= 0 or max_w_mm <= 0 or max_h_mm <= 0:
        return QRectF(0, 0, 0, 0)
    w = max_w_mm
    h = w / aspect
    if h > max_h_mm:
        h = max_h_mm
        w = h * aspect
    # 居中
    x = (max_w_mm - w) / 2
    y = (max_h_mm - h) / 2
    return QRectF(x, y, w, h)


def layout_pages(invoices: List[Invoice], per_page: int = 2) -> List[LayoutPage]:
    """把发票列表排成页面。per_page: 1 或 2。"""
    pages: List[LayoutPage] = []
    if per_page not in (1, 2):
        per_page = 2

    count = len(invoices)
    for i in range(0, count, per_page):
        chunk = invoices[i:i + per_page]
        page = LayoutPage(index=len(pages))
        for j, inv in enumerate(chunk):
            if per_page == 2:
                # 每页 2 张：上半张 / 下半张
                card_h = PAGE_H_MM / 2.0
                max_w = CARD2_MAX_W_MM
                max_h = CARD2_MAX_H_MM
                rect = _fit_rect(max_w, max_h, inv.aspect)
                rect.translate(0, j * card_h)
                item = LayoutItem(invoice=inv, rect_mm=rect, cut_before=(j == 1))
            else:
                # 每页 1 张：整页
                rect = _fit_rect(CARD1_MAX_W_MM, CARD1_MAX_H_MM, inv.aspect)
                item = LayoutItem(invoice=inv, rect_mm=rect, cut_before=False)
            page.items.append(item)
        pages.append(page)
    return pages


# ---------------- 渲染 ----------------

def _mm_to_px(mm: float, dpi: int) -> int:
    """毫米 → 像素（1 英寸 = 25.4mm）。"""
    return int(round(mm / 25.4 * dpi))


def render_page(page: LayoutPage, dpi: int = 300, show_cutline: bool = True) -> QImage:
    """把一页渲染成 QImage（白底），返回 dpi 分辨率位图。"""
    w_px = _mm_to_px(PAGE_W_MM, dpi)
    h_px = _mm_to_px(PAGE_H_MM, dpi)
    img = QImage(w_px, h_px, QImage.Format_RGB32)
    img.fill(Qt.white)

    painter = QPainter(img)
    painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
    try:
        for item in page.items:
            # 裁剪线（在该卡片上边界）
            if show_cutline and item.cut_before:
                _draw_cutline(painter, item.y_mm, dpi)

            # 绘制发票图像
            pm = item.invoice.scaled_qt(
                _mm_to_px(item.w_mm, dpi),
                _mm_to_px(item.h_mm, dpi),
            )
            if not pm.isNull():
                # 用实际绘制矩形（可能因圆整有微小偏差）
                dx = _mm_to_px(item.x_mm, dpi)
                dy = _mm_to_px(item.y_mm, dpi)
                dw = _mm_to_px(item.w_mm, dpi)
                dh = _mm_to_px(item.h_mm, dpi)
                painter.drawPixmap(dx, dy, dw, dh, pm)

        # 整页模式（1张）没有裁剪线；半张模式末卡下边界不需要线
    finally:
        painter.end()
    return img


def _draw_cutline(painter: QPainter, y_mm: float, dpi: int) -> None:
    """在 y_mm 处画一条贯穿页面的红色虚线裁剪线。"""
    y_px = _mm_to_px(y_mm, dpi)
    pen = QPen(Qt.red, max(1, _mm_to_px(0.3, dpi)))
    pen.setStyle(Qt.DashLine)
    painter.setPen(pen)
    painter.drawLine(0, y_px, _mm_to_px(PAGE_W_MM, dpi), y_px)


def page_to_pixmap(page: LayoutPage, screen_dpi: int = 96, show_cutline: bool = True) -> QPixmap:
    """渲染成适合屏幕预览的 QPixmap（降低 DPI 以省内存）。"""
    img = render_page(page, dpi=screen_dpi, show_cutline=show_cutline)
    return QPixmap.fromImage(img)
