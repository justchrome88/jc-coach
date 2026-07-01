# Public Deployment Checklist

Цель: подготовить `jcnodex` к публичному доступу, Steam Web API key и HTTPS.

## Уже сделано на сервере

- FastAPI переведен под `systemd`:
  - unit: `/etc/systemd/system/jc-coach.service`;
  - listen: `127.0.0.1:8010`;
  - autostart enabled.
- Nginx reverse proxy включен:
  - config: `/etc/nginx/sites-available/jcnodex`;
  - enabled: `/etc/nginx/sites-enabled/jcnodex`;
  - `server_name jcnodex`;
  - upload limit: `2048m`.
- Certbot и nginx plugin уже установлены.
- `.env` подготовлен под домен:
  - `PUBLIC_BASE_URL=http://jcnodex`;
  - `STEAM_REALM=http://jcnodex`;
  - `SESSION_SECRET_KEY` установлен;
  - `AUTH_COOKIE_SECURE=false` до HTTPS.
- Публичный `/` показывает landing с кнопками входа/регистрации.
- Рабочие страницы закрыты session auth.

## Что сделать после проброса портов

1. Пробросить на роутере:
   - external TCP `80` -> server `80`;
   - external TCP `443` -> server `443`.
2. Проверить извне:
   - `http://jcnodex/` открывает landing.
3. Выпустить сертификат:
   - `certbot --nginx -d jcnodex`
4. После успешного SSL обновить `.env`:
   - `PUBLIC_BASE_URL=https://jcnodex`
   - `STEAM_REALM=https://jcnodex`
   - `AUTH_COOKIE_SECURE=true`
5. Перезапустить приложение:
   - `systemctl restart jc-coach.service`
6. Проверить:
   - `curl -I https://jcnodex/`
   - landing открывается;
   - `/dashboard` редиректит на `/login`;
   - регистрация/вход работают.

## Steam Web API key

Для Steam Community Developer в поле домена укажи публичный домен: `jcnodex`.

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
