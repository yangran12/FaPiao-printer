# -*- coding: utf-8 -*-
"""PyInstaller 一键打包脚本。

用法:
    python scripts/build_exe.py                 # 打包 onefile
    python scripts/build_exe.py --onefile       # 同上
    python scripts/build_exe.py --clean         # 先清缓存再打包

产出: dist/InvoicePrint.exe （单文件，Windows 64 位）
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
APP_FILE = os.path.join(ROOT, "app", "main.py")
DIST = os.path.join(ROOT, "dist")
BUILD = os.path.join(ROOT, "build")
SUMMARY = os.path.join(DIST, "build_summary.txt")


def main():
    clean = "--clean" in sys.argv or "-c" in sys.argv

    if clean and os.path.isdir(BUILD):
        shutil.rmtree(BUILD, ignore_errors=True)
    if os.path.isdir(DIST):
        # 保留旧 exe 名片（最新一份）
        shutil.rmtree(DIST, ignore_errors=True)
    os.makedirs(DIST, exist_ok=True)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean",
        "--onefile",
        "--windowed",  # 无控制台窗口
        "--name", "InvoicePrint",
        "--distpath", DIST,
        "--workpath", BUILD,
        "--specpath", ROOT,
        "--hidden-import", "pymupdf",
        "--collect-submodules", "pymupdf",
        APP_FILE,
    ]
    print(">>> " + " ".join(cmd))
    code = subprocess.call(cmd, cwd=ROOT)
    if code != 0:
        print("打包失败", file=sys.stderr)
        sys.exit(1)

    exe = os.path.join(DIST, "InvoicePrint.exe")
    if not os.path.exists(exe):
        print("未找到产物 InvoicePrint.exe", file=sys.stderr)
        sys.exit(1)

    size_mb = os.path.getsize(exe) / 1024 / 1024
    print(f"打包完成: {exe} ({size_mb:.1f} MB)")

    # 写构建摘要（供发布时读取版本）
    from app import config
    with open(SUMMARY, "w", encoding="utf-8") as f:
        f.write(f"version={config.APP_VERSION}\n")
        f.write(f"app={config.APP_ID}\n")
        f.write(f"built_with=PyInstaller\n")
    print(f"摘要: {SUMMARY}")


if __name__ == "__main__":
    main()