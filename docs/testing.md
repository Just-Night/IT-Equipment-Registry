# Тестування

```bash
make test                                              # усі тести
docker compose -f docker-compose-local.yml exec app pytest -q tests/admin   # окрема папка
docker compose -f docker-compose-local.yml exec app pytest -k overdue -v    # за назвою
```

pytest + pytest-django + factory_boy. Конфіг: `services/backend/service/pytest.ini`.
Тестова БД створюється з міграцій (перевіряє і data-міграції груп).

## Структура (`tests/`, дзеркалить домени)

| Папка / файл | Що покриває | К-сть |
|---|---|---|
| `conftest.py`, `factories.py` | фікстури `api_client`, `admin_user`, `technician_user`, `employee_user`; фабрики моделей | — |
| `test_smoke.py` | health-check | 1 |
| `users/test_permissions.py` | групи з міграцій, точний набір прав, helpers ролей | 5 |
| `equipment/test_models.py` | `__str__`, дефолти, унікальність, історія | 4 |
| `equipment/test_services.py` | наступний огляд, прострочення, гарантія (межі), `set_status`, реальні огляди | 14 |
| `maintenance/test_models.py`, `test_services.py` | дефолти, всі переходи статусів заявки → обладнання | 6 + 9 |
| `admin/test_admin.py` | доступ по ролях до списків, ізоляція даних працівника, inline, seed | 8 |
| `admin/test_dashboard.py` | дашборд для 3 ролей, KPI, ізоляція | 7 |
| `admin/test_export.py` | CSV/XLSX, права на експорт | 6 |
| `admin/test_pdf_actions.py` | PDF-endpoint'и: 200 / 403 / 404 по ролях, content-type | 8 |
| `reports/test_summary.py` | KPI, списки, групування по місяцях (локальний час) | 9 |
| `reports/test_pdf.py` | 3 PDF: `%PDF`, кирилиця, вміст | 4 |

Разом: **81**.

## Принципи

- Прості тести через ORM і Django `Client` / DRF `APIClient`, без моків.
- Кожен етап розробки додавав свої тести; `pytest` зелений у кінці етапу.
- Ролі перевіряються і на рівні прав (403), і на рівні даних (чужі записи відсутні у відповіді).
