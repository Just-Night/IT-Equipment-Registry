import factory
from django.contrib.auth import get_user_model

from apps.equipment.choices import EquipmentStatus
from apps.equipment.models import Category, Equipment, Location
from apps.maintenance.choices import IncidentStatus, InspectionCondition
from apps.maintenance.models import Incident, Inspection


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = get_user_model()
        django_get_or_create = ('username',)

    username = factory.Sequence(lambda n: f'user{n}')
    email = factory.LazyAttribute(lambda o: f'{o.username}@example.com')


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category

    name = factory.Sequence(lambda n: f'Категорія {n}')
    description = 'Опис категорії'


class LocationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Location

    name = factory.Sequence(lambda n: f'Локація {n}')
    address = 'вул. Тестова, 1'


class EquipmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Equipment

    inventory_number = factory.Sequence(lambda n: f'INV-{n:05d}')
    name = 'Ноутбук Dell Latitude'
    category = factory.SubFactory(CategoryFactory)
    location = factory.SubFactory(LocationFactory)
    manufacturer = 'Dell'
    model_name = 'Latitude 5420'
    serial_number = factory.Sequence(lambda n: f'SN{n:08d}')
    status = EquipmentStatus.ACTIVE
    inspection_interval_days = 180


class InspectionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Inspection

    equipment = factory.SubFactory(EquipmentFactory)
    performed_by = factory.SubFactory(UserFactory)
    condition = InspectionCondition.GOOD
    comment = 'Все гаразд'


class IncidentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Incident

    equipment = factory.SubFactory(EquipmentFactory)
    reported_by = factory.SubFactory(UserFactory)
    description = 'Не вмикається'
    status = IncidentStatus.NEW
