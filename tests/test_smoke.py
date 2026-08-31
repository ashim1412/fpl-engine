import fpl_engine
from fpl_engine.config.settings import get_settings


def test_package_imports():
    assert fpl_engine.__version__


def test_settings_load():
    settings = get_settings()
    assert settings.database_url is None or isinstance(settings.database_url, str)
