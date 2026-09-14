"""Seed the database with demo data for manual testing / defence demos.

Not intended to be a fully general-purpose fixture generator: it creates a
fixed, small, "realistic enough" dataset (PLAN.md §5, Stage 3) — a handful
of demo users, categories, locations, ~25 equipment units, ~40 inspections
spread over the past year and ~10 incidents in mixed statuses.

Idempotent-ish: if `Equipment` rows already exist, the command does nothing
unless `--force` is passed, in which case previously seeded data (equipment,
categories, locations, the three demo users) is wiped and recreated. Objects
are created one by one via `Model.objects.create()` (never `bulk_create`) so
that `BaseModel._pre_create`/`_pre_update` side-effect hooks (see
`apps/maintenance/models.py` — an `Incident` flipping `Equipment.status`)
run exactly like they would from the admin/API.
"""
import datetime
import random

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.utils import timezone
from faker import Faker

from apps.equipment.choices import EquipmentStatus
from apps.equipment.models import Category, Equipment, Location
from apps.maintenance.choices import IncidentStatus, InspectionCondition
from apps.maintenance.models import Incident, Inspection
from apps.users.choices import GROUP_EMPLOYEE, GROUP_TECHNICIAN

User = get_user_model()

DEMO_PASSWORD = 'demo1234'
DEMO_USERNAMES = ('technician', 'employee1', 'employee2')

CATEGORY_NAMES = ['Ноутбуки', 'Комп\'ютери', 'Монітори', 'Мережеве обладнання']

LOCATIONS = [
    ('Головний офіс', 'м. Київ, вул. Хрещатик, 1'),
    ('Склад', 'м. Київ, вул. Промислова, 12'),
    ('Філія №2', 'м. Львів, просп. Свободи, 5'),
]

EQUIPMENT_COUNT = 25
INSPECTION_COUNT = 40
INCIDENT_COUNT = 16

# A handful of equipment units get a hand-picked `warranty_until` instead of
# a random one (PLAN.md §4.2 dashboard KPI "Гарантія закінчується протягом
# 30 днів" needs at least a few units actually inside that window to be
# demoable — with a uniformly random 1/2/3-year warranty over a purchase
# date up to ~3 years in the past, landing inside a specific 30-day window
# is very unlikely, so a plain random seed near-always shows 0 there).
# `equipment index -> days from today` (negative = already expired).
FORCED_WARRANTY_OFFSET_DAYS = {
    1: 5,
    2: 15,
    3: 29,
    4: -10,
    5: -200,
}


class Command(BaseCommand):
    """Populate the DB with demo Category/Location/Equipment/Inspection/Incident data."""

    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Wipe previously seeded demo data (equipment, categories, locations, demo users) and recreate it.',
        )

    def handle(self, *args, **options):
        force = options['force']

        if Equipment.objects.exists():
            if not force:
                self.stdout.write(self.style.WARNING(
                    'Equipment уже існує в базі — нічого не роблю (передай --force для перегенерації).'
                ))
                return
            self._wipe()

        self.fake = Faker('uk_UA')
        random.seed()

        technician, employees = self._create_users()
        categories = self._create_categories()
        locations = self._create_locations()
        equipment_list = self._create_equipment(categories, locations, technician, employees)
        self._create_inspections(equipment_list, technician)
        self._create_incidents(equipment_list, employees, technician)

        self.stdout.write(self.style.SUCCESS(
            f'Готово: {len(equipment_list)} обладнання, '
            f'{INSPECTION_COUNT} оглядів, {INCIDENT_COUNT} заявок.'
        ))

    def _wipe(self):
        self.stdout.write('Видаляю попередні демо-дані...')
        Equipment.objects.all().delete()  # cascades onto Inspection/Incident
        Category.objects.filter(name__in=CATEGORY_NAMES).delete()
        Location.objects.filter(name__in=[name for name, _address in LOCATIONS]).delete()
        User.objects.filter(username__in=DEMO_USERNAMES).delete()

    def _create_users(self):
        technician_group, _ = Group.objects.get_or_create(name=GROUP_TECHNICIAN)
        employee_group, _ = Group.objects.get_or_create(name=GROUP_EMPLOYEE)

        technician, _ = User.objects.get_or_create(
            username='technician',
            defaults={'email': 'technician@example.com', 'is_staff': True},
        )
        technician.is_staff = True
        technician.set_password(DEMO_PASSWORD)
        technician.save()
        technician.groups.add(technician_group)

        employees = []
        for username in ('employee1', 'employee2'):
            employee, _ = User.objects.get_or_create(
                username=username,
                defaults={'email': f'{username}@example.com', 'is_staff': True},
            )
            employee.is_staff = True
            employee.set_password(DEMO_PASSWORD)
            employee.save()
            employee.groups.add(employee_group)
            employees.append(employee)

        return technician, employees

    def _create_categories(self):
        return [
            Category.objects.create(name=name, description=self.fake.catch_phrase())
            for name in CATEGORY_NAMES
        ]

    def _create_locations(self):
        return [
            Location.objects.create(name=name, address=address)
            for name, address in LOCATIONS
        ]

    def _create_equipment(self, categories, locations, technician, employees):
        assignees = [None, technician, *employees]
        # Weighted so most equipment ends up "active"; incidents created later
        # will flip some of these to `faulty`/`in_repair` for real.
        statuses = (
            [EquipmentStatus.ACTIVE] * 6
            + [EquipmentStatus.FAULTY] * 1
            + [EquipmentStatus.IN_REPAIR] * 1
            + [EquipmentStatus.DECOMMISSIONED] * 1
        )
        equipment_list = []
        today = timezone.localdate()

        for i in range(1, EQUIPMENT_COUNT + 1):
            if i in FORCED_WARRANTY_OFFSET_DAYS:
                warranty_until = today + datetime.timedelta(days=FORCED_WARRANTY_OFFSET_DAYS[i])
                purchase_date = warranty_until - datetime.timedelta(days=365 * 2)
            else:
                purchase_date = today - datetime.timedelta(days=random.randint(60, 1200))
                warranty_years = random.choice([1, 2, 3])
                warranty_until = purchase_date + datetime.timedelta(days=365 * warranty_years)
            equipment = Equipment.objects.create(
                inventory_number=f'INV-{i:05d}',
                name=f'{self.fake.word().capitalize()} {self.fake.word()}',
                category=random.choice(categories),
                location=random.choice(locations),
                manufacturer=random.choice(['Dell', 'HP', 'Lenovo', 'Asus', 'Cisco', 'Apple']),
                model_name=self.fake.bothify(text='??-####'),
                serial_number=self.fake.unique.bothify(text='SN########'),
                purchase_date=purchase_date,
                warranty_until=warranty_until,
                status=random.choice(statuses),
                assigned_to=random.choice(assignees),
                inspection_interval_days=random.choice([90, 180, 365]),
                note=self.fake.sentence() if random.random() < 0.3 else '',
            )
            equipment_list.append(equipment)

        return equipment_list

    def _create_inspections(self, equipment_list, technician):
        # Only inspect a random subset of equipment (some units get none at
        # all -> naturally overdue via `Equipment.is_inspection_overdue`).
        today = timezone.localdate()
        for _ in range(INSPECTION_COUNT):
            equipment = random.choice(equipment_list)
            days_ago = random.randint(0, 365)
            performed_at = timezone.make_aware(
                datetime.datetime.combine(today - datetime.timedelta(days=days_ago), datetime.time(hour=10))
            )
            condition = random.choices(
                [InspectionCondition.GOOD, InspectionCondition.SATISFACTORY, InspectionCondition.POOR],
                weights=[6, 3, 1],
            )[0]
            Inspection.objects.create(
                equipment=equipment,
                performed_by=technician,
                performed_at=performed_at,
                condition=condition,
                comment=self.fake.sentence() if random.random() < 0.5 else '',
            )

    def _create_incidents(self, equipment_list, employees, technician):
        status_targets = (
            [IncidentStatus.NEW] * 3
            + [IncidentStatus.IN_PROGRESS] * 3
            + [IncidentStatus.RESOLVED] * 5
            + [IncidentStatus.CLOSED] * 5
        )
        random.shuffle(status_targets)
        now = timezone.now()

        for target_status in status_targets:
            equipment = random.choice(equipment_list)
            reporter = random.choice(employees)
            # `_pre_create` (see `apps/maintenance/models.py`) always flips
            # `equipment.status` to `faulty` on creation — desired, matches
            # what happens when an employee reports a problem via the admin.
            incident = Incident.objects.create(
                equipment=equipment,
                reported_by=reporter,
                description=self.fake.sentence(nb_words=10),
            )
            if target_status != IncidentStatus.NEW:
                incident.assigned_to = technician
                incident.status = target_status
                if target_status in (IncidentStatus.RESOLVED, IncidentStatus.CLOSED):
                    incident.resolution = self.fake.sentence()
                incident.save()
            # Spread closed incidents over the past year so the monthly chart
            # has data; open ones stay recent. `created_at` is auto_now_add,
            # hence the queryset update (bypasses hooks on purpose).
            if target_status in (IncidentStatus.RESOLVED, IncidentStatus.CLOSED):
                created_at = now - datetime.timedelta(days=random.randint(20, 330))
                resolved_at = created_at + datetime.timedelta(days=random.randint(1, 14))
                Incident.objects.filter(pk=incident.pk).update(created_at=created_at, resolved_at=resolved_at)
