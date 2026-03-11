from pathlib import Path

from easy_tracer.main import _default_config_path


def test_default_config_path_uses_config_directory() -> None:
    app_root = Path("C:/easytracer")

    assert _default_config_path(app_root) == app_root / "config" / "config.json"
