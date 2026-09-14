"""Reports/dashboard business logic (PLAN.md §4.1, §4.2).

Pure functions over the ORM — no `request` objects here (role scoping is the
caller's job: `apps/reports/dashboard.py` passes an already-filtered
`equipment_qs`/`incident_qs` for an Employee, `None`/all otherwise).

All overdue/warranty computation is delegated to `apps.equipment.services`
(`is_inspection_overdue`, `is_warranty_expiring`, `get_next_inspection_at`) —
nothing here reimplements that logic. Like `apps.equipment.admin`'s
`OverdueInspectionFilter`, the overdue/warranty lookups are plain Python
loops over an already-narrowed queryset: these properties are computed, not
DB fields, and the dataset (dozens of equipment units, per PLAN.md's scope)
is small enough that this is simpler and more obviously correct than
reimplementing the interval math as SQL.
"""
import datetime

from django.db.models import Count
from django.db.models.functions import TruncMonth
from django.utils import timezone

from apps.equipment import services as equipment_services
from apps.equipment.choices import EquipmentStatus
from apps.equipment.models import Equipment
from apps.maintenance.models import Incident, Inspection
from apps.maintenance.services import OPEN_STATUSES


def get_summary(today=None, equipment_qs=None):
    """KPI dict for the dashboard/`/reports/summary/` (Stage 6).

    `equipment_qs` lets a caller scope the whole summary to a subset of
    equipment (e.g. an Employee's own equipment) — defaults to all
    equipment. Incidents are scoped to match: incidents of that equipment
    subset (or all incidents, when unscoped).
    """
    today = today or timezone.localdate()
    equipment_qs = Equipment.objects.all() if equipment_qs is None else equipment_qs

    equipment_total = equipment_qs.count()
    equipment_by_status = {
        status: equipment_qs.filter(status=status).count()
        for status, _label in EquipmentStatus.choices
    }

    incident_qs = Incident.objects.filter(equipment__in=equipment_qs)
    open_incidents = incident_qs.filter(status__in=OPEN_STATUSES).count()

    non_decommissioned = equipment_services.with_last_inspection(
        equipment_qs.exclude(status=EquipmentStatus.DECOMMISSIONED)
    )
    overdue_inspections = sum(
        1
        for equipment in non_decommissioned
        if equipment_services.is_inspection_overdue(equipment, today=today)
    )
    warranty_expiring = sum(
        1
        for equipment in non_decommissioned
        if equipment_services.is_warranty_expiring(equipment, today=today)
    )

    return {
        'equipment_total': equipment_total,
        'equipment_by_status': equipment_by_status,
        'open_incidents': open_incidents,
        'overdue_inspections': overdue_inspections,
        'warranty_expiring': warranty_expiring,
    }


def get_overdue_equipment(limit=10, equipment_qs=None, today=None):
    """Equipment with an overdue inspection, soonest-due first.

    `next_inspection_at` is a Python property (`apps.equipment.services`),
    not a DB column, so ordering happens in Python after filtering.
    """
    today = today or timezone.localdate()
    equipment_qs = Equipment.objects.all() if equipment_qs is None else equipment_qs

    candidates = equipment_services.with_last_inspection(
        equipment_qs.exclude(status=EquipmentStatus.DECOMMISSIONED)
        .select_related('category', 'location', 'assigned_to')
    )
    overdue = [
        equipment
        for equipment in candidates
        if equipment_services.is_inspection_overdue(equipment, today=today)
    ]
    overdue.sort(key=lambda equipment: equipment_services.get_next_inspection_at(equipment) or datetime.date.max)
    return overdue[:limit]


def get_open_incidents(limit=10, incident_qs=None):
    """Open (NEW/IN_PROGRESS) incidents, newest first."""
    incident_qs = Incident.objects.all() if incident_qs is None else incident_qs
    return (
        incident_qs.filter(status__in=OPEN_STATUSES)
        .select_related('equipment', 'assigned_to')
        .order_by('-created_at')[:limit]
    )


def get_warranty_expiring_equipment(limit=10, equipment_qs=None, today=None):
    """Equipment whose warranty expires within 30 days, soonest first."""
    today = today or timezone.localdate()
    equipment_qs = Equipment.objects.all() if equipment_qs is None else equipment_qs

    candidates = equipment_qs.exclude(status=EquipmentStatus.DECOMMISSIONED).select_related(
        'category', 'location', 'assigned_to'
    )
    expiring = [
        equipment
        for equipment in candidates
        if equipment_services.is_warranty_expiring(equipment, today=today)
    ]
    expiring.sort(key=lambda equipment: equipment.warranty_until)
    return expiring[:limit]


def _last_n_months(months, today=None):
    """`months` `(year, month)` tuples, ascending, ending at the current month."""
    today = today or timezone.localdate()
    base_index = today.year * 12 + (today.month - 1)
    result = []
    for offset in range(months - 1, -1, -1):
        index = base_index - offset
        year, month = divmod(index, 12)
        result.append((year, month + 1))
    return result


def _counts_by_month(queryset, date_field, months, today=None):
    """`[(label, count), ...]` for `months` months, chart-ready (chronological, zero-filled)."""
    month_list = _last_n_months(months, today)
    counts = dict.fromkeys(month_list, 0)

    start_date = datetime.date(*month_list[0], 1)
    rows = (
        queryset.filter(**{f'{date_field}__date__gte': start_date})
        .annotate(month=TruncMonth(date_field))
        .values('month')
        .annotate(total=Count('pk'))
    )
    for row in rows:
        key = (row['month'].year, row['month'].month)
        if key in counts:
            counts[key] = row['total']

    return [(f'{month:02d}.{year}', counts[(year, month)]) for year, month in month_list]


def get_incidents_by_month(months=12, today=None, incident_qs=None):
    """Incident count per month (by `created_at`) for the last `months` months."""
    incident_qs = Incident.objects.all() if incident_qs is None else incident_qs
    return _counts_by_month(incident_qs, 'created_at', months, today)


def get_inspections_by_month(months=12, today=None, inspection_qs=None):
    """Inspection count per month (by `performed_at`) for the last `months` months."""
    inspection_qs = Inspection.objects.all() if inspection_qs is None else inspection_qs
    return _counts_by_month(inspection_qs, 'performed_at', months, today)
