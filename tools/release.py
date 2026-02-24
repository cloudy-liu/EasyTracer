
import os
import argparse
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SPEC_FILE = ROOT_DIR / "easy_tracer.spec"

def main() -> int:
    parser = argparse.ArgumentParser(description="Build EasyTracer executable")
    parser.add_argument("--clean", action="store_true", help="Clean dist/build before packaging")
    parser.add_argument("--no-warmup", action="store_true", help="Skip post-build warmup run")
    parser.add_argument("--warmup-timeout", type=int, default=180, help="Warmup timeout in seconds (default: 180)")
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
    rc = os.system(f"cd /d {ROOT_DIR} && {cmd}")
    if rc != 0:
        return rc

    if args.no_warmup:
        return 0

    exe_name = "easy_tracer.exe" if os.name == "nt" else "easy_tracer"
    exe_path = ROOT_DIR / "dist" / "easy_tracer" / exe_name
    if not exe_path.exists():
        print(f"Warmup skipped: executable not found: {exe_path}")
        return 0

    print("Warming up first-run caches (this can take a while on the first run)...")
    try:
        subprocess.run(
            [str(exe_path), "--warmup"],
            cwd=str(exe_path.parent),
            timeout=max(10, int(args.warmup_timeout)),
            check=False,
        )
    except subprocess.TimeoutExpired:
        print("Warmup timed out; continuing anyway.")
    except Exception as e:
        print(f"Warmup failed: {e}")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
