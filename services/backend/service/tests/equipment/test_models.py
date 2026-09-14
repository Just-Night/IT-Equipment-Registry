import pytest
from django.db import IntegrityError

from apps.equipment.choices import EquipmentStatus
from tests.factories import EquipmentFactory


@pytest.mark.django_db
def test_str():
    equipment = EquipmentFactory(inventory_number='INV-00001', name='Монітор Dell')
    assert str(equipment) == 'INV-00001 — Монітор Dell'


@pytest.mark.django_db
def test_default_status():
    equipment = EquipmentFactory()
    assert equipment.status == EquipmentStatus.ACTIVE


@pytest.mark.django_db
def test_inventory_number_unique():
    EquipmentFactory(inventory_number='INV-DUP')
    with pytest.raises(IntegrityError):
        EquipmentFactory(inventory_number='INV-DUP')


@pytest.mark.django_db
def test_history_record_created_on_save():
    equipment = EquipmentFactory()
    assert equipment.history.count() == 1

    equipment.status = EquipmentStatus.FAULTY
    equipment.save()

    assert equipment.history.count() == 2
    assert equipment.history.first().status == EquipmentStatus.FAULTY
