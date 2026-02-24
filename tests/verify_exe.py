import subprocess
import time
import os
import sys
from pathlib import Path

def verify_exe():
    # Path to the generated EXE (repo-local). Keep this robust against renames.
    repo_root = Path(__file__).resolve().parents[1]
    candidates = [
        repo_root / "dist" / "easy_tracer" / "easy_tracer.exe",
        repo_root / "dist" / "easy_tracer" / "easy_tracer",  # non-Windows fallback
    ]
    exe_path = next((p for p in candidates if p.exists()), candidates[0])

    print(f"Verifying EXE at: {exe_path}")

    if not exe_path.exists():
        print(f"Error: EXE not found at {exe_path}")
        sys.exit(1)

    print("Launching EXE...")
    try:
        # Start the process
        # We use creationflags to suppress the console window if it's a GUI app,
        # but for testing we want to see output if possible.
        process = subprocess.Popen([str(exe_path)])

        # Wait for a few seconds to let it initialize
        print("Waiting for 5 seconds...")
        time.sleep(5)

        # Check if it's still running
        if process.poll() is None:
            print("SUCCESS: EXE is running!")
            print("Terminating process...")
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
            print("Process terminated.")
            sys.exit(0)
        else:
            print(f"FAILURE: EXE exited prematurely with code {process.returncode}")
            sys.exit(1)

    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    verify_exe()
