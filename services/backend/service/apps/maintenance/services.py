"""Business logic for `Incident`/`Inspection` side effects (PLAN.md §2 "Побічні ефекти").

Status transitions are triggered from `Incident._pre_create`/`_pre_update`
(see `apps/maintenance/models.py`) — no `save()` overrides, no signals.
"""
from django.utils import timezone

from apps.equipment import services as equipment_services
from apps.equipment.choices import EquipmentStatus
from apps.maintenance.choices import IncidentStatus

OPEN_STATUSES = (IncidentStatus.NEW, IncidentStatus.IN_PROGRESS)
CLOSED_STATUSES = (IncidentStatus.RESOLVED, IncidentStatus.CLOSED)


def has_open_incidents(equipment, exclude_pk=None) -> bool:
    """True if `equipment` has other incidents still in NEW/IN_PROGRESS."""
    from apps.maintenance.models import Incident

    qs = Incident.objects.filter(equipment=equipment, status__in=OPEN_STATUSES)
    if exclude_pk is not None:
        qs = qs.exclude(pk=exclude_pk)
    return qs.exists()


def _set_equipment_status(equipment, status):
    """Change equipment status, unless it is decommissioned (terminal state)."""
    if equipment.status == EquipmentStatus.DECOMMISSIONED:
        return
    equipment_services.set_status(equipment, status)


def on_incident_created(incident):
    """New `Incident` → equipment becomes `faulty` (unless decommissioned)."""
    _set_equipment_status(incident.equipment, EquipmentStatus.FAULTY)


def on_incident_status_changed(incident, old_status):
    """React to an `Incident.status` transition.

    `old_status` is the value as it was in the DB before this save (see
    `Incident._pre_update`); if it equals the new (in-memory) status, this
    is a save of some other field and nothing here should run.
    """
    new_status = incident.status
    if old_status == new_status:
        return

    closing = old_status not in CLOSED_STATUSES and new_status in CLOSED_STATUSES
    reopening = old_status in CLOSED_STATUSES and new_status in OPEN_STATUSES

    if closing:
        if not incident.resolved_at:
            incident.resolved_at = timezone.now()
        if not has_open_incidents(incident.equipment, exclude_pk=incident.pk):
            _set_equipment_status(incident.equipment, EquipmentStatus.ACTIVE)
        return

    if reopening:
        incident.resolved_at = None
        if new_status == IncidentStatus.IN_PROGRESS:
            _set_equipment_status(incident.equipment, EquipmentStatus.IN_REPAIR)
        else:
            _set_equipment_status(incident.equipment, EquipmentStatus.FAULTY)
        return

    if old_status == IncidentStatus.NEW and new_status == IncidentStatus.IN_PROGRESS:
        _set_equipment_status(incident.equipment, EquipmentStatus.IN_REPAIR)
