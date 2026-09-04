# -*- coding: utf-8 -*-
"""完整更新流程测试（非 GUI，直接调用更新器 API）。

测试场景：本地 1.0.0 → 服务器 1.0.1 → 下载 → 校验 → 模拟替换（不真替换 EXE）
"""
import os
import sys
import tempfile
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from app import config
from app.updater import updater

def test_full_update_flow():
    print("=" * 60)
    print("完整更新流程测试")
    print("=" * 60)

    # 1. 检测更新
    print("\n[1] 检测更新 ...")
    info = updater.check_for_update()
    if not info.get("available"):
        print(f"    当前无更新可用: 本地 {config.APP_VERSION}, 服务器 {info.get('version', 'N/A')}")
        print("    提示：需要服务器上 update.json 的 version > 本地版本")
        return

    print(f"    检测到新版本: {info['version']}")
    print(f"    更新说明: {info['notes']}")
    print(f"    下载地址: {info['url']}")

    # 2. 下载并校验
    print("\n[2] 下载并校验 SHA-256 ...")
    tmp_file = updater._download_and_verify(info)
    if not tmp_file:
        print("    下载或校验失败")
        return

    print(f"    下载成功: {tmp_file}")
    print(f"    文件大小: {os.path.getsize(tmp_file) / 1024 / 1024:.1f} MB")

    # 3. 验证文件有效性
    with open(tmp_file, "rb") as f:
        magic = f.read(2)
    if magic != b"MZ":
        print(f"    警告: 下载的文件不是有效的 PE 文件 (magic: {magic!r})")
        return
    print(f"    PE 文件头校验通过")

    # 4. 清理
    temp_dir = os.path.dirname(tmp_file)
    shutil.rmtree(temp_dir, ignore_errors=True)
    print(f"\n[3] 清理临时文件: {temp_dir}")

    print("\n" + "=" * 60)
    print("✓ 完整更新流程测试通过")
    print("  (下载、校验、文件有效性 均 OK)")
    print("  替换自身 需要在真实 EXE 中手动触发验证")
    print("=" * 60)

if __name__ == "__main__":
    test_full_update_flow()
