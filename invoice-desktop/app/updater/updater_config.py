# -*- coding: utf-8 -*-
"""更新源配置 —— ★ 换服务器 / 域名 / 端口时，只需要改这一个文件 ★

当前更新源：阿里云轻量服务器 118.178.193.189 上的 personal-site Flask 服务
（443 端口 HTTPS，因用 IP 访问证书不匹配，客户端跳过证书校验）。

以后如果换服务器 / 域名 / 备案通过走正规 HTTPS，只改下面两个常量即可，
其余代码不用动。
"""

import os

# 服务器更新根路径（update.json 和 .exe 都放在这个路径下）
# 注意：阿里云这台机器上 80 端口是 personal-site（带 /updates 路由），
#       443 端口是另一个应用（qqhb），没有 /updates 路由，所以走 HTTP:80。
UPDATE_BASE_URL = "http://118.178.193.189/updates"

# 是否跳过 SSL 证书校验。走 HTTP 时无需校验，改 False 性能更好。
SKIP_SSL_VERIFY = False

# 可追加的自定义请求头（预留，一般不用动）
EXTRA_HEADERS = {
    "User-Agent": "InvoicePrint-Updater/1.0",
}

# ---- 派生配置，一般不用改 ----
UPDATE_JSON_URL = os.path.join(UPDATE_BASE_URL, "update.json")

# 下载/校验相关
DOWNLOAD_TIMEOUT = 120          # 秒
CHUNK_SIZE = 256 * 1024         # 下载分块大小


def verify_ssl():
    """返回是否校验证书（requests 用 verify= 参数）。"""
    return not SKIP_SSL_VERIFY
