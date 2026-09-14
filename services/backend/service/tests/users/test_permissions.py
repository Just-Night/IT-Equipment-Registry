import pytest
from django.contrib.auth.models import Group

from apps.users.choices import GROUP_EMPLOYEE, GROUP_TECHNICIAN
from apps.users.permissions import is_admin, is_employee, is_technician
from tests.factories import UserFactory


@pytest.mark.django_db
def test_groups_created_by_migration_exist():
    technician = Group.objects.get(name=GROUP_TECHNICIAN)
    employee = Group.objects.get(name=GROUP_EMPLOYEE)

    technician_codenames = set(technician.permissions.values_list('codename', flat=True))
    assert technician_codenames == {
        'view_category', 'view_location', 'view_equipment', 'change_equipment',
        'add_inspection', 'view_inspection',
        'add_incident', 'change_incident', 'view_incident',
    }

    employee_codenames = set(employee.permissions.values_list('codename', flat=True))
    assert employee_codenames == {'view_equipment', 'add_incident', 'view_incident'}


@pytest.mark.django_db
def test_is_technician(technician_user, employee_user):
    assert is_technician(technician_user) is True
    assert is_technician(employee_user) is False


@pytest.mark.django_db
def test_is_employee(technician_user, employee_user):
    assert is_employee(employee_user) is True
    assert is_employee(technician_user) is False


@pytest.mark.django_db
def test_is_admin():
    superuser = UserFactory(is_superuser=True)
    regular_user = UserFactory()

    assert is_admin(superuser) is True
    assert is_admin(regular_user) is False


@pytest.mark.django_db
def test_superuser_not_technician_or_employee_unless_in_group():
    superuser = UserFactory(is_superuser=True)

    assert is_technician(superuser) is False
    assert is_employee(superuser) is False
