from django.db import models


class InspectionCondition(models.TextChoices):
    GOOD = 'good', 'Добре'
    SATISFACTORY = 'satisfactory', 'Задовільно'
    POOR = 'poor', 'Погано'


class IncidentStatus(models.TextChoices):
    NEW = 'new', 'Нова'
    IN_PROGRESS = 'in_progress', 'В роботі'
    RESOLVED = 'resolved', 'Вирішена'
    CLOSED = 'closed', 'Закрита'
