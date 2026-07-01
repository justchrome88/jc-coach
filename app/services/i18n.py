from __future__ import annotations

SUPPORTED_LOCALES = ("ru", "en")
DEFAULT_LOCALE = "ru"

TRANSLATIONS = {
    "ru": {
        "nav.dashboard": "Дашборд",
        "nav.stats": "Статистика",
        "nav.coach": "Тренер",
        "nav.matches": "Матчи",
        "nav.upload": "Импорт",
        "nav.report": "Отчёт",
        "nav.accounts": "Аккаунты",
        "nav.login": "Войти",
        "nav.register": "Регистрация",
        "nav.logout": "Выйти",
        "language.ru": "Рус",
        "language.en": "Eng",
        "stats.title": "Общая статистика",
        "stats.subtitle": "Срез текущей формы, динамики и карт за выбранный диапазон матчей.",
        "stats.range": "Диапазон",
        "stats.last_matches": "Последние матчи",
        "stats.date_range": "По датам",
        "stats.all": "Все матчи",
        "stats.apply": "Применить",
        "stats.reset": "Сброс",
        "stats.period": "Период",
        "stats.trend": "Динамика",
        "stats.maps": "Карты",
        "stats.sources": "Источники",
        "stats.recent": "Последние матчи",
        "steam.title": "Аккаунты и автоимпорт",
        "steam.connect": "Подключить Steam",
        "steam.auth_code": "Game Authentication Code",
        "steam.queue_sync": "Поставить sync в очередь",
        "steam.run_queue": "Обработать очередь",
    },
    "en": {
        "nav.dashboard": "Dashboard",
        "nav.stats": "Stats",
        "nav.coach": "Coach",
        "nav.matches": "Matches",
        "nav.upload": "Import",
        "nav.report": "Report",
        "nav.accounts": "Accounts",
        "nav.login": "Log In",
        "nav.register": "Sign Up",
        "nav.logout": "Log Out",
        "language.ru": "Rus",
        "language.en": "Eng",
        "stats.title": "General Stats",
        "stats.subtitle": "Current form, trends and maps for the selected match range.",
        "stats.range": "Range",
        "stats.last_matches": "Last matches",
        "stats.date_range": "Date range",
        "stats.all": "All matches",
        "stats.apply": "Apply",
        "stats.reset": "Reset",
        "stats.period": "Period",
        "stats.trend": "Trend",
        "stats.maps": "Maps",
        "stats.sources": "Sources",
        "stats.recent": "Recent matches",
        "steam.title": "Accounts and Auto Import",
        "steam.connect": "Connect Steam",
        "steam.auth_code": "Game Authentication Code",
        "steam.queue_sync": "Queue sync",
        "steam.run_queue": "Run queue",
    },
}


def normalize_locale(value: str | None) -> str:
    if value in SUPPORTED_LOCALES:
        return value
    return DEFAULT_LOCALE


def translate(locale: str, key: str) -> str:
    normalized = normalize_locale(locale)
    return TRANSLATIONS.get(normalized, TRANSLATIONS[DEFAULT_LOCALE]).get(
        key,
        TRANSLATIONS[DEFAULT_LOCALE].get(key, key),
    )
