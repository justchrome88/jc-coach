> СТАТУС: ВСПОМОГАТЕЛЬНЫЙ / ЧАСТИЧНО АКТУАЛЬНЫЙ / НЕ SOURCE OF TRUTH
> Канонический источник: `docs/PROJECT_CONTROL.md`, `docs/SECURITY.md` и `docs/DEPLOYMENT.md`.
> Не использовать этот файл как текущий план реализации, если `PROJECT_CONTROL` явно на него не ссылается.

# Public Deployment Checklist

Цель: подготовить `jcnodex.ru` к публичному доступу, Steam Web API key и HTTPS.

## Уже сделано на сервере

- FastAPI переведен под `systemd`:
  - unit: `/etc/systemd/system/jc-coach.service`;
  - listen: `127.0.0.1:8010`;
  - autostart enabled.
- Nginx reverse proxy включен:
  - config: `/etc/nginx/sites-available/jcnodex`;
  - enabled: `/etc/nginx/sites-enabled/jcnodex`;
  - `server_name jcnodex.ru www.jcnodex.ru jcnodex 192.168.102.129 88.201.150.73`;
  - upload limit: `2048m`.
- Certbot и nginx plugin уже установлены.
- `.env` подготовлен под домен:
  - `PUBLIC_BASE_URL=http://jcnodex.ru`;
  - `STEAM_REALM=http://jcnodex.ru`;
  - `SESSION_SECRET_KEY` установлен;
  - `AUTH_COOKIE_SECURE=false` до HTTPS.
- Публичный `/` показывает landing с кнопками входа/регистрации.
- Рабочие страницы закрыты session auth.
- Локальная VM резолвит `jcnodex.ru` в `192.168.102.129` через `/etc/hosts`.
- Sing-box оставлен для внешнего исходящего трафика VM, но добавлено direct-исключение для `88.201.150.73/32`.

## Сетевая схема

- LAN IP VM: `192.168.102.129`.
- Public router IP для сайта: `88.201.150.73`.
- Outbound IP самой VM через sing-box: `185.141.217.101`.
- Локальная проверка сайта с VM:
  - `curl http://jcnodex.ru/` -> `192.168.102.129`;
  - `curl http://192.168.102.129/` -> nginx;
  - `curl https://api.ipify.org` -> `185.141.217.101`.

Важно: если с самой VM `curl http://88.201.150.73/` не открывается, это может быть нормальным при отключенном hairpin NAT на роутере. Внешнюю доступность лучше проверять с устройства вне LAN.

## Что сделать после проброса портов

1. Пробросить на роутере:
   - external TCP `80` -> server `80`;
   - external TCP `443` -> server `443`.
2. Проверить извне:
   - `http://jcnodex.ru/` открывает landing.
3. Выпустить сертификат:
   - `certbot --nginx -d jcnodex.ru`
4. После успешного SSL обновить `.env`:
   - `PUBLIC_BASE_URL=https://jcnodex.ru`
   - `STEAM_REALM=https://jcnodex.ru`
   - `AUTH_COOKIE_SECURE=true`
5. Перезапустить приложение:
   - `systemctl restart jc-coach.service`
6. Проверить:
   - `curl -I https://jcnodex.ru/`
   - landing открывается;
   - `/dashboard` редиректит на `/login`;
   - регистрация/вход работают.

## Steam Web API key

Для Steam Community Developer в поле домена укажи публичный домен: `jcnodex.ru`.

После получения key:

1. Открой `/settings/imports`.
2. Вставь Steam Web API key.
3. Нажми `Run` у failed `match_history_sync` job или `Обработать очередь`.

## Команды диагностики

```bash
systemctl status jc-coach.service --no-pager
systemctl status nginx --no-pager
nginx -t
journalctl -u jc-coach.service -n 100 --no-pager
tail -n 100 /var/log/nginx/jcnodex.error.log
```
