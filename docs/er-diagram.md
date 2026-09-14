# ER-діаграма

Усі предметні моделі наслідують `libs.db.models.BaseModel`: первинний ключ `uuid`,
`created_at`, `updated_at`. `Equipment` додатково веде історію змін (`HistoricalEquipment`,
`django-simple-history`). Користувачі — стандартна `auth.User`, ролі — `auth.Group`.

```mermaid
erDiagram
    USER {
        int id PK
        string username
        bool is_superuser
        bool is_staff
    }
    GROUP {
        int id PK
        string name "Technician | Employee"
    }
    CATEGORY {
        uuid uuid PK
        string name UK
        text description
    }
    LOCATION {
        uuid uuid PK
        string name UK
        string address
    }
    EQUIPMENT {
        uuid uuid PK
        string inventory_number UK
        string name
        string manufacturer
        string model_name
        string serial_number
        date purchase_date
        date warranty_until
        string status "active | faulty | in_repair | decommissioned"
        int inspection_interval_days "default 180"
        text note
        datetime created_at
        datetime updated_at
    }
    HISTORICAL_EQUIPMENT {
        int history_id PK
        datetime history_date
        string history_type "+ ~ -"
        string status
    }
    INSPECTION {
        uuid uuid PK
        datetime performed_at
        string condition "good | satisfactory | poor"
        text comment
        datetime created_at
    }
    INCIDENT {
        uuid uuid PK
        text description
        string status "new | in_progress | resolved | closed"
        datetime resolved_at
        text resolution
        datetime created_at
    }

    USER }o--o{ GROUP : "member of"
    CATEGORY ||--o{ EQUIPMENT : "category (PROTECT)"
    LOCATION ||--o{ EQUIPMENT : "location (PROTECT)"
    USER |o--o{ EQUIPMENT : "assigned_to (SET_NULL)"
    EQUIPMENT ||--o{ INSPECTION : "inspections (CASCADE)"
    USER |o--o{ INSPECTION : "performed_by (SET_NULL)"
    EQUIPMENT ||--o{ INCIDENT : "incidents (CASCADE)"
    USER |o--o{ INCIDENT : "reported_by (SET_NULL)"
    USER |o--o{ INCIDENT : "assigned_to (SET_NULL)"
    EQUIPMENT ||--o{ HISTORICAL_EQUIPMENT : "history"
    USER |o--o{ HISTORICAL_EQUIPMENT : "history_user"
```

## Обчислювані атрибути `Equipment` (не зберігаються в БД)

| Атрибут | Правило | Де реалізовано |
|---|---|---|
| `last_inspection_at` | `MAX(inspections.performed_at)` | `apps/equipment/services.py::get_last_inspection_at` (анотація `with_last_inspection` проти N+1) |
| `next_inspection_at` | `last_inspection_at + inspection_interval_days`; якщо оглядів не було — `purchase_date + interval`; інакше `None` | `get_next_inspection_at` |
| `is_inspection_overdue` | `next_inspection_at < today` | `is_inspection_overdue` |
| `is_warranty_expiring` | `today <= warranty_until <= today + 30 днів` | `is_warranty_expiring` |

## Міграції

| Файл | Зміст |
|---|---|
| `0001_initial` | Category, Location, Equipment, HistoricalEquipment |
| `0002_groups` | data: групи `Technician`, `Employee` + права на equipment-моделі |
| `0003_incident_inspection` | Inspection, Incident |
| `0004_groups_maintenance` | data: права груп на Inspection/Incident |
| `0005_alter_historicalequipment_options` | українська назва історії |
| `0006_technician_inspection_readonly` | data: технік — лише створення/перегляд оглядів |

Групи і права відтворюються на порожній БД командою `migrate` (виконується в entrypoint контейнера).
