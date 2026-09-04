# -*- coding: utf-8 -*-
"""对真实阿里云服务器的端到端更新测试。

模拟「本机是旧版 0.9.0」→ 检测到服务器 1.0.0 → 从公网下载真实 EXE → SHA-256 校验。
"""
import os
import sys
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import config
from app.updater import updater as upd

def main():
    print("=" * 60)
    print("真实服务器端到端更新测试")
    print("=" * 60)

    old_version = config.APP_VERSION
    config.APP_VERSION = "0.9.0"  # 模拟旧版本
    try:
        info = upd.check_for_update()
        assert info.get("available"), f"应检测到更新, got {info}"
        print(f"[1] 检测到新版本: {info['version']} (本地模拟 {config.APP_VERSION})")
        print(f"    notes: {info['notes']}")
        print(f"    url:   {info['url']}")

        # 下载 + SHA256 校验（真实 71MB 文件）
        print("[2] 从公网下载并校验 SHA-256 …")
        tmp = upd._download_and_verify(info)
        assert tmp is not None, "下载或校验失败"
        size = os.path.getsize(tmp)
        print(f"    下载 OK: {tmp} ({size/1024/1024:.1f} MB), SHA-256 一致")

        # 验证下载内容确实是有效 PE 文件（MZ 头）
        with open(tmp, "rb") as f:
            head = f.read(2)
        assert head == b"MZ", f"不是有效 EXE: {head!r}"
        print(f"    PE 文件头校验 OK (MZ)")

        shutil.rmtree(os.path.dirname(tmp), ignore_errors=True)
        print("\n=== 真实服务器端到端测试通过 ===")
    finally:
        config.APP_VERSION = old_version

if __name__ == "__main__":
    main()