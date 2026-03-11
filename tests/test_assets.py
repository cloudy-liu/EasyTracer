from easy_tracer.assets import icon_path


def test_app_icon_uses_app_ico():
    path = icon_path("app")

    assert path is not None
    assert path.name == "app.ico"
