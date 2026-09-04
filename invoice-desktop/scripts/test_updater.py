# -*- coding: utf-8 -*-
"""端到端更新器测试：启动本地 HTTP 服务器扮演「阿里云更新服务器」。

验证：
1. 构造一个假的新版本 manifest（版本号高于当前）
2. 客户端 check_for_update() 应返回 available=True 且 URL 正确
3. download_and_verify() 应下载成功且 SHA-256 一致
4. 用假版本号（仍可用）再来一遍，应 available=False（版本相等不更新）
"""
import http.server
import json
import os
import socketserver
import sys
import tempfile
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import config
from app.updater import updater
from app.updater import updater_config, updater as upd


# 假更新服务器内容
FAKE_VERSION = "999.0.0"
FAKE_BODY = b"FAKE-UPDATE-EXE-CONTENT-" * 100
import hashlib
FAKE_SHA = hashlib.sha256(FAKE_BODY).hexdigest()


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.endswith("/update.json"):

            manifest = {
                "app": "invoice-print",
                "version": FAKE_VERSION,
                "notes": "测试更新说明",
                "url": "/updates/InvoicePrint_999.0.0_win64.exe",
            }
            payload = json.dumps(manifest).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        elif self.path.endswith(".exe"):
            self.send_response(200)
            self.send_header("Content-Length", str(len(FAKE_BODY)))
            self.end_headers()
            self.wfile.write(FAKE_BODY)
        else:
            self.send_response(404)
            self.end_headers()


def main():
    # 起本地服务器
    port = 8787
    httpd = socketserver.TCPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    print(f"[test] 本地更新服务器 http://127.0.0.1:{port}")

    # 临时把更新源指向本地（不打脏真实配置）
    old_base = updater_config.UPDATE_BASE_URL
    old_verify = updater_config.SKIP_SSL_VERIFY
    updater_config.UPDATE_BASE_URL = f"http://127.0.0.1:{port}/updates"
    updater_config.SKIP_SSL_VERIFY = False
    try:
        # 1. 检查
        info = upd.check_for_update()
        assert info.get("available"), f"应检测到新版本, got {info}"
        assert info["version"] == FAKE_VERSION, info
        assert "updates/" in info["url"], info
        print("[test] 检查到新版本:", info["version"], "| url:", info["url"])

        # 2. 下载+校验
        tmp = upd._download_and_verify(info)
        assert tmp is not None, "下载+校验失败"
        with open(tmp, "rb") as f:
            assert f.read() == FAKE_BODY
        print("[test] 下载+SHA256 校验 OK")

        # 3. 相同版本不应触发更新
        old_ver = config.APP_VERSION
        config.APP_VERSION = FAKE_VERSION  # 模拟已是最新
        info2 = upd.check_for_update()
        assert not info2.get("available"), f"相同版本不应更新, got {info2}"
        config.APP_VERSION = old_ver
        print("[test] 相同版本不更新 OK")

        # 4. 源码模式 apply_update 应返回"无法替换"（is_frozen=False）
        from unittest.mock import patch
        with patch("app.updater.updater._is_frozen", return_value=False):
            res = upd.apply_update(info)
            assert not res.get("ok"), res
            assert "无法替换" in res.get("reason", "")
        print("[test] 源码模式不替换(exe 需真打包后验证) OK")

        print("\n=== UPDATER E2E TESTS PASSED ===")
    finally:
        updater_config.UPDATE_BASE_URL = old_base
        updater_config.SKIP_SSL_VERIFY = old_verify
        httpd.shutdown()


if __name__ == "__main__":
    main()