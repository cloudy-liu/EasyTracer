<p align="center">
  <img src="doc/assets/easytracer-logo-brand-guidelines.svg" alt="EasyTracer" width="760" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-0078D6?logo=desktop&logoColor=white" alt="Platform" />
  <img src="https://img.shields.io/badge/GUI-PySide6-41CD52?logo=qt&logoColor=white" alt="GUI" />
  <img src="https://img.shields.io/badge/CLI-Click-000000?logo=gnubash&logoColor=white" alt="CLI" />
</p>

EasyTracer 是一个面向 Android 性能分析场景的桌面 GUI 工具，统一封装了
`Systrace`、`Perfetto`、`Simpleperf`、`Traceview` 等常用链路，降低抓取门槛，
适合日常性能定位、回归比对和问题复现。

## ⚡ 30 秒快速开始

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -U pip
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python src/easy_tracer/main.py
```

首次运行前请先确认 ADB 可用：

```powershell
adb version
adb devices -l
```

## ✨ 核心能力

- 🔌 **设备管理**：通过 ADB 自动识别已连接设备。
- 🧵 **Systrace 抓取**：支持分类选择、缓冲区配置、目标应用设置。
- 📈 **Perfetto 抓取**：支持现代 Android Trace 录制流程。
- 🔥 **Simpleperf 分析**：支持 App/系统 CPU profiling，可生成 HTML 报告。
- 🧠 **Traceview 方法跟踪**：支持启动/停止、采样模式。
- 🧩 **组合抓取（Combo）**：可并行触发多种抓取方式。
- 🪟 **统一操作体验**：主界面统一录制按钮、状态反馈和日志输出。

## 🧱 技术栈

- Python `>=3.10`
- PySide6
- ADB（Android Debug Bridge）
- PyInstaller（可选，用于打包 EXE）

## 📦 环境要求

开始前请确保：

- 已安装 Python 3.10+ 并加入 `PATH`
- 已安装 `adb` 并可在终端直接执行
- Android 设备已开启开发者选项与 USB 调试

如果尚未安装 ADB，建议使用官方 Android Platform Tools：

- 下载地址：https://developer.android.com/tools/releases/platform-tools
- 下载后解压，并将目录加入系统 `PATH`
- 重新打开终端后执行 `adb version` 验证

可通过以下命令自检：

```powershell
python --version
adb version
adb devices -l
```

## 🚀 快速开始（Windows / PowerShell）

### 1) 创建虚拟环境

```powershell
python -m venv .venv
```

### 2) 安装依赖

```powershell
.\.venv\Scripts\python -m pip install -U pip
.\.venv\Scripts\python -m pip install -r requirements.txt
```

### 3) 启动应用

```powershell
.\.venv\Scripts\python src/easy_tracer/main.py
```

运行成功判定：

- 能看到 EasyTracer 主窗口（顶部工具栏 + 左侧导航 + 主内容区）。
- 即使未连接设备，应用也应正常启动（只是无法开始抓取）。
- 连接设备后执行 `adb devices -l`，状态为 `device` 时可正常采集。

## 🧪 自检模式（推荐）

项目内置 `--selftest`，可在无 GUI 交互下验证关键抓取链路是否可用。

```powershell
.\.venv\Scripts\python src/easy_tracer/main.py --selftest
```

常见参数：

```powershell
.\.venv\Scripts\python src/easy_tracer/main.py --selftest `
  --adb adb `
  --device YOUR_SERIAL `
  --output .\output\selftest_run `
  --package com.android.settings `
  --skip-simpleperf
```

## 🏗️ 打包 EXE（Windows）

### 方式 A：使用项目脚本（推荐）

```powershell
.\.venv\Scripts\python -m pip install pyinstaller
.\.venv\Scripts\python tools/release.py --clean
```

说明：

- `tools/release.py` 默认会在打包后做一次 `--warmup` 预热，减少首次交互启动抖动。
- 可通过 `--no-warmup` 关闭预热。

### 方式 B：直接调用 PyInstaller

```powershell
.\.venv\Scripts\pyinstaller easy_tracer.spec --noconfirm
```

产物默认位于：

- `dist/easy_tracer/easy_tracer.exe`

## 📁 项目结构（简版）

```text
src/easy_tracer/
  framework/      # 各抓取后端适配层（adb/systrace/perfetto/simpleperf/traceview）
  services/       # 业务服务层
  presenters/     # Presenter 逻辑
  ui/             # 主窗口、面板、组件
  main.py         # 应用入口（支持 --selftest / --warmup）
  selftest.py     # 自检流程
tools/
  release.py      # 打包脚本
easy_tracer.spec  # PyInstaller 配置
```

## 🛠️ 常见问题

### 1) 识别不到设备

- 确认 USB 调试已开启
- 确认授权弹窗已允许
- 执行 `adb devices -l` 检查状态是否为 `device`

### 2) `dist` 目录删除失败 / 文件被占用

应用退出时会尝试关闭 ADB 后台进程；若仍被占用，可手动执行：

```powershell
adb kill-server
```

### 3) 首次启动较慢

首次运行可能受 Defender 扫描、DLL 冷启动缓存影响；后续通常会更快。  
也可以在发布流程中启用 warmup（`tools/release.py` 默认已开启）。

### 4) 打包后脚本资源报错

请优先使用仓库内 `easy_tracer.spec` 与 `tools/release.py`，二者已处理
systrace/simpleperf 资源打包细节。

## ✅ 测试

运行测试：

```powershell
pytest -q
```

验证打包产物是否能拉起：

```powershell
.\.venv\Scripts\python tests/verify_exe.py
```

## 🤝 贡献与许可证

欢迎通过 Issue / PR 一起完善项目。

- 提交前建议先运行 `pytest -q`。
- Commit message 采用 Conventional Commits（详见仓库 `AGENTS.md` 约定）。
- 当前仓库尚未提供 `LICENSE` 文件；如需对外分发或商用，请先补充许可证声明。

---

如果这个项目对你有帮助，欢迎提 Issue / PR 一起完善 🙌
