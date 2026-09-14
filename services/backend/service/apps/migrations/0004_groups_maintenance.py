"""Extend `Technician`/`Employee` groups with Stage 2 (maintenance) permissions.

See `apps/migrations/0002_groups.py` for why this uses the real (global)
app registry instead of the migration's frozen `apps` state.
"""
from django.apps import apps as global_apps
from django.contrib.auth.management import create_permissions
from django.db import migrations

GROUP_TECHNICIAN = 'Technician'
GROUP_EMPLOYEE = 'Employee'

TECHNICIAN_INSPECTION_CODENAMES = ['add_inspection', 'change_inspection', 'view_inspection', 'delete_inspection']
TECHNICIAN_INCIDENT_CODENAMES = ['add_incident', 'change_incident', 'view_incident']
EMPLOYEE_INCIDENT_CODENAMES = ['add_incident', 'view_incident']


def add_permissions(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')
    ContentType = apps.get_model('contenttypes', 'ContentType')

    # Make sure Permission rows for `apps` models exist before we look them up.
    create_permissions(global_apps.get_app_config('apps'), verbosity=0)

    def perms(model_name, codenames):
        content_type = ContentType.objects.get_for_model(
            global_apps.get_model('apps', model_name), for_concrete_model=False
        )
        return Permission.objects.filter(content_type=content_type, codename__in=codenames)

    technician = Group.objects.get(name=GROUP_TECHNICIAN)
    technician.permissions.add(
        *perms('Inspection', TECHNICIAN_INSPECTION_CODENAMES),
        *perms('Incident', TECHNICIAN_INCIDENT_CODENAMES),
    )

    employee = Group.objects.get(name=GROUP_EMPLOYEE)
    employee.permissions.add(
        *perms('Incident', EMPLOYEE_INCIDENT_CODENAMES),
    )


def remove_permissions(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')
    ContentType = apps.get_model('contenttypes', 'ContentType')

    def perms(model_name, codenames):
        content_type = ContentType.objects.get_for_model(
            global_apps.get_model('apps', model_name), for_concrete_model=False
        )
        return Permission.objects.filter(content_type=content_type, codename__in=codenames)

    technician = Group.objects.filter(name=GROUP_TECHNICIAN).first()
    if technician:
        technician.permissions.remove(
            *perms('Inspection', TECHNICIAN_INSPECTION_CODENAMES),
            *perms('Incident', TECHNICIAN_INCIDENT_CODENAMES),
        )

    employee = Group.objects.filter(name=GROUP_EMPLOYEE).first()
    if employee:
        employee.permissions.remove(
            *perms('Incident', EMPLOYEE_INCIDENT_CODENAMES),
        )


class Migration(migrations.Migration):

    dependencies = [
        ('apps', '0003_incident_inspection'),
        ('auth', '0012_alter_user_first_name_max_length'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.RunPython(add_permissions, remove_permissions),
    ]
