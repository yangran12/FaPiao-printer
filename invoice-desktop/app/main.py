# -*- coding: utf-8 -*-
"""发票排版打印 · Windows 桌面版入口。

用法:
    python app/main.py                # 正常启动
    python app/main.py --version      # 只打印版本号退出（更新器/诊断用）
    python app/main.py --check-update # 只检查更新并打印结果（诊断用）
"""
import sys
import os

# 确保在未打包（源码运行）时也能 import 到 app 包
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    args = [a for a in sys.argv[1:]]

    if "--version" in args:
        from app.config import APP_VERSION, APP_NAME
        print(f"{APP_NAME} {APP_VERSION}")
        return 0

    if "--check-update" in args:
        # 仅用于诊断：执行一次更新检查并打印结果
        from app.updater import updater
        result = updater.check_for_update()
        print(result)
        return 0

    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt
    from app.gui.main_window import MainWindow
    from app import config

    # 高分屏适配
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app = QApplication(sys.argv)
    app.setApplicationName(config.APP_NAME)
    app.setApplicationVersion(config.APP_VERSION)
    app.setOrganizationName(config.ORG_NAME)
    app.setStyle("Fusion")

    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    sys.exit(main())
