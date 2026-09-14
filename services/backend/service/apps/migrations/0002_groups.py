"""Create `Technician`/`Employee` groups with their Stage 1 permissions.

Stage 2 (maintenance app: Inspection/Incident) adds a migration that grants
the additional permissions listed in PLAN.md §1 ("Дія / Адмін / Технік /
Працівник") once those models exist.

Uses the real (global) app registry rather than the migration's frozen
`apps` state: `create_permissions` needs the actual model classes (to read
their `Meta` and build `add_permission_name` etc.), and the `Permission`
rows for models created earlier in this same migration run do not exist yet
— `post_migrate` normally creates them only after all migrations finish.
"""
from django.apps import apps as global_apps
from django.contrib.auth.management import create_permissions
from django.db import migrations

GROUP_TECHNICIAN = 'Technician'
GROUP_EMPLOYEE = 'Employee'


def create_groups(apps, schema_editor):
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

    technician = Group.objects.create(name=GROUP_TECHNICIAN)
    technician.permissions.add(
        *perms('Category', ['view_category']),
        *perms('Location', ['view_location']),
        *perms('Equipment', ['view_equipment', 'change_equipment']),
    )

    employee = Group.objects.create(name=GROUP_EMPLOYEE)
    employee.permissions.add(
        *perms('Equipment', ['view_equipment']),
    )


def delete_groups(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name__in=[GROUP_TECHNICIAN, GROUP_EMPLOYEE]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('apps', '0001_initial'),
        # Explicit deps so this migration runs after auth/contenttypes have
        # reached their final schema (this data migration touches both
        # directly, e.g. `django_content_type` still has a NOT NULL `name`
        # column before contenttypes.0002 runs).
        ('auth', '0012_alter_user_first_name_max_length'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.RunPython(create_groups, delete_groups),
    ]
