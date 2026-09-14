import pytest
from django.urls import reverse

from tests.factories import EquipmentFactory, InspectionFactory

pytestmark = pytest.mark.django_db

EQUIPMENT_CARD_URL = 'admin_site:apps_equipment_equipment_card_pdf_action'
INSPECTION_ACT_URL = 'admin_site:apps_inspection_inspection_act_pdf_action'
SUMMARY_PDF_URL = 'admin_site:reports_summary_pdf'


def _pdf_url(name, obj):
    return reverse(name, args=[obj.pk])


def test_superuser_gets_equipment_card_pdf(client, admin_user):
    equipment = EquipmentFactory(inventory_number='INV-CARD-1')

    client.force_login(admin_user)
    response = client.get(_pdf_url(EQUIPMENT_CARD_URL, equipment))

    assert response.status_code == 200
    assert response['Content-Type'] == 'application/pdf'
    assert b'%PDF' in response.content[:10]
    assert 'INV-CARD-1' in response['Content-Disposition']


def test_technician_gets_equipment_card_pdf(client, technician_user):
    equipment = EquipmentFactory()

    client.force_login(technician_user)
    response = client.get(_pdf_url(EQUIPMENT_CARD_URL, equipment))

    assert response.status_code == 200
    assert response['Content-Type'] == 'application/pdf'


def test_employee_gets_own_equipment_card_pdf(client, employee_user):
    own = EquipmentFactory(inventory_number='INV-OWN-CARD', assigned_to=employee_user)

    client.force_login(employee_user)
    response = client.get(_pdf_url(EQUIPMENT_CARD_URL, own))

    assert response.status_code == 200
    assert response['Content-Type'] == 'application/pdf'


def test_employee_cannot_get_foreign_equipment_card_pdf(client, employee_user):
    foreign = EquipmentFactory(inventory_number='INV-FOREIGN-CARD', assigned_to=None)

    client.force_login(employee_user)
    response = client.get(_pdf_url(EQUIPMENT_CARD_URL, foreign))

    assert response.status_code == 404


def test_superuser_gets_inspection_act_pdf(client, admin_user):
    inspection = InspectionFactory()

    client.force_login(admin_user)
    response = client.get(_pdf_url(INSPECTION_ACT_URL, inspection))

    assert response.status_code == 200
    assert response['Content-Type'] == 'application/pdf'


def test_technician_gets_inspection_act_pdf(client, technician_user):
    inspection = InspectionFactory()

    client.force_login(technician_user)
    response = client.get(_pdf_url(INSPECTION_ACT_URL, inspection))

    assert response.status_code == 200
    assert response['Content-Type'] == 'application/pdf'


def test_employee_cannot_get_any_inspection_act_pdf(client, employee_user):
    # Employees have no `view_inspection` permission at all (PLAN.md §1) —
    # this is a 403 (permission), not a 404 (object scoping).
    inspection = InspectionFactory()

    client.force_login(employee_user)
    response = client.get(_pdf_url(INSPECTION_ACT_URL, inspection))

    assert response.status_code == 403


def test_dashboard_summary_pdf_200_for_all_three_roles(client, admin_user, technician_user, employee_user):
    for user in (admin_user, technician_user, employee_user):
        client.force_login(user)
        response = client.get(reverse(SUMMARY_PDF_URL))

        assert response.status_code == 200, user
        assert response['Content-Type'] == 'application/pdf'
        assert b'%PDF' in response.content[:10]
