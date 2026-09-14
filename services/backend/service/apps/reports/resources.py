"""`django-import-export` resources for admin CSV/XLSX export (PLAN.md §4.1).

Export-only (no import — see `apps/equipment/admin.py`,
`apps/maintenance/admin.py`: `ExportActionModelAdmin`, not
`ImportExportModelAdmin`). FK columns export as human-readable text (name/
inventory number/username) and choice fields as their display label, via
`dehydrate_<field>` — the resource's `Meta.fields`/`export_order` still list
the plain attribute name, `dehydrate_*` just overrides how it renders.
"""
from django.utils import timezone

from import_export import fields, resources

from apps.equipment.models import Equipment
from apps.maintenance.models import Incident, Inspection


def _format_date(value):
    """`dd.mm.yyyy` for a date, empty string for `None`."""
    return value.strftime('%d.%m.%Y') if value else ''


def _format_datetime(value):
    """`dd.mm.yyyy HH:MM` in local time for a datetime, empty string for `None`.

    Raw datetimes export as UTC with microseconds (e.g.
    `2026-09-13 22:21:55.531071+00:00`) — not what a human reading the CSV/
    XLSX in Kyiv time wants to see, so this localizes and truncates to
    minutes, matching `EquipmentAdmin.last_inspection_display`'s format.
    """
    if not value:
        return ''
    if timezone.is_aware(value):
        value = timezone.localtime(value)
    return value.strftime('%d.%m.%Y %H:%M')


class EquipmentResource(resources.ModelResource):
    inventory_number = fields.Field(attribute='inventory_number', column_name='Інвентарний номер')
    name = fields.Field(attribute='name', column_name='Назва')
    category = fields.Field(attribute='category', column_name='Категорія')
    location = fields.Field(attribute='location', column_name='Локація')
    manufacturer = fields.Field(attribute='manufacturer', column_name='Виробник')
    model_name = fields.Field(attribute='model_name', column_name='Модель')
    serial_number = fields.Field(attribute='serial_number', column_name='Серійний номер')
    purchase_date = fields.Field(attribute='purchase_date', column_name='Дата придбання')
    warranty_until = fields.Field(attribute='warranty_until', column_name='Гарантія до')
    status = fields.Field(attribute='status', column_name='Статус')
    assigned_to = fields.Field(attribute='assigned_to', column_name='Закріплено за')
    inspection_interval_days = fields.Field(
        attribute='inspection_interval_days', column_name='Інтервал оглядів (днів)'
    )
    note = fields.Field(attribute='note', column_name='Примітка')

    class Meta:
        model = Equipment
        fields = (
            'inventory_number',
            'name',
            'category',
            'location',
            'manufacturer',
            'model_name',
            'serial_number',
            'purchase_date',
            'warranty_until',
            'status',
            'assigned_to',
            'inspection_interval_days',
            'note',
        )
        export_order = fields

    def dehydrate_category(self, obj):
        return obj.category.name if obj.category_id else ''

    def dehydrate_location(self, obj):
        return obj.location.name if obj.location_id else ''

    def dehydrate_purchase_date(self, obj):
        return _format_date(obj.purchase_date)

    def dehydrate_warranty_until(self, obj):
        return _format_date(obj.warranty_until)

    def dehydrate_status(self, obj):
        return obj.get_status_display()

    def dehydrate_assigned_to(self, obj):
        return obj.assigned_to.get_username() if obj.assigned_to_id else ''


class InspectionResource(resources.ModelResource):
    equipment = fields.Field(attribute='equipment', column_name='Обладнання')
    performed_by = fields.Field(attribute='performed_by', column_name='Виконав')
    performed_at = fields.Field(attribute='performed_at', column_name='Дата проведення')
    condition = fields.Field(attribute='condition', column_name='Стан')
    comment = fields.Field(attribute='comment', column_name='Коментар')

    class Meta:
        model = Inspection
        fields = ('equipment', 'performed_by', 'performed_at', 'condition', 'comment')
        export_order = fields

    def dehydrate_equipment(self, obj):
        return obj.equipment.inventory_number

    def dehydrate_performed_by(self, obj):
        return obj.performed_by.get_username() if obj.performed_by_id else ''

    def dehydrate_performed_at(self, obj):
        return _format_datetime(obj.performed_at)

    def dehydrate_condition(self, obj):
        return obj.get_condition_display()


class IncidentResource(resources.ModelResource):
    equipment = fields.Field(attribute='equipment', column_name='Обладнання')
    reported_by = fields.Field(attribute='reported_by', column_name='Повідомив')
    assigned_to = fields.Field(attribute='assigned_to', column_name='Призначено')
    description = fields.Field(attribute='description', column_name='Опис')
    status = fields.Field(attribute='status', column_name='Статус')
    resolved_at = fields.Field(attribute='resolved_at', column_name='Дата вирішення')
    resolution = fields.Field(attribute='resolution', column_name='Рішення')

    class Meta:
        model = Incident
        fields = ('equipment', 'reported_by', 'assigned_to', 'description', 'status', 'resolved_at', 'resolution')
        export_order = fields

    def dehydrate_equipment(self, obj):
        return obj.equipment.inventory_number

    def dehydrate_reported_by(self, obj):
        return obj.reported_by.get_username() if obj.reported_by_id else ''

    def dehydrate_assigned_to(self, obj):
        return obj.assigned_to.get_username() if obj.assigned_to_id else ''

    def dehydrate_resolved_at(self, obj):
        return _format_datetime(obj.resolved_at)

    def dehydrate_status(self, obj):
        return obj.get_status_display()
