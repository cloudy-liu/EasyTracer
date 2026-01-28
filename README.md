# EasyTracer

A GUI wrapper for various Android performance tracing tools, including Systrace, Perfetto, Simpleperf, and Traceview.

## Features

- **Device Management**: Auto-detect connected Android devices via ADB.
- **Systrace**: Capture system traces with configurable categories and buffer size. Auto-loads categories upon device selection.
- **Perfetto**: Record modern Android traces.
- **Simpleperf**: Profile application or system CPU usage (FlameGraph generation supported).
- **Traceview**: Start/Stop method tracing with sampling support.
- **Combo Capture**: Run multiple tools simultaneously for comprehensive analysis.

## Prerequisites

- **Python 3.9+** must be installed and added to your system PATH (required for running Systrace and Simpleperf scripts).
- **ADB (Android Debug Bridge)** installed and in PATH.
- Connected Android device with USB debugging enabled.

## Setup

1.  **Create Virtual Environment (.venv)**:
    ```bash
    # Windows (PowerShell)
    python -m venv .venv
    ```

2.  **Install Dependencies**:
    ```bash
    # Windows (PowerShell)
    .\.venv\Scripts\pip install -r requirements.txt
    ```

3.  **Run Application**:
    ```bash
    .\.venv\Scripts\python src/easy_tracer/main.py
    ```

## Building Executable (Windows)

To package the application as a standalone EXE:

1.  Install PyInstaller:
    ```bash
    .\.venv\Scripts\pip install pyinstaller
    ```

2.  Build:
    ```bash
    .\.venv\Scripts\pyinstaller easy_tracer.spec --noconfirm
    ```

3.  The executable will be located in `dist/easy_tracer/easy_tracer.exe`.

## Troubleshooting

- **ADB locks**: If you cannot delete the `dist` folder, ensure the application is closed. The app attempts to kill the background ADB server on exit, but you may need to run `adb kill-server` manually if issues persist.
- **Startup speed**: The first launch might be slightly slower as it initializes ADB. Subsequent launches should be faster.
- **Scripts not found**: Ensure you have a valid Python installation in your system PATH, as the packaged tool relies on the system Python to execute vendor scripts (Systrace/Simpleperf).
