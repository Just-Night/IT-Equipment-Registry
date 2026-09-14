import datetime

import pytest
from django.utils import timezone

from apps.equipment.choices import EquipmentStatus
from apps.equipment.models import Equipment
from apps.maintenance.choices import IncidentStatus
from apps.maintenance.models import Incident
from apps.reports import services
from tests.factories import EquipmentFactory, IncidentFactory

pytestmark = pytest.mark.django_db


def _days_ago(days):
    return timezone.localdate() - datetime.timedelta(days=days)


def _days_ahead(days):
    return timezone.localdate() + datetime.timedelta(days=days)


@pytest.fixture
def summary_fixture_set():
    """3 equipment (1 overdue, 1 warranty-expiring, 1 decommissioned-overdue-excluded)
    + 2 incidents (1 open, 1 resolved), per the Stage 4 task spec."""
    overdue_equipment = EquipmentFactory(
        inventory_number='INV-OVERDUE',
        purchase_date=_days_ago(400),
        inspection_interval_days=180,
        warranty_until=_days_ahead(400),  # far away — not warranty-expiring
    )
    warranty_equipment = EquipmentFactory(
        inventory_number='INV-WARRANTY',
        purchase_date=timezone.localdate(),
        inspection_interval_days=180,  # next inspection far in the future — not overdue
        warranty_until=_days_ahead(10),
    )
    decommissioned_overdue_equipment = EquipmentFactory(
        inventory_number='INV-DECOMMISSIONED',
        purchase_date=_days_ago(400),
        inspection_interval_days=180,
        warranty_until=_days_ahead(5),
        status=EquipmentStatus.DECOMMISSIONED,
    )

    open_incident = IncidentFactory(equipment=overdue_equipment, status=IncidentStatus.NEW)
    resolved_incident = IncidentFactory(equipment=warranty_equipment, status=IncidentStatus.NEW)
    resolved_incident.status = IncidentStatus.RESOLVED
    resolved_incident.save()

    return {
        'overdue_equipment': overdue_equipment,
        'warranty_equipment': warranty_equipment,
        'decommissioned_overdue_equipment': decommissioned_overdue_equipment,
        'open_incident': open_incident,
        'resolved_incident': resolved_incident,
    }


def test_get_summary_counts(summary_fixture_set):
    summary = services.get_summary()

    assert summary['equipment_total'] == 3
    assert set(summary['equipment_by_status'].keys()) == set(EquipmentStatus.values)
    assert sum(summary['equipment_by_status'].values()) == 3
    assert summary['open_incidents'] == 1
    # Only the non-decommissioned equipment counts as overdue.
    assert summary['overdue_inspections'] == 1
    assert summary['warranty_expiring'] == 1


def test_get_overdue_equipment_excludes_decommissioned(summary_fixture_set):
    overdue = services.get_overdue_equipment()
    inventory_numbers = [equipment.inventory_number for equipment in overdue]

    assert inventory_numbers == ['INV-OVERDUE']


def test_get_overdue_equipment_orders_ascending_by_next_inspection():
    more_overdue = EquipmentFactory(
        inventory_number='INV-MORE-OVERDUE',
        purchase_date=_days_ago(400),
        inspection_interval_days=180,
    )
    less_overdue = EquipmentFactory(
        inventory_number='INV-LESS-OVERDUE',
        purchase_date=_days_ago(200),
        inspection_interval_days=180,
    )

    overdue = services.get_overdue_equipment()

    assert [equipment.pk for equipment in overdue] == [more_overdue.pk, less_overdue.pk]


def test_get_warranty_expiring_equipment_excludes_decommissioned(summary_fixture_set):
    expiring = services.get_warranty_expiring_equipment()
    inventory_numbers = [equipment.inventory_number for equipment in expiring]

    assert inventory_numbers == ['INV-WARRANTY']


def test_get_open_incidents_only_new_and_in_progress(summary_fixture_set):
    open_incidents = services.get_open_incidents()

    assert list(open_incidents) == [summary_fixture_set['open_incident']]


def _expected_month_label(today, months_back):
    index = today.year * 12 + (today.month - 1) - months_back
    year, month = divmod(index, 12)
    return f'{month + 1:02d}.{year}'


def test_get_incidents_by_month_is_chronological_and_zero_filled():
    today = timezone.localdate()
    this_month_equipment = EquipmentFactory()
    IncidentFactory(equipment=this_month_equipment, status=IncidentStatus.NEW)

    result = services.get_incidents_by_month(months=3, today=today)

    assert len(result) == 3
    labels = [label for label, _count in result]
    # Ascending, current month last.
    assert labels[-1] == _expected_month_label(today, 0)
    assert labels[0] == _expected_month_label(today, 2)

    counts = dict(result)
    assert counts[_expected_month_label(today, 0)] == 1
    # Months with no incidents are present with count 0, not omitted.
    assert sum(counts.values()) == 1


def test_get_incidents_by_month_buckets_by_local_time():
    """A UTC timestamp that is already "next month" in Europe/Kyiv must be
    counted in the next month's bucket, not the UTC month.

    `2026-08-31 22:30 UTC` is `2026-09-01 01:30` in Europe/Kyiv (UTC+3,
    daylight saving in effect) — this incident must land in the September
    bucket, not August.
    """
    equipment = EquipmentFactory()
    incident = IncidentFactory(equipment=equipment, status=IncidentStatus.NEW)
    utc_last_day_of_august = datetime.datetime(2026, 8, 31, 22, 30, tzinfo=datetime.timezone.utc)
    incident.created_at = utc_last_day_of_august
    incident.save(update_fields=['created_at'])

    today = datetime.date(2026, 9, 13)
    result = services.get_incidents_by_month(months=3, today=today, incident_qs=Incident.objects.filter(pk=incident.pk))
    counts = dict(result)

    assert counts['08.2026'] == 0
    assert counts['09.2026'] == 1


def test_get_inspections_by_month_counts_current_month():
    from tests.factories import InspectionFactory

    today = timezone.localdate()
    InspectionFactory(performed_at=timezone.now())

    result = services.get_inspections_by_month(months=6, today=today)
    counts = dict(result)

    assert counts[f'{today.month:02d}.{today.year}'] == 1


def test_get_summary_scoped_to_employee_equipment(employee_user):
    own_equipment = EquipmentFactory(
        inventory_number='INV-OWN',
        assigned_to=employee_user,
        purchase_date=_days_ago(400),
        inspection_interval_days=180,
    )
    EquipmentFactory(
        inventory_number='INV-FOREIGN',
        assigned_to=None,
        purchase_date=_days_ago(400),
        inspection_interval_days=180,
    )

    scoped_qs = Equipment.objects.filter(assigned_to=employee_user)
    summary = services.get_summary(equipment_qs=scoped_qs)
    overdue = services.get_overdue_equipment(equipment_qs=scoped_qs)

    assert summary['equipment_total'] == 1
    assert summary['overdue_inspections'] == 1
    assert [equipment.pk for equipment in overdue] == [own_equipment.pk]
