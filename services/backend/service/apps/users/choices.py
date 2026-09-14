from django.db import models


class Role(models.TextChoices):
    TECHNICIAN = 'technician', 'Технік'
    EMPLOYEE = 'employee', 'Працівник'


# Names of the Django Groups used to implement roles (see apps/migrations/0002_groups.py).
GROUP_TECHNICIAN = 'Technician'
GROUP_EMPLOYEE = 'Employee'
