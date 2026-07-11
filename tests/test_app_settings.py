from app.db.models import AppSetting
from app.services.ingestion.settings import get_app_setting, set_app_setting


def test_set_app_setting_upserts_trimmed_value(db):
    setting = set_app_setting(db, "steam_web_api_key", " key-1 ")

    assert setting.value == "key-1"
    assert get_app_setting(db, "steam_web_api_key") == "key-1"

    set_app_setting(db, "steam_web_api_key", "key-2")

    assert db.query(AppSetting).count() == 1
    assert get_app_setting(db, "steam_web_api_key") == "key-2"
