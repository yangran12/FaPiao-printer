# -*- coding: utf-8 -*-
"""自动更新器：检查版本 → 下载 → SHA-256 校验 → 替换自身 → 重启。

设计要点：
- 服务器地址 / 是否校验证书 / 更新清单 URL 全部在 updater_config.py（换服务器只改那一个文件）。
- 不依赖第三方库，只用标准库 urllib（下载）、hashlib（校验）、subprocess（重启）。
- 替换自身采用「临时 bat 延迟替换」方案：Windows 下正在运行的 exe 无法被覆盖，
  先启动一个 bat（等待 2 秒后把新 exe 拷贝覆盖旧 exe，再启动新 exe，最后自删 bat），
  当前进程立刻退出。
"""
import hashlib
import json
import os
import shutil
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, Optional, Tuple

from .. import config
from . import updater_config


# ---------------- 小工具 ----------------

def _opener() -> urllib.request.OpenerDirector:
    """按配置构造 URL opener（可选跳过证书校验）。"""
    ctx = ssl.create_default_context()
    if updater_config.SKIP_SSL_VERIFY:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))


def _http_get_json(url: str, timeout: float = 20) -> Optional[Dict]:
    """GET 一个 JSON。失败返回 None（不抛异常，方便静默检查）。"""
    req = urllib.request.Request(url, headers=updater_config.EXTRA_HEADERS)
    try:
        with _opener().open(req, timeout=timeout) as resp:
            data = resp.read()
        return json.loads(data.decode("utf-8"))
    except Exception:
        return None


def _download(url: str, dest: str, timeout: float = None) -> bool:
    """流式下载文件到 dest。失败返回 False。"""
    timeout = timeout or updater_config.DOWNLOAD_TIMEOUT
    req = urllib.request.Request(url, headers=updater_config.EXTRA_HEADERS)
    try:
        with _opener().open(req, timeout=timeout) as resp:
            total = int(resp.headers.get("Content-Length") or 0)
            got = 0
            with open(dest, "wb") as fh:
                while True:
                    chunk = resp.read(updater_config.CHUNK_SIZE)
                    if not chunk:
                        break
                    fh.write(chunk)
                    got += len(chunk)
            if total and got != total:
                return False
        return True
    except Exception:
        try:
            os.remove(dest)
        except OSError:
            pass
        return False


def sha256_of(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _parse_version(ver: str) -> Tuple[int, ...]:
    """'1.2.3' -> (1,2,3)。无法解析时返回空元组（视为 0）。"""
    parts = []
    for seg in str(ver).strip().split("."):
        digits = "".join(ch for ch in seg if ch.isdigit())
        if digits:
            parts.append(int(digits))
        else:
            break
    return tuple(parts)


def is_newer_version(latest: str, current: str) -> bool:
    """latest > current 返回 True。支持 1.0 / 1.0.1 / 1.2.3.4。"""
    a, b = _parse_version(latest), _parse_version(current)
    # 位数补齐比较
    n = max(len(a), len(b))
    a += (0,) * (n - len(a))
    b += (0,) * (n - len(b))
    return a > b


# ---------------- 检查 ----------------

def _manifest_url() -> str:
    """动态拼 update.json 地址（支持测试时覆盖 UPDATE_BASE_URL）。"""
    return updater_config.UPDATE_BASE_URL.rstrip("/") + "/update.json"


def check_for_update() -> Dict:
    """检查是否有新版本。返回状态字典，供 GUI 与 --check-update 使用。

    返回:
      {available: False}                         无更新或检查失败
      {available: True, version, notes, url, checksum}  有新版本
    """
    manifest = _http_get_json(_manifest_url())
    if not manifest:
        return {"available": False, "error": "无法连接更新服务器"}

    if manifest.get("app") not in (None, config.APP_ID):
        return {"available": False, "error": "更新清单应用标识不匹配"}

    latest = manifest.get("version", "")
    if not is_newer_version(str(latest), config.APP_VERSION):
        return {"available": False}

    url = manifest.get("url", "")
    if not url.startswith(("http://", "https://")):
        if url.startswith("/"):
            # 绝对路径：相对于服务器域名根（避免和更新根目录前缀重复）
            parts = urllib.parse.urlsplit(updater_config.UPDATE_BASE_URL)
            origin = f"{parts.scheme}://{parts.netloc}"
            url = origin + url
        else:
            # 相对路径：相对于更新根目录
            url = updater_config.UPDATE_BASE_URL.rstrip("/") + "/" + url.lstrip("/")
    return {
        "available": True,
        "version": str(latest),
        "notes": manifest.get("notes", ""),
        "url": url,
        "checksum": manifest.get("checksum", ""),
    }


# ---------------- 下载 + 校验 + 替换 ----------------

def _download_and_verify(info: Dict) -> Optional[str]:
    """下载更新包到临时目录并校验 SHA-256。返回临时文件路径，失败返回 None。"""
    url = info["url"]
    tmp_dir = tempfile.mkdtemp(prefix="invprint_upd_")
    dest = os.path.join(tmp_dir, "update.bin")

    if not _download(url, dest):
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return None

    checksum = (info.get("checksum") or "").strip().lower()
    if checksum:
        actual = sha256_of(dest).lower()
        if actual != checksum:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            return None
    return dest


def _is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def _replace_and_restart(downloaded_exe: str) -> bool:
    """把 downloaded_exe 替换为当前程序并重启。

    PyInstaller onefile：当前 exe 是 sys.executable。
    源码运行：无法真正替换，退回「提示路径」（不实际执行）。
    """
    if not _is_frozen():
        # 源码模式：不支持原地替换，仅返回状态（测试/调试用）
        return False

    current_exe = os.path.abspath(sys.executable)
    if not os.path.exists(current_exe):
        return False

    # 校验下载的确实是个可执行文件
    if not os.path.basename(downloaded_exe).lower().endswith(".exe"):
        shutil.rmtree(os.path.dirname(downloaded_exe), ignore_errors=True)
        return False

    # 备份当前 exe（保留最近一份）
    backup = current_exe + ".bak"
    try:
        if os.path.exists(backup):
            os.remove(backup)
        shutil.copy2(current_exe, backup)
    except OSError:
        pass

    # 生成延迟替换 bat
    tmp_dir = os.path.dirname(downloaded_exe)
    bat = os.path.join(tmp_dir, "apply_update.bat")
    new_exe = os.path.join(tmp_dir, "InvoicePrint_new.exe")
    try:
        os.replace(downloaded_exe, new_exe)  # 临时目录内重命名
    except OSError:
        new_exe = downloaded_exe

    lines = [
        "@echo off",
        f"set NEW={new_exe}",
        f'set OLD="{current_exe}"',
        'timeout /t 2 /nobreak >nul',
        'copy /y "%NEW%" %OLD% >nul',
        'start "" %OLD%',
        'timeout /t 1 /nobreak >nul',
        'del "%NEW%" >nul 2>&1',
        f'del "%~f0" >nul 2>&1',
    ]
    with open(bat, "w", encoding="gbk", errors="ignore") as fh:
        fh.write("\r\n".join(lines))

    try:
        subprocess.Popen(["cmd", "/c", bat], cwd=tmp_dir,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except OSError:
        return False
    return True


def apply_update(info: Dict) -> Dict:
    """下载 + 校验 + 替换。返回状态字典。"""
    downloaded = _download_and_verify(info)
    if not downloaded:
        return {"ok": False, "reason": "下载失败或校验不通过"}

    if not _replace_and_restart(downloaded):
        # 源码模式或替换失败
        shutil.rmtree(os.path.dirname(downloaded), ignore_errors=True)
        return {"ok": False, "reason": "无法替换自身（请手动下载新版）",
                "new_package": info.get("url")}

    return {"ok": True}
