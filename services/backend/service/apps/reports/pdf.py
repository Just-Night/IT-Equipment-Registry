"""PDF report rendering (Stage 4b) — WeasyPrint HTML → PDF.

`render_pdf` is the only place that touches WeasyPrint; everything else in
this module builds a plain template context and hands it off. Templates
live in `templates/reports/` (`base_pdf.html` + one template per report).

This is presentation glue only — role scoping and business data come from
`apps.reports.services` / `apps.equipment.services` /
`apps.reports.dashboard.get_scoped_querysets`; nothing here decides who can
see what (that is the caller's job: the admin actions in
`apps/equipment/admin.py` / `apps/maintenance/admin.py`, and the summary
view in `apps/reports/views.py`, which use `ModelAdmin.get_queryset(request)`
/ `get_scoped_querysets(user)` before ever calling into this module).
"""
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone

from weasyprint import HTML

from apps.equipment import services as equipment_services
from apps.equipment.choices import EquipmentStatus
from apps.maintenance.choices import IncidentStatus, InspectionCondition
from apps.maintenance.models import Inspection
from apps.reports import services
from apps.reports.dashboard import get_scoped_querysets

# Same color vocabulary as the admin list `@display(label={...})` badges
# (`apps/equipment/admin.py::STATUS_LABELS`,
# `apps/maintenance/admin.py::CONDITION_LABELS`/`INCIDENT_STATUS_LABELS`) —
# duplicated here rather than imported to avoid a circular import (those
# admin modules import `apps.reports.pdf` for the PDF actions).
EQUIPMENT_STATUS_BADGES = {
    EquipmentStatus.ACTIVE: 'success',
    EquipmentStatus.FAULTY: 'danger',
    EquipmentStatus.IN_REPAIR: 'warning',
    EquipmentStatus.DECOMMISSIONED: 'info',
}
INSPECTION_CONDITION_BADGES = {
    InspectionCondition.GOOD: 'success',
    InspectionCondition.SATISFACTORY: 'warning',
    InspectionCondition.POOR: 'danger',
}
INCIDENT_STATUS_BADGES = {
    IncidentStatus.NEW: 'info',
    IncidentStatus.IN_PROGRESS: 'warning',
    IncidentStatus.RESOLVED: 'success',
    IncidentStatus.CLOSED: 'success',
}

HISTORY_TYPE_LABELS = {
    '+': 'Створено',
    '~': 'Змінено',
    '-': 'Видалено',
}


def render_pdf(template_name, context) -> bytes:
    """Render `template_name` with `context` to PDF bytes via WeasyPrint."""
    html_string = render_to_string(template_name, context)
    return HTML(string=html_string, base_url=str(settings.BASE_DIR)).write_pdf()


def _date(value):
    return value.strftime('%d.%m.%Y') if value else '—'


def _datetime(value):
    if not value:
        return '—'
    if timezone.is_aware(value):
        value = timezone.localtime(value)
    return value.strftime('%d.%m.%Y %H:%M')


def _user_label(user):
    return user.get_username() if user else '—'


def _base_context(user, title):
    return {
        'project_name': settings.PROJECT_NAME,
        'report_title': title,
        'generated_at': _datetime(timezone.now()),
        'generated_by': _user_label(user),
    }


def equipment_card_pdf(equipment, user=None) -> bytes:
    """"Картка обладнання" — full equipment attribute sheet, inspections,
    incidents, and status-change history."""
    today = timezone.localdate()

    inspections = equipment.inspections.select_related('performed_by').order_by('-performed_at')[:10]
    inspection_rows = [
        {
            'performed_at': _datetime(inspection.performed_at),
            'performed_by': _user_label(inspection.performed_by),
            'condition': inspection.get_condition_display(),
            'condition_code': INSPECTION_CONDITION_BADGES.get(inspection.condition, 'info'),
            'comment': inspection.comment or '—',
        }
        for inspection in inspections
    ]

    incidents = equipment.incidents.select_related('reported_by', 'assigned_to').order_by('-created_at')
    incident_rows = [
        {
            'created_at': _datetime(incident.created_at),
            'status': incident.get_status_display(),
            'status_code': INCIDENT_STATUS_BADGES.get(incident.status, 'info'),
            'reported_by': _user_label(incident.reported_by),
            'assigned_to': _user_label(incident.assigned_to),
            'description': incident.description,
            'resolved_at': _datetime(incident.resolved_at),
            'resolution': incident.resolution or '—',
        }
        for incident in incidents
    ]

    history_rows = [
        {
            'date': _datetime(record.history_date),
            'user': _user_label(record.history_user),
            'type': HISTORY_TYPE_LABELS.get(record.history_type, record.history_type),
            'status': record.get_status_display(),
        }
        for record in equipment.history.select_related('history_user').order_by('-history_date')[:10]
    ]

    context = _base_context(user, f'Картка обладнання №{equipment.inventory_number}')
    context.update(
        {
            'equipment': equipment,
            'status_code': EQUIPMENT_STATUS_BADGES.get(equipment.status, 'info'),
            'last_inspection_at': _datetime(equipment_services.get_last_inspection_at(equipment)),
            'next_inspection_at': _date(equipment_services.get_next_inspection_at(equipment)),
            'is_inspection_overdue': equipment_services.is_inspection_overdue(equipment, today=today),
            'is_warranty_expiring': equipment_services.is_warranty_expiring(equipment, today=today),
            'purchase_date': _date(equipment.purchase_date),
            'warranty_until': _date(equipment.warranty_until),
            'assigned_to': _user_label(equipment.assigned_to),
            'inspections': inspection_rows,
            'incidents': incident_rows,
            'history': history_rows,
        }
    )
    return render_pdf('reports/equipment_card.html', context)


def inspection_act_pdf(inspection, user=None) -> bytes:
    """"Акт огляду №<short id> від <date>"."""
    act_number = str(inspection.pk).split('-')[0].upper()
    context = _base_context(user, f'Акт огляду №{act_number} від {_date(inspection.performed_at)}')
    context.update(
        {
            'inspection': inspection,
            'act_number': act_number,
            'equipment': inspection.equipment,
            'performed_at': _datetime(inspection.performed_at),
            'performed_by': _user_label(inspection.performed_by),
            'condition': inspection.get_condition_display(),
            'condition_code': INSPECTION_CONDITION_BADGES.get(inspection.condition, 'info'),
            'comment': inspection.comment or '—',
        }
    )
    return render_pdf('reports/inspection_act.html', context)


# Rows shown in the PDF summary's overdue/incidents/warranty tables — the
# on-screen dashboard caps these at 10 for a compact widget
# (`apps/reports/dashboard.py`); a printed report can afford to be complete
# for the small datasets this project deals with (PLAN.md's scope).
PDF_TABLE_LIMIT = 200


def dashboard_summary_pdf(user) -> bytes:
    """"Зведений звіт" — KPI table + the three report tables + a 12-month
    incidents/inspections table, scoped exactly like the admin dashboard
    (`apps.reports.dashboard.get_scoped_querysets`)."""
    today = timezone.localdate()
    equipment_qs, incident_qs = get_scoped_querysets(user)
    inspection_qs = Inspection.objects.filter(equipment__in=equipment_qs)

    summary = services.get_summary(equipment_qs=equipment_qs, today=today)
    overdue_equipment = services.get_overdue_equipment(equipment_qs=equipment_qs, limit=PDF_TABLE_LIMIT, today=today)
    open_incidents = services.get_open_incidents(incident_qs=incident_qs, limit=PDF_TABLE_LIMIT)
    warranty_equipment = services.get_warranty_expiring_equipment(
        equipment_qs=equipment_qs, limit=PDF_TABLE_LIMIT, today=today
    )

    # (label, value, color) — color maps to `.kpi-card.kpi-<color>` in the template.
    kpi_rows = [
        ('Всього обладнання', summary['equipment_total'], 'primary'),
        ('Активне', summary['equipment_by_status'].get('active', 0), 'success'),
        ('Несправне', summary['equipment_by_status'].get('faulty', 0), 'danger'),
        ('В ремонті', summary['equipment_by_status'].get('in_repair', 0), 'warning'),
        ('Списано', summary['equipment_by_status'].get('decommissioned', 0), 'muted'),
        ('Відкриті заявки', summary['open_incidents'], 'warning'),
        ('Прострочені огляди', summary['overdue_inspections'], 'danger'),
        ('Гарантія спливає до 30 днів', summary['warranty_expiring'], 'info'),
    ]

    overdue_rows = [
        {
            'inventory_number': equipment.inventory_number,
            'name': equipment.name,
            'next_inspection_at': _date(equipment_services.get_next_inspection_at(equipment)),
            'assigned_to': _user_label(equipment.assigned_to),
        }
        for equipment in overdue_equipment
    ]

    incident_rows = [
        {
            'inventory_number': incident.equipment.inventory_number,
            'description': incident.description[:80],
            'status': incident.get_status_display(),
            'status_code': INCIDENT_STATUS_BADGES.get(incident.status, 'info'),
            'created_at': _date(incident.created_at),
        }
        for incident in open_incidents
    ]

    warranty_rows = [
        {
            'inventory_number': equipment.inventory_number,
            'name': equipment.name,
            'warranty_until': _date(equipment.warranty_until),
            'days_left': (equipment.warranty_until - today).days if equipment.warranty_until else None,
            'assigned_to': _user_label(equipment.assigned_to),
        }
        for equipment in warranty_equipment
    ]

    months, incident_counts = zip(*services.get_incidents_by_month(incident_qs=incident_qs, today=today))
    _, inspection_counts = zip(*services.get_inspections_by_month(inspection_qs=inspection_qs, today=today))
    # Bar widths (0-100) let the template draw inline bars without JS.
    monthly_max = max([*incident_counts, *inspection_counts, 1])
    monthly_rows = [
        (month, inc, insp, round(inc * 100 / monthly_max), round(insp * 100 / monthly_max))
        for month, inc, insp in zip(months, incident_counts, inspection_counts)
    ]

    context = _base_context(user, 'Зведений звіт')
    context.update(
        {
            'kpi_rows': kpi_rows,
            'overdue_rows': overdue_rows,
            'incident_rows': incident_rows,
            'warranty_rows': warranty_rows,
            'monthly_rows': monthly_rows,
        }
    )
    return render_pdf('reports/dashboard_summary.html', context)
