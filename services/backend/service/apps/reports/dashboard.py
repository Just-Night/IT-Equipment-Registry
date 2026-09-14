"""Admin dashboard KPI callback (PLAN.md §4.2).

Wired via `UNFOLD["DASHBOARD_CALLBACK"]` (`settings/settings.py`). This is
presentation glue only — all numbers come from `apps.reports.services`
(which itself reuses `apps.equipment.services`); nothing here computes
overdue/warranty logic.

`unfold.sites.UnfoldAdminSite.index()` calls
`dashboard_callback(request, context)` and uses whatever it returns as the
*entire* template context, so this function must return the (mutated)
`context` it was given, not a fresh dict.

Role scoping (PLAN.md §1): an Employee only sees KPIs/tables for their own
equipment (`assigned_to=request.user`) and its incidents. Technician and
superuser see everything.
"""
import json

from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html

from apps.equipment.choices import EquipmentStatus
from apps.equipment.models import Equipment
from apps.maintenance.choices import IncidentStatus
from apps.maintenance.models import Incident, Inspection
from apps.reports import services
from apps.users.permissions import is_employee


def _equipment_link(equipment):
    url = reverse('admin_site:apps_equipment_change', args=[equipment.pk])
    return format_html('<a href="{}">{}</a>', url, equipment.inventory_number)


def _open_button(url, text='Відкрити'):
    return format_html(
        '<a class="btn-open" href="{}"><span class="material-symbols-outlined">open_in_new</span>{}</a>', url, text
    )


def _incident_link(incident):
    return _open_button(reverse('admin_site:apps_incident_change', args=[incident.pk]))


def _equipment_button(equipment):
    return _open_button(reverse('admin_site:apps_equipment_change', args=[equipment.pk]))


def _date(value):
    return value.strftime('%d.%m.%Y') if value else '—'


# Badge colors map to `.badge-*` classes in `templates/admin/index.html`.
INCIDENT_BADGES = {
    IncidentStatus.NEW: 'info',
    IncidentStatus.IN_PROGRESS: 'warning',
    IncidentStatus.RESOLVED: 'success',
    IncidentStatus.CLOSED: 'success',
}


def _badge(text, kind):
    return format_html('<span class="badge badge-{}">{}</span>', kind, text)


def _overdue_date(value):
    """Overdue date: always red — this table only lists overdue equipment."""
    return format_html('<span class="date-danger">{}</span>', _date(value))


def _warranty_date(value, today):
    days_left = (value - today).days if value else None
    kind = 'danger' if days_left is not None and days_left <= 7 else 'warning'
    return format_html('<span class="date-{}">{} <small>({} дн.)</small></span>', kind, _date(value), days_left)


def _user_label(user):
    return user.get_username() if user else '—'


def get_scoped_querysets(user):
    """Role-scoped `(equipment_qs, incident_qs)` (PLAN.md §1).

    An Employee only sees their own equipment (`assigned_to=user`) and its
    incidents; Technician/superuser see everything. Shared by
    `dashboard_callback` (this module) and
    `apps.reports.pdf.dashboard_summary_pdf` — one place decides Employee
    scoping so the PDF summary and the on-screen dashboard can never drift
    apart.
    """
    scoped_to_own_equipment = not user.is_superuser and is_employee(user)

    equipment_qs = Equipment.objects.all()
    incident_qs = Incident.objects.all()
    if scoped_to_own_equipment:
        equipment_qs = equipment_qs.filter(assigned_to=user)
        incident_qs = incident_qs.filter(equipment__in=equipment_qs)
    return equipment_qs, incident_qs


def dashboard_callback(request, context):
    user = request.user
    equipment_qs, incident_qs = get_scoped_querysets(user)

    summary = services.get_summary(equipment_qs=equipment_qs)
    overdue_equipment = services.get_overdue_equipment(equipment_qs=equipment_qs)
    warranty_equipment = services.get_warranty_expiring_equipment(equipment_qs=equipment_qs)
    open_incidents = services.get_open_incidents(incident_qs=incident_qs)

    # `color` → `.kpi-<color>` accent class in `templates/admin/index.html`.
    kpi_cards = [
        {'title': 'Всього обладнання', 'value': summary['equipment_total'], 'icon': 'devices', 'color': 'primary'},
        {
            'title': 'Активне',
            'value': summary['equipment_by_status'][EquipmentStatus.ACTIVE],
            'icon': 'check_circle',
            'color': 'success',
        },
        {
            'title': 'Несправне',
            'value': summary['equipment_by_status'][EquipmentStatus.FAULTY],
            'icon': 'error',
            'color': 'danger',
        },
        {'title': 'Відкриті заявки', 'value': summary['open_incidents'], 'icon': 'report', 'color': 'warning'},
        {'title': 'Прострочені огляди', 'value': summary['overdue_inspections'], 'icon': 'schedule', 'color': 'rose'},
        {
            'title': 'Гарантія спливає до 30 днів',
            'value': summary['warranty_expiring'],
            'icon': 'verified',
            'color': 'info',
        },
    ]
    today = timezone.localdate()

    overdue_table = {
        'headers': ['Інв. номер', 'Назва', 'Наступний огляд', 'Закріплено за', ''],
        'rows': [
            [
                _equipment_link(equipment),
                equipment.name,
                _overdue_date(equipment.next_inspection_at),
                _user_label(equipment.assigned_to),
                _equipment_button(equipment),
            ]
            for equipment in overdue_equipment
        ],
    }

    incidents_table = {
        'headers': ['Обладнання', 'Опис', 'Статус', 'Створено', ''],
        'rows': [
            [
                _equipment_link(incident.equipment),
                incident.description[:60],
                _badge(incident.get_status_display(), INCIDENT_BADGES.get(incident.status, 'muted')),
                _date(incident.created_at),
                _incident_link(incident),
            ]
            for incident in open_incidents
        ],
    }

    warranty_table = {
        'headers': ['Інв. номер', 'Назва', 'Гарантія до', 'Закріплено за', ''],
        'rows': [
            [
                _equipment_link(equipment),
                equipment.name,
                _warranty_date(equipment.warranty_until, today),
                _user_label(equipment.assigned_to),
                _equipment_button(equipment),
            ]
            for equipment in warranty_equipment
        ],
    }

    report_tables = [
        {'title': 'Прострочені огляди', 'icon': 'schedule', 'color': 'rose',
         'count': summary['overdue_inspections'], 'table': overdue_table},
        {'title': 'Відкриті заявки', 'icon': 'report', 'color': 'warning',
         'count': summary['open_incidents'], 'table': incidents_table},
        {'title': 'Гарантія спливає до 30 днів', 'icon': 'verified', 'color': 'info',
         'count': summary['warranty_expiring'], 'table': warranty_table},
    ]

    inspection_qs = Inspection.objects.filter(equipment__in=equipment_qs)
    months, incident_counts = zip(*services.get_incidents_by_month(incident_qs=incident_qs))
    _, inspection_counts = zip(*services.get_inspections_by_month(inspection_qs=inspection_qs))
    chart_data = json.dumps(
        {
            'labels': list(months),
            'datasets': [
                {
                    'label': 'Заявки',
                    'data': list(incident_counts),
                    'backgroundColor': 'rgba(249, 115, 22, 0.85)',
                    'borderColor': 'rgb(249, 115, 22)',
                    'borderRadius': 6,
                    'maxBarThickness': 28,
                },
                {
                    'label': 'Огляди',
                    'data': list(inspection_counts),
                    'backgroundColor': 'rgba(59, 130, 246, 0.75)',
                    'borderColor': 'rgb(59, 130, 246)',
                    'borderRadius': 6,
                    'maxBarThickness': 28,
                },
            ],
        }
    )

    context.update(
        {
            'kpi_cards': kpi_cards,
            'report_tables': report_tables,
            'chart_data': chart_data,
        }
    )
    return context
