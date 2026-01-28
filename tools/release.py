
import os
import argparse
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SPEC_FILE = ROOT_DIR / "easy_tracer.spec"

def main() -> int:
    parser = argparse.ArgumentParser(description="Build EasyTracer executable")
    parser.add_argument("--clean", action="store_true", help="Clean dist/build before packaging")
    args = parser.parse_args()

    if not SPEC_FILE.exists():
        print(f"Error: Spec file not found at {SPEC_FILE}")
        return 1

    cmd = "pyinstaller --noconfirm"
    if args.clean:
        cmd += " --clean"

    cmd += f" {SPEC_FILE.name}"

    print(f"Executing: {cmd}")

    # Execute command in the root directory
    return os.system(f"cd /d {ROOT_DIR} && {cmd}")

if __name__ == "__main__":
    raise SystemExit(main())
