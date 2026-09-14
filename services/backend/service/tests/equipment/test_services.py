import datetime

import pytest

from apps.equipment import services
from apps.equipment.choices import EquipmentStatus
from tests.factories import EquipmentFactory, InspectionFactory

TODAY = datetime.date(2026, 1, 15)


@pytest.mark.django_db
def test_get_next_inspection_at_without_purchase_date():
    equipment = EquipmentFactory(purchase_date=None, inspection_interval_days=180)
    assert services.get_next_inspection_at(equipment) is None


@pytest.mark.django_db
def test_get_next_inspection_at_with_purchase_date():
    equipment = EquipmentFactory(
        purchase_date=datetime.date(2026, 1, 1),
        inspection_interval_days=180,
    )
    assert services.get_next_inspection_at(equipment) == datetime.date(2026, 1, 1) + datetime.timedelta(days=180)


@pytest.mark.django_db
def test_is_inspection_overdue_true():
    equipment = EquipmentFactory(
        purchase_date=TODAY - datetime.timedelta(days=200),
        inspection_interval_days=180,
    )
    assert services.is_inspection_overdue(equipment, today=TODAY) is True


@pytest.mark.django_db
def test_is_inspection_overdue_false():
    equipment = EquipmentFactory(
        purchase_date=TODAY - datetime.timedelta(days=10),
        inspection_interval_days=180,
    )
    assert services.is_inspection_overdue(equipment, today=TODAY) is False


@pytest.mark.django_db
def test_is_inspection_overdue_no_purchase_date():
    equipment = EquipmentFactory(purchase_date=None)
    assert services.is_inspection_overdue(equipment, today=TODAY) is False


@pytest.mark.django_db
@pytest.mark.parametrize(
    'warranty_until,expected',
    [
        (None, False),
        (TODAY, True),
        (TODAY + datetime.timedelta(days=30), True),
        (TODAY + datetime.timedelta(days=31), False),
        (TODAY - datetime.timedelta(days=1), False),
    ],
)
def test_is_warranty_expiring_boundaries(warranty_until, expected):
    equipment = EquipmentFactory(warranty_until=warranty_until)
    assert services.is_warranty_expiring(equipment, today=TODAY, days=30) is expected


@pytest.mark.django_db
def test_set_status_saves_by_default():
    equipment = EquipmentFactory(status=EquipmentStatus.ACTIVE)
    services.set_status(equipment, EquipmentStatus.IN_REPAIR)

    equipment.refresh_from_db()
    assert equipment.status == EquipmentStatus.IN_REPAIR


@pytest.mark.django_db
def test_set_status_no_save():
    equipment = EquipmentFactory(status=EquipmentStatus.ACTIVE)
    services.set_status(equipment, EquipmentStatus.FAULTY, save=False)

    assert equipment.status == EquipmentStatus.FAULTY
    equipment.refresh_from_db()
    assert equipment.status == EquipmentStatus.ACTIVE


@pytest.mark.django_db
def test_get_last_inspection_at_uses_real_inspections():
    equipment = EquipmentFactory()
    assert services.get_last_inspection_at(equipment) is None

    InspectionFactory(equipment=equipment, performed_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc))
    latest = InspectionFactory(
        equipment=equipment, performed_at=datetime.datetime(2026, 1, 10, tzinfo=datetime.timezone.utc)
    )

    assert services.get_last_inspection_at(equipment) == latest.performed_at


@pytest.mark.django_db
def test_get_next_inspection_at_uses_latest_inspection_plus_interval():
    equipment = EquipmentFactory(
        purchase_date=datetime.date(2020, 1, 1),
        inspection_interval_days=180,
    )
    InspectionFactory(equipment=equipment, performed_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc))

    assert services.get_next_inspection_at(equipment) == datetime.date(2026, 1, 1) + datetime.timedelta(days=180)
