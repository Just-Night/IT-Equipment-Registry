import datetime

import pytest

from apps.maintenance.choices import IncidentStatus, InspectionCondition
from apps.maintenance.models import Incident, Inspection
from tests.factories import EquipmentFactory, IncidentFactory, InspectionFactory


@pytest.mark.django_db
def test_inspection_str():
    equipment = EquipmentFactory(inventory_number='INV-00001', name='Монітор Dell')
    performed_at = datetime.datetime(2026, 1, 15, 10, 0, tzinfo=datetime.timezone.utc)
    inspection = InspectionFactory(equipment=equipment, performed_at=performed_at)
    assert str(inspection) == 'Огляд INV-00001 — Монітор Dell від 2026-01-15'


@pytest.mark.django_db
def test_inspection_default_condition():
    inspection = InspectionFactory()
    assert inspection.condition == InspectionCondition.GOOD


@pytest.mark.django_db
def test_inspection_ordering_newest_first():
    equipment = EquipmentFactory()
    older = InspectionFactory(equipment=equipment, performed_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc))
    newer = InspectionFactory(equipment=equipment, performed_at=datetime.datetime(2026, 2, 1, tzinfo=datetime.timezone.utc))

    assert list(Inspection.objects.filter(equipment=equipment)) == [newer, older]


@pytest.mark.django_db
def test_incident_str():
    equipment = EquipmentFactory(inventory_number='INV-00002', name='Сервер HP')
    incident = IncidentFactory(equipment=equipment, status=IncidentStatus.NEW)
    assert str(incident) == 'Заявка по INV-00002 — Сервер HP (Нова)'


@pytest.mark.django_db
def test_incident_default_status():
    incident = IncidentFactory()
    assert incident.status == IncidentStatus.NEW


@pytest.mark.django_db
def test_incident_ordering_newest_first():
    older = IncidentFactory()
    newer = IncidentFactory()

    assert list(Incident.objects.all())[:2] == [newer, older]
