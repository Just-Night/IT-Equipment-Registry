import pytest

from apps.equipment.choices import EquipmentStatus
from apps.maintenance import services
from apps.maintenance.choices import IncidentStatus
from tests.factories import EquipmentFactory, IncidentFactory


@pytest.mark.django_db
def test_incident_created_makes_equipment_faulty():
    equipment = EquipmentFactory(status=EquipmentStatus.ACTIVE)
    IncidentFactory(equipment=equipment)

    equipment.refresh_from_db()
    assert equipment.status == EquipmentStatus.FAULTY


@pytest.mark.django_db
def test_incident_created_on_decommissioned_equipment_unchanged():
    equipment = EquipmentFactory(status=EquipmentStatus.DECOMMISSIONED)
    IncidentFactory(equipment=equipment)

    equipment.refresh_from_db()
    assert equipment.status == EquipmentStatus.DECOMMISSIONED


@pytest.mark.django_db
def test_incident_new_to_in_progress_sets_equipment_in_repair():
    equipment = EquipmentFactory(status=EquipmentStatus.ACTIVE)
    incident = IncidentFactory(equipment=equipment, status=IncidentStatus.NEW)

    incident.status = IncidentStatus.IN_PROGRESS
    incident.save()

    equipment.refresh_from_db()
    assert equipment.status == EquipmentStatus.IN_REPAIR


@pytest.mark.django_db
def test_incident_resolved_sets_equipment_active_and_resolved_at():
    equipment = EquipmentFactory(status=EquipmentStatus.ACTIVE)
    incident = IncidentFactory(equipment=equipment, status=IncidentStatus.NEW)
    assert incident.resolved_at is None

    incident.status = IncidentStatus.RESOLVED
    incident.save()
    incident.refresh_from_db()

    equipment.refresh_from_db()
    assert equipment.status == EquipmentStatus.ACTIVE
    assert incident.resolved_at is not None


@pytest.mark.django_db
def test_incident_resolved_with_other_open_incident_keeps_equipment_status():
    equipment = EquipmentFactory(status=EquipmentStatus.ACTIVE)
    incident1 = IncidentFactory(equipment=equipment, status=IncidentStatus.NEW)
    IncidentFactory(equipment=equipment, status=IncidentStatus.NEW)

    equipment.refresh_from_db()
    assert equipment.status == EquipmentStatus.FAULTY

    incident1.status = IncidentStatus.RESOLVED
    incident1.save()

    equipment.refresh_from_db()
    assert equipment.status == EquipmentStatus.FAULTY


@pytest.mark.django_db
def test_incident_reopened_clears_resolved_at_and_sets_equipment_faulty():
    equipment = EquipmentFactory(status=EquipmentStatus.ACTIVE)
    incident = IncidentFactory(equipment=equipment, status=IncidentStatus.NEW)

    incident.status = IncidentStatus.RESOLVED
    incident.save()
    equipment.refresh_from_db()
    assert equipment.status == EquipmentStatus.ACTIVE

    incident.status = IncidentStatus.NEW
    incident.save()
    incident.refresh_from_db()

    equipment.refresh_from_db()
    assert incident.resolved_at is None
    assert equipment.status == EquipmentStatus.FAULTY


@pytest.mark.django_db
def test_incident_reopened_to_in_progress_sets_equipment_in_repair():
    equipment = EquipmentFactory(status=EquipmentStatus.ACTIVE)
    incident = IncidentFactory(equipment=equipment, status=IncidentStatus.NEW)

    incident.status = IncidentStatus.CLOSED
    incident.save()

    incident.status = IncidentStatus.IN_PROGRESS
    incident.save()

    equipment.refresh_from_db()
    assert equipment.status == EquipmentStatus.IN_REPAIR


@pytest.mark.django_db
def test_editing_non_status_field_does_not_touch_equipment():
    equipment = EquipmentFactory(status=EquipmentStatus.ACTIVE)
    incident = IncidentFactory(equipment=equipment, status=IncidentStatus.NEW)

    # Simulate a manual status change unrelated to the incident lifecycle.
    equipment.status = EquipmentStatus.ACTIVE
    equipment.save(update_fields=['status', 'updated_at'])

    incident.description = 'Оновлений опис'
    incident.save()

    equipment.refresh_from_db()
    assert equipment.status == EquipmentStatus.ACTIVE


@pytest.mark.django_db
def test_has_open_incidents():
    equipment = EquipmentFactory()
    incident = IncidentFactory(equipment=equipment, status=IncidentStatus.NEW)

    assert services.has_open_incidents(equipment) is True
    assert services.has_open_incidents(equipment, exclude_pk=incident.pk) is False
