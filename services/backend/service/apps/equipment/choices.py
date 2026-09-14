from django.db import models


class EquipmentStatus(models.TextChoices):
    ACTIVE = 'active', 'Активне'
    FAULTY = 'faulty', 'Несправне'
    IN_REPAIR = 'in_repair', 'У ремонті'
    DECOMMISSIONED = 'decommissioned', 'Списане'
