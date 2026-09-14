import pytest
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from apps.users.choices import GROUP_EMPLOYEE, GROUP_TECHNICIAN
from tests.factories import UserFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user(django_user_model):
    return django_user_model.objects.create_superuser(
        username='admin',
        email='admin@admin.com',
        password='admin',
    )


@pytest.fixture
def technician_user(db):
    user = UserFactory(username='technician', is_staff=True)
    group, _ = Group.objects.get_or_create(name=GROUP_TECHNICIAN)
    user.groups.add(group)
    return user


@pytest.fixture
def employee_user(db):
    user = UserFactory(username='employee', is_staff=True)
    group, _ = Group.objects.get_or_create(name=GROUP_EMPLOYEE)
    user.groups.add(group)
    return user
