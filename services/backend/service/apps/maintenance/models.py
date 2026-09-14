from django.conf import settings
from django.db import models
from django.utils import timezone

from libs.db.models import NB, BaseModel

from apps.maintenance.choices import IncidentStatus, InspectionCondition


class Inspection(BaseModel):
    equipment = models.ForeignKey(
        'apps.Equipment',
        verbose_name='обладнання',
        on_delete=models.CASCADE,
        related_name='inspections',
    )
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='виконав',
        on_delete=models.SET_NULL,
        related_name='inspections',
        **NB,
    )
    performed_at = models.DateTimeField('дата проведення', default=timezone.now)
    condition = models.CharField(
        'стан',
        max_length=20,
        choices=InspectionCondition.choices,
        default=InspectionCondition.GOOD,
    )
    comment = models.TextField('коментар', **NB)

    class Meta:
        verbose_name = 'огляд'
        verbose_name_plural = 'огляди'
        ordering = ['-performed_at']

    def __str__(self):
        return f'Огляд {self.equipment} від {self.performed_at:%Y-%m-%d}'


class Incident(BaseModel):
    equipment = models.ForeignKey(
        'apps.Equipment',
        verbose_name='обладнання',
        on_delete=models.CASCADE,
        related_name='incidents',
    )
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='повідомив',
        on_delete=models.SET_NULL,
        related_name='reported_incidents',
        **NB,
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='призначено',
        on_delete=models.SET_NULL,
        related_name='assigned_incidents',
        **NB,
    )
    description = models.TextField('опис')
    status = models.CharField(
        'статус',
        max_length=20,
        choices=IncidentStatus.choices,
        default=IncidentStatus.NEW,
    )
    resolved_at = models.DateTimeField('дата вирішення', **NB)
    resolution = models.TextField('рішення', **NB)

    class Meta:
        verbose_name = 'заявка на несправність'
        verbose_name_plural = 'заявки на несправність'
        ordering = ['-created_at']

    def __str__(self):
        return f'Заявка по {self.equipment} ({self.get_status_display()})'

    def _pre_create(self):
        from apps.maintenance import services
        services.on_incident_created(self)

    def _pre_update(self):
        from apps.maintenance import services
        old_status = Incident.objects.filter(pk=self.pk).values_list('status', flat=True).first()
        services.on_incident_status_changed(self, old_status)
