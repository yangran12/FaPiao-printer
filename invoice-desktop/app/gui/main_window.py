# -*- coding: utf-8 -*-
"""主窗口：现代简洁风格，拖放发票 → A4 预览 → 打印。"""
from typing import List

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QFileDialog, QFrame, QHBoxLayout, QLabel,
    QMainWindow, QMessageBox, QPushButton, QRadioButton, QScrollArea,
    QVBoxLayout, QWidget,
)

from .. import config
from ..core.invoice import Invoice
from ..core.layout import layout_pages, page_to_pixmap
from ..core.pdf_engine import load_invoices
from ..updater import updater
from .printer import print_pages
from .update_dialog import UpdateDialog

MODERN_QSS = """
/* ===== 现代简洁 · Windows 11 浅色风格 ===== */
QMainWindow, QWidget#centralRoot { background: #f3f4f6; color: #1f2937; }

/* 标题栏 */
QWidget#headerBar { background: #16233f; border-radius: 0px; }
QLabel#headerTitle { color: #ffffff; font-size: 16px; font-weight: 700; letter-spacing: 1px; padding: 2px 0; }
QLabel#headerSub   { color: #9fb0cc; font-size: 12px; }

/* 工具栏卡片 */
QFrame#toolCard {
    background: #ffffff; border-radius: 10px;
    margin: 10px 14px 2px 14px; padding: 6px;
}
QFrame#toolCard QRadioButton, QFrame#toolCard QCheckBox { font-size: 13px; color: #374151; spacing: 6px; }

/* 按钮 */
QPushButton {
    background: #ffffff; border: 1px solid #d1d5db; border-radius: 8px;
    padding: 8px 16px; font-size: 13px; color: #1f2937;
}
QPushButton:hover { background: #f9fafb; border-color: #9ca3af; }
QPushButton:pressed { background: #eef0f2; }
QPushButton:disabled { color: #9ca3af; background: #f3f4f6; border-color: #e5e7eb; }

QPushButton#primaryBtn {
    background: #2563eb; color: #ffffff; border: none; font-weight: 600; padding: 8px 22px;
}
QPushButton#primaryBtn:hover { background: #1d4ed8; }
QPushButton#primaryBtn:disabled { background: #93b4ee; color: #eaf1fd; }

/* 拖放区 */
QLabel#dropZone {
    background: #ffffff; border: 2px dashed #c3cad6; border-radius: 12px;
    color: #6b7280; font-size: 13px; padding: 26px 12px;
}
QLabel#dropZone:hover { border-color: #2563eb; background: #eff6ff; }
QLabel#dropZone[dragActive="true"] { border-color: #2563eb; background: #eff6ff; }

/* 状态栏 */
QStatusBar { background: #eef0f3; color: #4b5563; font-size: 12px; }

/* 预览滚动区 */
QScrollArea { background: #f3f4f6; border: none; }
QLabel#pageCard {
    background: #ffffff; border: 1px solid #e5e7eb; border-radius: 8px;
    padding: 8px;
}
QLabel#pageLabel { color: #6b7280; font-size: 12px; padding: 2px 0 6px 0; }

/* 空状态 */
QLabel#emptyHint { color: #9ca3af; font-size: 15px; font-weight: 600; }
"""


class UpdateCheckThread(QThread):
    """后台更新检查线程。"""
    finished_check = Signal(dict)

    def run(self):
        try:
            info = updater.check_for_update()
        except Exception:
            info = {"available": False}
        self.finished_check.emit(info)


class UpdateApplyThread(QThread):
    """后台下载 + 替换线程。"""
    finished_apply = Signal(dict)

    def __init__(self, info: dict, parent=None):
        super().__init__(parent)
        self._info = info

    def run(self):
        try:
            result = updater.apply_update(self._info)
        except Exception as e:
            result = {"ok": False, "reason": str(e)}
        self.finished_apply.emit(result)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{config.APP_NAME} · 半张A4 · 每页2张")
        self.resize(920, 720)
        self.setMinimumSize(760, 560)

        self.invoices: List[Invoice] = []
        self.per_page = 2
        self.show_cutline = True

        self._build_ui()
        self.setStyleSheet(MODERN_QSS)
        self._rebuild_preview()

        self._update_thread = None
        self._download_thread = None
        # 后台检查更新（不阻塞界面）
        self._start_update_check()

    def closeEvent(self, ev):
        """退出前等待更新线程收敛，避免 'QThread destroyed while running' 崩溃。"""
        for t in (self._update_thread, self._download_thread):
            if t is not None and t.isRunning():
                t.wait(5000)  # 最多等 5s（下载线程若有超时上限，这里兜底）
        super().closeEvent(ev)

    # ---------------- UI ----------------
    def _build_ui(self):
        central = QWidget()
        central.setObjectName("centralRoot")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 标题栏
        header = QWidget()
        header.setObjectName("headerBar")
        header.setFixedHeight(58)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(18, 0, 18, 0)
        title = QLabel(config.APP_NAME)
        title.setObjectName("headerTitle")
        sub = QLabel("拖入电子发票 → 自动排成半张A4（每页2张）→ 一键打印")
        sub.setObjectName("headerSub")
        hl.addWidget(title)
        hl.addWidget(sub)
        hl.addStretch(1)
        root.addWidget(header)

        # 工具栏
        tool = QFrame()
        tool.setObjectName("toolCard")
        th = QHBoxLayout(tool)
        th.setContentsMargins(12, 8, 12, 8)
        th.setSpacing(16)

        th.addWidget(QLabel("每页张数："))
        self.rb2 = QRadioButton("2张（半张A4）")
        self.rb1 = QRadioButton("1张")
        self.rb2.setChecked(True)
        self.rb2.toggled.connect(lambda c: self._on_per_page(c, 2))
        self.rb1.toggled.connect(lambda c: self._on_per_page(c, 1))
        th.addWidget(self.rb2)
        th.addWidget(self.rb1)

        self.cut_check = QCheckBox("显示裁剪线")
        self.cut_check.setChecked(True)
        self.cut_check.toggled.connect(self._on_cut_toggled)
        th.addWidget(self.cut_check)

        th.addStretch(1)

        self.add_btn = QPushButton("添加文件…")
        self.add_btn.clicked.connect(self._on_add_files)
        th.addWidget(self.add_btn)

        self.clear_btn = QPushButton("清空")
        self.clear_btn.clicked.connect(self._on_clear)
        th.addWidget(self.clear_btn)

        self.print_btn = QPushButton("一键打印")
        self.print_btn.setObjectName("primaryBtn")
        self.print_btn.setEnabled(False)
        self.print_btn.clicked.connect(self._on_print)
        th.addWidget(self.print_btn)

        root.addWidget(tool)

        # 拖放区
        self.drop_zone = QLabel(
            "把发票文件拖到这里\n支持 PDF 电子发票 及 PNG / JPG / BMP / WEBP 图片，可一次拖入多张"
        )
        self.drop_zone.setObjectName("dropZone")
        self.drop_zone.setAlignment(Qt.AlignCenter)
        self.drop_zone.setMinimumHeight(86)
        root.addWidget(self.drop_zone)
        root.setSpacing(10)

        # 预览滚动区
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.preview_host = QWidget()
        self.preview_host.setObjectName("previewHost")
        self.preview_layout = QVBoxLayout(self.preview_host)
        self.preview_layout.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        self.preview_layout.setContentsMargins(14, 10, 14, 24)
        self.preview_layout.setSpacing(18)
        scroll.setWidget(self.preview_host)
        root.addWidget(scroll, 1)

        # 状态栏
        self.statusBar().showMessage("就绪 — 等待添加发票")

        # 拖放支持
        self.drop_zone.setAcceptDrops(True)
        self.drop_zone.installEventFilter(self)
        self.setAcceptDrops(True)

    # ---------------- 事件 ----------------
    def eventFilter(self, obj, ev):
        if obj is self.drop_zone:
            if ev.type() == ev.Type.DragEnter:
                return self._on_drag_enter(ev)
            if ev.type() == ev.Type.DragLeave:
                self._set_drag_active(False)
                return True
            if ev.type() == ev.Type.Drop:
                self._on_drop(ev)
                return True
        return super().eventFilter(obj, ev)

    def _set_drag_active(self, active: bool):
        self.drop_zone.setProperty("dragActive", "true" if active else "false")
        self.drop_zone.style().unpolish(self.drop_zone)
        self.drop_zone.style().polish(self.drop_zone)

    def _on_drag_enter(self, ev: QDragEnterEvent) -> bool:
        if ev.mimeData().hasUrls():
            self._set_drag_active(True)
            ev.acceptProposedAction()
            return True
        return False

    def _on_drop(self, ev: QDropEvent):
        self._set_drag_active(False)
        paths = [u.toLocalFile() for u in ev.mimeData().urls() if u.isLocalFile()]
        if paths:
            self._load_paths(paths)

    # ---------------- 行为 ----------------
    def _on_add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "添加发票文件", "",
            "发票文件 (*.pdf *.png *.jpg *.jpeg *.bmp *.webp);;所有文件 (*.*)",
        )
        if files:
            self._load_paths(files)

    def _on_clear(self):
        self.invoices.clear()
        self._rebuild_preview()

    def _on_per_page(self, checked: bool, value: int):
        if checked:
            self.per_page = value
            self._rebuild_preview()

    def _on_cut_toggled(self, checked: bool):
        self.show_cutline = checked
        self._rebuild_preview()

    def _on_print(self):
        if not self.invoices:
            return
        print_pages(self, self.invoices, self.per_page, self.show_cutline)

    # ---------------- 加载 ----------------
    def _load_paths(self, paths: List[str]):
        self.statusBar().showMessage(f"正在处理 {len(paths)} 个文件…")
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            invoices, errors = load_invoices(paths)
        finally:
            QApplication.restoreOverrideCursor()

        if invoices:
            self.invoices.extend(invoices)
            self._rebuild_preview()
        msg = f"已载入 {len(self.invoices)} 张发票。"
        if errors:
            msg += f" 失败 {len(errors)} 个：" + "；".join(errors[:3])
            self.statusBar().showMessage(msg)
        else:
            self.statusBar().showMessage(msg)

    # ---------------- 预览 ----------------
    def _rebuild_preview(self):
        # 清空旧预览
        while self.preview_layout.count():
            item = self.preview_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        pages = layout_pages(self.invoices, per_page=self.per_page)
        self.print_btn.setEnabled(bool(self.invoices))

        if not pages:
            hint = QLabel("还没有发票 — 拖入文件或点击「添加文件…」开始")
            hint.setObjectName("emptyHint")
            hint.setAlignment(Qt.AlignCenter)
            self.preview_layout.addWidget(hint)
            return

        for page in pages:
            page_box = QWidget()
            pb = QVBoxLayout(page_box)
            pb.setContentsMargins(0, 0, 0, 0)
            pb.setSpacing(0)

            label = QLabel(f"第 {page.index + 1} 页 · "
                           f"{'半张A4' if page.is_half_mode else '整页'} · "
                           f"{len(page.items)} 张发票")
            label.setObjectName("pageLabel")
            label.setAlignment(Qt.AlignCenter)
            pb.addWidget(label)

            img_label = QLabel()
            img_label.setObjectName("pageCard")
            img_label.setAlignment(Qt.AlignCenter)
            pm = page_to_pixmap(page, screen_dpi=96, show_cutline=self.show_cutline)
            img_label.setPixmap(pm)
            img_label.setFixedSize(pm.width(), pm.height())
            pb.addWidget(img_label)

            self.preview_layout.addWidget(page_box)

        self.statusBar().showMessage(
            f"已载入 {len(self.invoices)} 张发票，共 {len(pages)} 页。"
        )

    # ---------------- 更新 ----------------
    def _start_update_check(self):
        self._update_thread = UpdateCheckThread(self)
        self._update_thread.finished_check.connect(self._on_update_check)
        self._update_thread.start()

    def _on_update_check(self, info: dict):
        if not info.get("available"):
            return
        dlg = UpdateDialog(self, info)
        if dlg.exec() == UpdateDialog.Accepted:
            self.statusBar().showMessage(f"正在下载新版本 v{info['version']} …")
            self._apply_update(info)

    def _apply_update(self, info: dict):
        # 再次后台执行下载+替换，避免阻塞界面
        self._download_thread = UpdateApplyThread(info, self)
        self._download_thread.finished_apply.connect(self._on_update_applied)
        self._download_thread.start()

    def _on_update_applied(self, result: dict):
        if result.get("ok"):
            QMessageBox.information(
                self, "更新", "更新已下载并应用，程序将重新启动。"
            )
            # 更新线程已通过 bat 重启新 exe，这里什么都不用做
        else:
            reason = result.get("reason", "未知错误")
            new_pkg = result.get("new_package", "")
            msg = f"更新失败：{reason}"
            if new_pkg:
                msg += f"\n请手动下载：{new_pkg}"
            QMessageBox.warning(self, "更新失败", msg)
