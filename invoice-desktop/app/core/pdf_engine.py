# -*- coding: utf-8 -*-
"""发票文件解析引擎：PDF / 常见图片 → Invoice 列表。

- PDF：用 PyMuPDF 渲染每页为图像（保留原始纵横比），每页当一张发票。
- 图片：PNG/JPG/BMP/WEBP 直接加载，保留原始纵横比。
"""
import os
from typing import List

import pymupdf  # type: ignore

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap

from .invoice import Invoice

# 渲染 PDF 时的目标 DPI（控制清晰度与内存平衡）
PDF_RENDER_DPI = 300
# 图片读取时上限（太高会吃内存）
MAX_IMAGE_DIM = 4000


def load_invoices(paths: List[str]) -> tuple[List[Invoice], List[str]]:
    """加载一批文件，返回 (成功的发票列表, 失败的文件名列表)。"""
    invoices: List[Invoice] = []
    errors: List[str] = []

    for path in paths:
        lower = path.lower()
        if lower.endswith(".pdf"):
            try:
                invoices.extend(_pdf_to_invoices(path))
            except Exception as e:  # noqa: BLE001
                errors.append(f"{path}: {e}")
        elif lower.endswith((".png", ".jpg", ".jpeg", ".bmp", ".webp")):
            try:
                inv = _image_to_invoice(path)
                if inv is not None:
                    invoices.append(inv)
                else:
                    errors.append(f"{path}: 无法识别的图片")
            except Exception as e:  # noqa: BLE001
                errors.append(f"{path}: {e}")
        else:
            errors.append(f"{path}: 不支持的文件类型")

    return invoices, errors


def _pdf_to_invoices(path: str) -> List[Invoice]:
    doc = pymupdf.open(path)
    result: List[Invoice] = []
    for page_no in range(doc.page_count):
        page = doc.load_page(page_no)
        # 渲染为位图（矩阵缩放到目标 DPI）
        zoom = PDF_RENDER_DPI / 72.0
        mat = pymupdf.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
        qimg = qimg.copy()  # 深拷贝，脱离 samples 缓冲
        pm = QPixmap.fromImage(qimg)
        base = os.path.basename(path)
        result.append(Invoice(name=f"{base} (p{page_no + 1})", pixmap=pm))
    doc.close()
    return result


def _image_to_invoice(path: str):
    qimg = QImage(path)
    if qimg.isNull():
        return None
    # 限制超大图
    if qimg.width() > MAX_IMAGE_DIM or qimg.height() > MAX_IMAGE_DIM:
        qimg = qimg.scaled(
            MAX_IMAGE_DIM, MAX_IMAGE_DIM,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
    return Invoice(name=path.rsplit("/", 1)[-1].rsplit("\\", 1)[-1], pixmap=QPixmap.fromImage(qimg))