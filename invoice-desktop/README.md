# 发票排版打印 Windows 桌面版

Windows 64 位桌面应用，支持自动更新。

## 功能特性

- **PDF/图片解析**：支持 PDF、JPG、PNG 等格式发票
- **智能排版**：自动拼版到 A4 纸，实时预览
- **打印支持**：连接系统打印机直接打印
- **自动更新**：后台检测新版本，一键下载更新并重启

## 快速使用

### 运行打包后的 EXE（推荐给最终用户）

```bash
# 直接双击运行
dist/InvoicePrint.exe

# 或命令行运行
cd dist
InvoicePrint.exe
```

**首次启动**：程序会在后台检测更新（异步，不阻塞主界面）。如检测到新版本，会弹窗提示。

### 源码运行（开发/调试）

```bash
# 安装依赖
pip install PySide6 pymupdf requests

# 运行
python app/main.py
```

**命令行参数**：

- `--version`：打印版本号并退出
- `--check-update`：只检查更新（诊断用）

## 自动更新机制

### 用户视角

1. 启动应用后，后台自动检测更新（不影响使用）
2. 若有新版本，弹出对话框提示版本号、更新说明、文件大小
3. 点击"立即更新"，下载 → 校验 → 替换旧版 EXE → 自动重启
4. 点击"跳过"，本次启动不再提示（下次启动仍会检测）

### 技术实现

- **更新源**：`http://118.178.193.189/updates/`（阿里云轻量服务器）
- **检测协议**：GET `/updates/update.json`，返回最新版本元数据
- **下载&校验**：SHA-256 完整性校验，确保文件未被篡改
- **替换策略**：
  1. 下载到临时目录 `%TEMP%\invprint_upd_*\update.bin`
  2. 启动批处理脚本 `_updater.bat`（等待主进程退出 → 替换 EXE → 重启）
  3. 主进程退出，批处理接管
- **容错**：下载失败、校验失败、网络超时均有友好提示，不影响当前版本使用

## 开发指南

### 项目结构

```
invoice-desktop/
├── app/
│   ├── main.py              # 入口
│   ├── config.py            # 版本号、应用名等配置
│   ├── gui/
│   │   └── main_window.py   # 主窗口（导入文件、预览、打印）
│   ├── core/
│   │   ├── parser.py        # PDF/图片解析
│   │   ├── layout.py        # A4 排版引擎
│   │   └── printer.py       # 打印接口
│   └── updater/
│       ├── updater.py       # 更新器核心逻辑
│       ├── updater_config.py # 更新源 URL
│       └── updater_ui.py    # 更新提示对话框
├── scripts/
│   ├── build_exe.py                # PyInstaller 打包脚本
│   ├── make_update_manifest.py     # 生成 update.json
│   ├── upload_to_server.py         # 上传到阿里云服务器
│   ├── deploy_updates_route.py     # 部署服务器 Flask 路由
│   └── test_update_flow.py         # 端到端更新测试
└── dist/
    └── InvoicePrint.exe     # 打包后的单文件 EXE（~72 MB）
```

### 发布新版本流程

#### 1. 修改版本号

编辑 `app/config.py`：

```python
APP_VERSION = "1.0.1"  # 修改这里
```

#### 2. 打包 EXE

```bash
python scripts/build_exe.py --clean
```

输出：`dist/InvoicePrint.exe`（~72 MB，包含所有依赖）

#### 3. 生成更新清单

```bash
python scripts/make_update_manifest.py
```

生成：
- `server-payload/update.json`（版本元数据 + SHA-256）
- `server-payload/InvoicePrint_1.0.1_win64.exe`（复制后的 EXE）

#### 4. 上传到服务器

```bash
python scripts/upload_to_server.py
```

上传到：`http://118.178.193.189/updates/`

#### 5. 验证

```bash
# 快速验证（命令行）
dist/InvoicePrint.exe --check-update

# 完整测试（下载+校验）
python scripts/test_update_flow.py
```

### 更换服务器

如果以后换了服务器或域名，只需修改 **一个文件**：

**`app/updater/updater_config.py`**：

```python
# 当前配置（阿里云轻量服务器公网 IP）
UPDATE_BASE_URL = "http://118.178.193.189/updates"

# 换服务器时改这里，例如：
# UPDATE_BASE_URL = "https://your-new-domain.com/updates"
```

然后重新打包 EXE 并上传到新服务器。

### 服务器端配置

#### Flask 路由（已部署）

位置：`/opt/personal-site/app.py`

```python
UPDATES_DIR = "/opt/personal-site/updates"

@app.route("/updates/<path:filename>")
def serve_update(filename):
    return send_from_directory(UPDATES_DIR, filename)
```

#### 文件结构

```
/opt/personal-site/updates/
├── update.json                           # 最新版本元数据
└── InvoicePrint_1.0.0_win64.exe         # 对应版本的 EXE
```

#### 权限要求

```bash
# 目录必须有执行位，Flask 才能进入
chmod 755 /opt/personal-site/updates

# 文件可读即可
chmod 644 /opt/personal-site/updates/*
```

## 依赖项

### Python 依赖

```
PySide6>=6.6.0      # Qt6 GUI 框架
pymupdf>=1.23.0     # PDF 解析（PyMuPDF）
Pillow>=10.0.0      # 图片处理
requests>=2.31.0    # HTTP 请求（更新检测）
```

### 打包依赖

```
pyinstaller>=6.0.0
```

### 服务器依赖

```
Flask>=3.0.0        # Web 框架
gunicorn>=21.0.0    # WSGI 服务器
```

## 已知问题与限制

1. **更新下载大小**：完整 EXE 约 72 MB，受网络速度影响（未来可考虑差分更新）
2. **服务器依赖**：当前依赖阿里云轻量服务器（到期时间：根据租期）
3. **Windows 专用**：打包为 Win64 EXE，不支持 macOS/Linux

## 测试状态

✅ **已验证的功能**：

- [x] PDF/图片解析引擎
- [x] A4 排版与实时预览
- [x] 打印功能
- [x] PyInstaller 单文件打包
- [x] 自动更新检测
- [x] 从公网下载更新文件
- [x] SHA-256 完整性校验
- [x] 服务器 Flask 路由部署

⚠️ **待实际验证**：

- [ ] 替换自身 EXE 并自动重启（需真实用户环境测试，已实现代码逻辑）

## 技术栈

- **GUI**: PySide6 (Qt6)
- **PDF**: PyMuPDF (pymupdf)
- **打包**: PyInstaller --onefile --windowed
- **更新**: HTTP + SHA-256 校验
- **服务器**: Flask + Gunicorn (Ubuntu 24.04)

## 许可与联系

内部工具，未开源。

技术支持：联系开发者
