from app.services.shared.i18n import DEFAULT_LOCALE, normalize_locale, translate


def test_normalize_locale_defaults_to_russian():
    assert DEFAULT_LOCALE == "ru"
    assert normalize_locale("en") == "en"
    assert normalize_locale("de") == "ru"
    assert normalize_locale(None) == "ru"


def test_translate_uses_curated_dictionary_and_key_fallback():
    assert translate("ru", "nav.coach") == "Тренер"
    assert translate("en", "nav.coach") == "Coach"
    assert translate("en", "missing.key") == "missing.key"
