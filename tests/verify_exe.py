import subprocess
import time
import os
import sys

def verify_exe():
    # Path to the generated EXE
    exe_path = os.path.abspath(os.path.join(
        os.path.dirname(__file__),
        "../../easy_tracer/dist/easytracer/easy_tracer.exe"
    ))

    print(f"Verifying EXE at: {exe_path}")

    if not os.path.exists(exe_path):
        print(f"Error: EXE not found at {exe_path}")
        sys.exit(1)

    print("Launching EXE...")
    try:
        # Start the process
        # We use creationflags to suppress the console window if it's a GUI app,
        # but for testing we want to see output if possible.
        process = subprocess.Popen(exe_path)

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
