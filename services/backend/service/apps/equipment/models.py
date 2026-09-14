from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords

from libs.db.models import NB, BaseModel

from apps.equipment.choices import EquipmentStatus


class Category(BaseModel):
    name = models.CharField('назва', max_length=150, unique=True)
    description = models.TextField('опис', **NB)

    class Meta:
        verbose_name = 'категорія'
        verbose_name_plural = 'категорії'
        ordering = ['name']

    def __str__(self):
        return self.name


class Location(BaseModel):
    name = models.CharField('назва', max_length=150, unique=True)
    address = models.CharField('адреса', max_length=255, **NB)

    class Meta:
        verbose_name = 'локація'
        verbose_name_plural = 'локації'
        ordering = ['name']

    def __str__(self):
        return self.name


class Equipment(BaseModel):
    """IT equipment unit.

    Stage 2 adds the `Inspection` model with `related_name='inspections'`
    and a `performed_at` field pointing back to this model — the
    `last_inspection_at`/`next_inspection_at`/`is_inspection_overdue`
    properties below are guarded against that relation not existing yet
    (see `apps/equipment/services.py`).
    """

    inventory_number = models.CharField('інвентарний номер', max_length=50, unique=True)
    name = models.CharField('назва', max_length=255)
    category = models.ForeignKey(
        Category,
        verbose_name='категорія',
        on_delete=models.PROTECT,
        related_name='equipment',
    )
    location = models.ForeignKey(
        Location,
        verbose_name='локація',
        on_delete=models.PROTECT,
        related_name='equipment',
    )
    manufacturer = models.CharField('виробник', max_length=150, **NB)
    model_name = models.CharField('модель', max_length=150, **NB)
    serial_number = models.CharField('серійний номер', max_length=150, **NB)
    purchase_date = models.DateField('дата придбання', **NB)
    warranty_until = models.DateField('гарантія до', **NB)
    status = models.CharField(
        'статус',
        max_length=20,
        choices=EquipmentStatus.choices,
        default=EquipmentStatus.ACTIVE,
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='закріплено за',
        on_delete=models.SET_NULL,
        related_name='assigned_equipment',
        **NB,
    )
    inspection_interval_days = models.PositiveIntegerField('інтервал оглядів (днів)', default=180)
    note = models.TextField('примітка', **NB)

    history = HistoricalRecords(verbose_name='Історія обладнання', verbose_name_plural='Історія обладнання')

    class Meta:
        verbose_name = 'обладнання'
        verbose_name_plural = 'обладнання'
        ordering = ['inventory_number']

    def __str__(self):
        return f'{self.inventory_number} — {self.name}'

    @property
    def last_inspection_at(self):
        from apps.equipment import services
        return services.get_last_inspection_at(self)

    @property
    def next_inspection_at(self):
        from apps.equipment import services
        return services.get_next_inspection_at(self)

    @property
    def is_inspection_overdue(self):
        from apps.equipment import services
        return services.is_inspection_overdue(self)

    @property
    def is_warranty_expiring(self):
        from apps.equipment import services
        return services.is_warranty_expiring(self)
