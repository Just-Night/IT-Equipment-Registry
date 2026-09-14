import pytest
from django.core.management import call_command
from django.urls import reverse

from apps.equipment.models import Equipment
from apps.maintenance.models import Incident, Inspection
from tests.factories import EquipmentFactory

pytestmark = pytest.mark.django_db

CHANGELIST_URL_NAMES = [
    'admin_site:apps_category_changelist',
    'admin_site:apps_location_changelist',
    'admin_site:apps_equipment_changelist',
    'admin_site:apps_inspection_changelist',
    'admin_site:apps_incident_changelist',
]


def test_superuser_sees_all_changelists(client, admin_user):
    client.force_login(admin_user)
    for url_name in CHANGELIST_URL_NAMES:
        response = client.get(reverse(url_name))
        assert response.status_code == 200, url_name


def test_employee_sees_only_own_equipment(client, employee_user):
    own = EquipmentFactory(inventory_number='INV-OWN-1', assigned_to=employee_user)
    other = EquipmentFactory(inventory_number='INV-OTHER-1', assigned_to=None)

    client.force_login(employee_user)
    response = client.get(reverse('admin_site:apps_equipment_changelist'))

    assert response.status_code == 200
    content = response.content.decode()
    assert own.inventory_number in content
    assert other.inventory_number not in content


def test_employee_cannot_open_inspection_changelist(client, employee_user):
    client.force_login(employee_user)
    response = client.get(reverse('admin_site:apps_inspection_changelist'))
    assert response.status_code == 403


def test_technician_can_open_equipment_changelist_and_inspection_add(client, technician_user):
    client.force_login(technician_user)

    response = client.get(reverse('admin_site:apps_equipment_changelist'))
    assert response.status_code == 200

    response = client.get(reverse('admin_site:apps_inspection_add'))
    assert response.status_code == 200


def test_equipment_history_and_change_pages(client, admin_user):
    equipment = EquipmentFactory()
    client.force_login(admin_user)

    response = client.get(reverse('admin_site:apps_equipment_change', args=[equipment.pk]))
    assert response.status_code == 200

    response = client.get(reverse('admin_site:apps_equipment_history', args=[equipment.pk]))
    assert response.status_code == 200


def test_seed_demo_data_creates_expected_counts():
    call_command('seed_demo_data')

    assert Equipment.objects.count() == 25
    assert Inspection.objects.count() == 40
    assert Incident.objects.count() == 16

    # Second run without --force is a no-op.
    call_command('seed_demo_data')
    assert Equipment.objects.count() == 25


def test_employee_incident_inline_shows_only_own_reports(client, employee_user):
    from tests.factories import IncidentFactory, UserFactory

    equipment = EquipmentFactory(assigned_to=employee_user)
    IncidentFactory(equipment=equipment, reported_by=employee_user, description='MY-INCIDENT')
    IncidentFactory(equipment=equipment, reported_by=UserFactory(), description='FOREIGN-INCIDENT')

    client.force_login(employee_user)
    response = client.get(reverse('admin_site:apps_equipment_change', args=[equipment.pk]))

    assert response.status_code == 200
    content = response.content.decode()
    assert 'MY-INCIDENT' in content
    assert 'FOREIGN-INCIDENT' not in content


def test_technician_cannot_change_or_delete_inspection(client, technician_user):
    from tests.factories import InspectionFactory

    inspection = InspectionFactory()
    client.force_login(technician_user)

    response = client.get(reverse('admin_site:apps_inspection_delete', args=[inspection.pk]))
    assert response.status_code == 403

    response = client.post(
        reverse('admin_site:apps_inspection_change', args=[inspection.pk]),
        {'comment': 'hacked'},
    )
    assert response.status_code == 403
