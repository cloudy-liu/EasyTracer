from __future__ import annotations

import json
from pathlib import Path


class ConfigService:
    def __init__(self, config_path: Path, default_adb_path: str, default_output_dir: Path):
        self.config_path = Path(config_path)
        self.adb_path = default_adb_path
        self.output_dir = str(default_output_dir)
        self._load()

    def _load(self) -> None:
        if not self.config_path.exists():
            self._ensure_output_dir()
            return
        try:
            data = json.loads(self.config_path.read_text(encoding="utf-8"))
            self.adb_path = data.get("adb_path", self.adb_path)
            self.output_dir = data.get("output_dir", self.output_dir)
        except (json.JSONDecodeError, OSError):
            pass
        self._ensure_output_dir()

    def _ensure_output_dir(self) -> None:
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

    def update(self, adb_path: str, output_dir: str) -> None:
        if adb_path:
            self.adb_path = adb_path
        if output_dir:
            self.output_dir = str(Path(output_dir).resolve())
        self._ensure_output_dir()
        self.save()

    def save(self) -> None:
        payload = {
            "adb_path": self.adb_path,
            "output_dir": self.output_dir,
        }
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
