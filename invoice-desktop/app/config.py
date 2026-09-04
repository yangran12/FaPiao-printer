# -*- coding: utf-8 -*-
"""全局配置：版本号、组织名、路径、应用常量。"""

APP_NAME = "发票排版打印"
APP_ID = "invoice-print"                 # 更新清单里用于标识本应用
APP_VERSION = "1.0.0"                    # 当前版本（发版时手动改这里 + updater_config.py 的当前版本应一致）
ORG_NAME = "YR"                          # Qt 设置/缓存目录用


def get_data_dir() -> str:
    """用户数据目录：保存设置/偏好，升级软件不丢。"""
    import os
    from pathlib import Path

    base = os.environ.get("APPDATA")
    if base:
        d = Path(base) / ORG_NAME / APP_ID
    else:
        d = Path.home() / f".{APP_ID}"
    d.mkdir(parents=True, exist_ok=True)
    return str(d)


def get_settings_path() -> str:
    import os
    return os.path.join(get_data_dir(), "settings.ini")


def get_cache_dir() -> str:
    """缓存目录：发票渲染中间文件。"""
    import os
    from pathlib import Path

    base = os.environ.get("LOCALAPPDATA")
    if base:
        d = Path(base) / ORG_NAME / APP_ID / "cache"
    else:
        d = Path.home() / f".{APP_ID}" / "cache"
    d.mkdir(parents=True, exist_ok=True)
    return str(d)
