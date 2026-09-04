# -*- coding: utf-8 -*-
"""发票模型：一张发票 = 一张可打印的图像（保持原始纵横比）。"""
from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap


@dataclass
class Invoice:
    name: str                 # 文件名
    pixmap: QPixmap           # 渲染后的图像（可能是 PDF 某页 / 图片原图）

    @property
    def aspect(self) -> float:
        """宽高比（宽/高），>1 表示横向发票。"""
        if self.pixmap.isNull():
            return 1.0
        w = self.pixmap.width()
        h = self.pixmap.height()
        return w / h if h else 1.0

    def scaled_qt(self, max_w_px: int, max_h_px: int) -> QPixmap:
        """按 Qt 目标尺寸等比缩放（用于屏幕预览/打印渲染）。"""
        if self.pixmap.isNull():
            return QPixmap()
        return self.pixmap.scaled(
            max_w_px, max_h_px,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
