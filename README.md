# EasyTracer

A GUI wrapper for various Android performance tracing tools, including Systrace, Perfetto, Simpleperf, and Traceview.

## Features

- **Device Management**: Auto-detect connected Android devices via ADB.
- **Systrace**: Capture system traces with configurable categories and buffer size.
- **Perfetto**: Record modern Android traces.
- **Simpleperf**: Profile application or system CPU usage.
- **Traceview**: Start/Stop method tracing with sampling support.
- **Combo Capture**: Run multiple tools simultaneously for comprehensive analysis.

## Prerequisites

- Python 3.9+
- ADB (Android Debug Bridge) installed and in PATH.
- Connected Android device with USB debugging enabled.

## Setup

1.  **Create Virtual Environment (.venv)**:
    ```bash
    # Linux/macOS
    python -m venv .venv

    # Windows (PowerShell)
    python -m venv .venv
    ```

2.  **Install Dependencies**:
    ```bash
    # Linux/macOS
    ./.venv/bin/python -m pip install -r requirements.txt

    # Windows (PowerShell)
    .\.venv\Scripts\python.exe -m pip install -r requirements.txt
    ```
    *Note: If `requirements.txt` is missing, install `PySide6` manually:*
    ```bash
    # Linux/macOS
    ./.venv/bin/python -m pip install PySide6

    # Windows (PowerShell)
    .\.venv\Scripts\python.exe -m pip install PySide6
    ```

3.  **Environment**:
    Ensure `adb` is in your system PATH.

## Running the Application

Run the main script from the root directory:

```bash
# Linux/macOS
./.venv/bin/python easy_tracer/src/easy_tracer/main.py

# Windows (PowerShell)
.\.venv\Scripts\python.exe easy_tracer/src/easy_tracer/main.py
```

## Running Tests

To run the unit tests:

```bash
# Linux/macOS
./.venv/bin/python -m unittest discover easy_tracer/tests

# Windows (PowerShell)
.\.venv\Scripts\python.exe -m unittest discover easy_tracer/tests
```

## Build EXE (Windows)

From the `easy_tracer` directory:

```bash
.\.venv\Scripts\python.exe tools\release.py --clean
```

The executable will be generated at:

```
easy_tracer/dist/easytracer/easy_tracer.exe
```

## Project Structure

- `src/easy_tracer/ui`: Qt (PySide6) UI components.
- `src/easy_tracer/presenters`: Business logic connecting UI and Services.
- `src/easy_tracer/services`: Coordination of tracing tasks.
- `src/easy_tracer/framework`: Adapters for external tools (ADB, Systrace, etc.).
- `src/easy_tracer/framework/external`: Bundled external tools (Systrace, Simpleperf).
