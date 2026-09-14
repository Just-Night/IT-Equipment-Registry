import csv
import io

import pytest
from django.urls import reverse

from tests.factories import EquipmentFactory, IncidentFactory, InspectionFactory

pytestmark = pytest.mark.django_db

EQUIPMENT_EXPORT_URL = 'admin_site:apps_equipment_export'
INSPECTION_EXPORT_URL = 'admin_site:apps_inspection_export'
INCIDENT_EXPORT_URL = 'admin_site:apps_incident_export'

CSV_FORMAT = '0'
XLSX_FORMAT = '1'
XLSX_CONTENT_TYPE = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


def test_superuser_export_equipment_csv_has_expected_header_and_rows(client, admin_user):
    equipment = EquipmentFactory(inventory_number='INV-EXPORT-1')

    client.force_login(admin_user)
    response = client.post(reverse(EQUIPMENT_EXPORT_URL), {'format': CSV_FORMAT})

    assert response.status_code == 200
    assert response['Content-Type'].startswith('text/csv')

    content = response.content.decode('utf-8-sig')
    rows = list(csv.reader(io.StringIO(content)))
    header = rows[0]

    assert header == [
        'Інвентарний номер',
        'Назва',
        'Категорія',
        'Локація',
        'Виробник',
        'Модель',
        'Серійний номер',
        'Дата придбання',
        'Гарантія до',
        'Статус',
        'Закріплено за',
        'Інтервал оглядів (днів)',
        'Примітка',
    ]
    data_rows = rows[1:]
    assert any(row[0] == 'INV-EXPORT-1' for row in data_rows)


def test_superuser_export_equipment_xlsx_content_type(client, admin_user):
    EquipmentFactory()

    client.force_login(admin_user)
    response = client.post(reverse(EQUIPMENT_EXPORT_URL), {'format': XLSX_FORMAT})

    assert response.status_code == 200
    assert response['Content-Type'] == XLSX_CONTENT_TYPE


def test_superuser_export_inspection_and_incident_csv(client, admin_user):
    InspectionFactory()
    IncidentFactory()

    client.force_login(admin_user)

    response = client.post(reverse(INSPECTION_EXPORT_URL), {'format': CSV_FORMAT})
    assert response.status_code == 200
    header = next(csv.reader(io.StringIO(response.content.decode('utf-8-sig'))))
    assert header == ['Обладнання', 'Виконав', 'Дата проведення', 'Стан', 'Коментар']

    response = client.post(reverse(INCIDENT_EXPORT_URL), {'format': CSV_FORMAT})
    assert response.status_code == 200
    header = next(csv.reader(io.StringIO(response.content.decode('utf-8-sig'))))
    assert header == [
        'Обладнання',
        'Повідомив',
        'Призначено',
        'Опис',
        'Статус',
        'Дата вирішення',
        'Рішення',
    ]


def test_technician_can_export_equipment(client, technician_user):
    EquipmentFactory()
    client.force_login(technician_user)

    response = client.post(reverse(EQUIPMENT_EXPORT_URL), {'format': CSV_FORMAT})

    assert response.status_code == 200
    assert response['Content-Type'].startswith('text/csv')


def test_employee_cannot_export_equipment(client, employee_user):
    EquipmentFactory()
    client.force_login(employee_user)

    get_response = client.get(reverse(EQUIPMENT_EXPORT_URL))
    post_response = client.post(reverse(EQUIPMENT_EXPORT_URL), {'format': CSV_FORMAT})

    assert get_response.status_code == 403
    assert post_response.status_code == 403


def test_employee_export_action_absent_from_changelist(client, employee_user):
    client.force_login(employee_user)
    response = client.get(reverse('admin_site:apps_equipment_changelist'))

    assert response.status_code == 200
    assert 'has_export_permission' in response.context
    assert response.context['has_export_permission'] is False
