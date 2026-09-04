# -*- coding: utf-8 -*-
"""生成服务器用的 update.json（自动读版本 + 算 SHA-256）。

用法:
    python scripts/make_update_manifest.py [新版本号] [发布说明]

说明:
    1. 先用 build_exe.py 打包好 dist/InvoicePrint.exe，并改好 app/config.py 的 APP_VERSION。
    2. 本脚本把 dist/InvoicePrint.exe 复制到 server-payload/，命名成带版本号的
       InvoicePrint_<ver>_win64.exe，并生成 server-payload/update.json。
    3. 把 server-payload/ 下内容上传到服务器 /updates/ 即可。

发布步骤（发新版）:
    1. 改 app/config.py: APP_VERSION = "1.0.1"
    2. python scripts/build_exe.py
    3. python scripts/make_update_manifest.py "1.0.1" "修复xxx、新增xxx"
    4. 上传 server-payload/* 到服务器 /opt/personal-site/updates/
"""
import hashlib
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from app import config

DIST_EXE = os.path.join(ROOT, "dist", "InvoicePrint.exe")
SERVER_DIR = os.path.join(os.path.dirname(ROOT), "server-payload")


def sha256_of(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if not os.path.exists(DIST_EXE):
        print(f"未找到 {DIST_EXE}，请先运行 build_exe.py", file=sys.stderr)
        sys.exit(1)

    version = sys.argv[1] if len(sys.argv) > 1 else config.APP_VERSION
    notes = sys.argv[2] if len(sys.argv) > 2 else ""

    os.makedirs(SERVER_DIR, exist_ok=True)

    # 拷贝为带版本号的文件名
    exe_name = f"InvoicePrint_{version}_win64.exe"
    server_exe = os.path.join(SERVER_DIR, exe_name)
    shutil.copy2(DIST_EXE, server_exe)

    checksum = sha256_of(server_exe)
    size = os.path.getsize(server_exe)

    manifest = {
        "app": config.APP_ID,
        "version": version,
        "notes": notes,
        "url": f"/updates/{exe_name}",
        "size_bytes": size,
        "sha256": checksum,
        "checksum": checksum,
    }
    manifest_path = os.path.join(SERVER_DIR, "update.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"版本: {version}")
    print(f"文件: {server_exe} ({size/1024/1024:.1f} MB)")
    print(f"SHA256: {checksum}")
    print(f"清单: {manifest_path}")
    print(f"\n上传 update.json + {exe_name} 到服务器 /opt/personal-site/updates/ 即可")


if __name__ == "__main__":
    main()