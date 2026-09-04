# -*- coding: utf-8 -*-
"""更新提示对话框：发现新版本时弹窗，提供「立即更新 / 以后再说」。"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QTextBrowser,
)

from .. import config


class UpdateDialog(QDialog):
    def __init__(self, parent, info: dict):
        super().__init__(parent)
        self.info = info
        self.setWindowTitle("发现新版本")
        self.setMinimumWidth(420)
        self.setModal(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        title = QLabel(f"发现新版本 v{info.get('version', '')}")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #16233f;")
        root.addWidget(title)

        notes = QTextBrowser()
        notes.setOpenExternalLinks(False)
        notes.setPlainText(info.get("notes", "").strip() or "（无更新说明）")
        notes.setFixedHeight(120)
        root.addWidget(notes)

        hint = QLabel("更新需要重新启动应用。")
        hint.setStyleSheet("font-size: 12px; color: #6b7280;")
        root.addWidget(hint)

        btns = QHBoxLayout()
        btns.addStretch(1)
        later = QPushButton("以后再说")
        later.clicked.connect(self.reject)
        btns.addWidget(later)
        update = QPushButton("立即更新")
        update.setStyleSheet(
            "background:#2563eb; color:#fff; font-weight:600;"
            "border:1px solid #2563eb; border-radius:8px; padding:8px 20px;"
            "font-size:13px;"
        )
        update.setDefault(True)
        update.clicked.connect(self.accept)
        btns.addWidget(update)
        root.addLayout(btns)