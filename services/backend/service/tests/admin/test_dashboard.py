import datetime
import html

import pytest
from django.urls import reverse
from django.utils import timezone

from tests.factories import EquipmentFactory

pytestmark = pytest.mark.django_db

KPI_LABELS = [
    'Всього обладнання',
    'Відкриті заявки',
    'Прострочені огляди',
    'Гарантія спливає до 30 днів',
]


def _overdue_kwargs(inventory_number, **extra):
    kwargs = {
        'inventory_number': inventory_number,
        'purchase_date': timezone.localdate() - datetime.timedelta(days=400),
        'inspection_interval_days': 180,
    }
    kwargs.update(extra)
    return kwargs


def test_dashboard_returns_200_for_superuser(client, admin_user):
    client.force_login(admin_user)
    response = client.get(reverse('admin_site:index'))
    assert response.status_code == 200


def test_dashboard_returns_200_for_technician(client, technician_user):
    client.force_login(technician_user)
    response = client.get(reverse('admin_site:index'))
    assert response.status_code == 200


def test_dashboard_returns_200_for_employee(client, employee_user):
    client.force_login(employee_user)
    response = client.get(reverse('admin_site:index'))
    assert response.status_code == 200


def test_dashboard_shows_kpi_labels(client, admin_user):
    client.force_login(admin_user)
    response = client.get(reverse('admin_site:index'))
    content = response.content.decode()

    for label in KPI_LABELS:
        assert label in content, label


def test_dashboard_renders_chart_and_icons(client, admin_user):
    client.force_login(admin_user)
    response = client.get(reverse('admin_site:index'))
    content = response.content.decode()

    assert 'material-symbols-outlined' in content
    assert 'data-type="bar"' in content
    assert '"labels"' in html.unescape(content)
    assert 'Заявки та огляди за останні 12 місяців' in content


def test_dashboard_shows_ukrainian_empty_state(client, employee_user):
    # A freshly created employee has no equipment -> all three report tables are empty.
    client.force_login(employee_user)
    response = client.get(reverse('admin_site:index'))
    content = response.content.decode()

    assert response.status_code == 200
    assert 'Немає даних' in content


def test_employee_dashboard_hides_foreign_equipment(client, employee_user):
    own = EquipmentFactory(**_overdue_kwargs('INV-OWN-DASH', assigned_to=employee_user))
    foreign = EquipmentFactory(**_overdue_kwargs('INV-FOREIGN-DASH', assigned_to=None))

    client.force_login(employee_user)
    response = client.get(reverse('admin_site:index'))
    content = response.content.decode()

    assert response.status_code == 200
    assert own.inventory_number in content
    assert foreign.inventory_number not in content
