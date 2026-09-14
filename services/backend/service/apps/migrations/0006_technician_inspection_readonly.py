"""Align `Technician` with PLAN.md §1: inspections are create + read only.

`0004_groups_maintenance` granted full CRUD on `Inspection`; drop change/delete.
"""
from django.apps import apps as global_apps
from django.db import migrations

GROUP_TECHNICIAN = 'Technician'
CODENAMES = ['change_inspection', 'delete_inspection']


def _perms(apps, codenames):
    Permission = apps.get_model('auth', 'Permission')
    ContentType = apps.get_model('contenttypes', 'ContentType')
    content_type = ContentType.objects.get_for_model(
        global_apps.get_model('apps', 'Inspection'), for_concrete_model=False
    )
    return Permission.objects.filter(content_type=content_type, codename__in=codenames)


def remove_permissions(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    technician = Group.objects.filter(name=GROUP_TECHNICIAN).first()
    if technician:
        technician.permissions.remove(*_perms(apps, CODENAMES))


def add_permissions(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    technician = Group.objects.filter(name=GROUP_TECHNICIAN).first()
    if technician:
        technician.permissions.add(*_perms(apps, CODENAMES))


class Migration(migrations.Migration):

    dependencies = [
        ('apps', '0005_alter_historicalequipment_options'),
    ]

    operations = [
        migrations.RunPython(remove_permissions, add_permissions),
    ]
