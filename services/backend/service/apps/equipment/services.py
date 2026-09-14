"""Business logic for `Equipment` that does not belong in models/admin/views.

`get_last_inspection_at`/`get_next_inspection_at`/`is_inspection_overdue` use
the reverse relation `inspections` (`Inspection.equipment`,
`related_name='inspections'`, field `performed_at`).
"""
import datetime

from django.db.models import Max
from django.utils import timezone


LAST_INSPECTION_ANNOTATION = '_last_inspection_at'


def with_last_inspection(queryset):
    """Annotate `queryset` so `get_last_inspection_at` needs no extra query per row.

    Use this whenever many `Equipment` rows are checked for overdue
    inspections (dashboard, reports, admin filters) to avoid N+1 queries.
    """
    return queryset.annotate(**{LAST_INSPECTION_ANNOTATION: Max('inspections__performed_at')})


def get_last_inspection_at(equipment):
    """Latest `performed_at` among the equipment's inspections, or `None`.

    Prefers the `with_last_inspection` annotation when present; otherwise
    falls back to one aggregate query. Returns `None` when there are no
    inspections yet.
    """
    if hasattr(equipment, LAST_INSPECTION_ANNOTATION):
        return getattr(equipment, LAST_INSPECTION_ANNOTATION)
    inspections = getattr(equipment, 'inspections', None)
    if inspections is None:
        return None
    return inspections.aggregate(last=Max('performed_at'))['last']


def get_next_inspection_at(equipment):
    """Date the next inspection is due.

    `last_inspection_at + inspection_interval_days` if there was at least
    one inspection, otherwise `purchase_date + inspection_interval_days` if
    `purchase_date` is set, otherwise `None`.
    """
    interval = datetime.timedelta(days=equipment.inspection_interval_days)
    last_inspection_at = get_last_inspection_at(equipment)
    if last_inspection_at is not None:
        if isinstance(last_inspection_at, datetime.datetime):
            last_inspection_at = timezone.localtime(last_inspection_at).date()
        return last_inspection_at + interval
    if equipment.purchase_date:
        return equipment.purchase_date + interval
    return None


def is_inspection_overdue(equipment, today=None) -> bool:
    """True if the next inspection date has already passed."""
    today = today or timezone.localdate()
    next_inspection_at = get_next_inspection_at(equipment)
    if next_inspection_at is None:
        return False
    return next_inspection_at < today


def is_warranty_expiring(equipment, today=None, days=30) -> bool:
    """True if `warranty_until` is set and falls within `[today, today + days]`."""
    if not equipment.warranty_until:
        return False
    today = today or timezone.localdate()
    return today <= equipment.warranty_until <= today + datetime.timedelta(days=days)


def set_status(equipment, status, save=True):
    """Change `equipment.status` (single point for status transitions)."""
    equipment.status = status
    if save:
        equipment.save(update_fields=['status', 'updated_at'])
    return equipment
