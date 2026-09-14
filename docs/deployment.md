# Розгортання

## Локально (розробка)

```bash
cp services/backend/.env.example services/backend/.env
make bup      # docker compose -f docker-compose-local.yml build && up -d
make seed     # демо-дані
make lg       # логи
```

`local.entrypoint.sh`: чекає Postgres → `migrate` → `collectstatic` → `create_default_super_user` → `runserver 0.0.0.0:8000`.
Код змонтовано volume'ами — зміни в `apps/`, `templates/`, `static/`, `settings/` підхоплюються без перезбірки.
Після зміни `requirements.txt` або `Dockerfile` — `make bup`.

## Змінні оточення (`services/backend/.env`)

| Змінна | Призначення |
|---|---|
| `POSTGRES_DB/USER/PASS/HOST/PORT` | підключення до БД |
| `SECRET_KEY` | Django secret (у production — обов'язково змінити) |
| `DEBUG` | `1`/`0`; у `ENVIRONMENT=production` завжди `0` |
| `ENVIRONMENT` | `local` / `dev` / `production`. У production адмінка змонтована на `/`, інакше на `/admin/` |
| `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS` | список через кому |
| `PROJECT_NAME` | назва в шапці адмінки та PDF |
| `DJANGO_SUPERUSER_LOGIN/EMAIL/PASSWORD` | дефолтний суперюзер (створюється/оновлюється при старті) |
| `EMAIL_BACKEND` | за замовчуванням console |
| `USE_S3`, `S3_*` | статика/медіа в S3-сумісному сховищі |
| `SENTRY_DSN` | опційно |

## Production

`docker-compose.yml` / `prod.docker-compose.yml` + `entrypoint.sh` (gunicorn). Перед деплоєм:

1. `ENVIRONMENT=production`, `DEBUG=0`, новий `SECRET_KEY`, реальні `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS`.
2. Postgres-образ: локально використовується `postgres:13-alpine` (старий `13.3-alpine` не знає TZ `Europe/Kyiv`).
   У `docker-compose.yml` перевірити тег.
3. Статика: `collectstatic` виконується в entrypoint; при `USE_S3=1` — у бакет.
4. Створити користувачів і додати в групи `Technician` / `Employee` (`is_staff=True`). Групи створюються міграціями автоматично.

## Оновлення

```bash
git pull
make bup            # перезбірка, якщо змінились залежності
make mg             # міграції (entrypoint робить це і сам при старті)
```

## Резервні копії

`make pg-dump db_name=… db_user=… db_pass=… export_dir=…` / `make pg-load …` (скрипти в `services/backend/scripts/`).
