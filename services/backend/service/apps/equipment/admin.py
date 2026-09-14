from django.contrib import admin
from django.db import models
from django.http import Http404, HttpResponse
from django.utils import timezone

from unfold.admin import ModelAdmin, StackedInline, TabularInline
from unfold.decorators import action, display
from unfold.widgets import UnfoldAdminExpandableTextareaWidget

from simple_history.admin import SimpleHistoryAdmin
from import_export.admin import ExportActionModelAdmin
from unfold.contrib.import_export.forms import ExportForm

from apps.equipment import services as equipment_services
from apps.equipment.choices import EquipmentStatus
from apps.equipment.models import Category, Equipment, Location
from apps.maintenance.models import Incident, Inspection
from apps.admin.model_admin import TimestampsAdminMixin
from apps.reports.pdf import equipment_card_pdf
from apps.reports.resources import EquipmentResource
from apps.users.permissions import is_employee, is_technician

STATUS_LABELS = {
    EquipmentStatus.ACTIVE: 'success',
    EquipmentStatus.FAULTY: 'danger',
    EquipmentStatus.IN_REPAIR: 'warning',
    EquipmentStatus.DECOMMISSIONED: 'info',
}

# Fields a `Technician` is allowed to edit on `Equipment` (PLAN.md §1: "технік
# читання + зміна статусу"). Everything else becomes readonly for them via
# `EquipmentAdmin.get_readonly_fields`.
TECHNICIAN_EDITABLE_FIELDS = {'status'}


class CategoryAdmin(ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)


class LocationAdmin(ModelAdmin):
    list_display = ('name', 'address')
    search_fields = ('name', 'address')


class OverdueInspectionFilter(admin.SimpleListFilter):
    """Custom filter: "Прострочений огляд" (так/ні).

    `next_inspection_at`/`is_inspection_overdue` are computed properties
    (see `apps/equipment/services.py`), not DB fields, so filtering is done
    in Python over the already-paginated-by-other-filters queryset and then
    narrowed back down with `pk__in` — simple and correct for the dataset
    sizes this project deals with (dozens of equipment units).
    """

    title = 'прострочений огляд'
    parameter_name = 'inspection_overdue'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Так'),
            ('no', 'Ні'),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value not in ('yes', 'no'):
            return queryset
        annotated = equipment_services.with_last_inspection(queryset)
        overdue_pks = [equipment.pk for equipment in annotated if equipment.is_inspection_overdue]
        if value == 'yes':
            return queryset.filter(pk__in=overdue_pks)
        return queryset.exclude(pk__in=overdue_pks)


# Text fields in inlines: 2 rows by default, grow with content
# (`field-sizing-content`), so short comments stay compact and long ones are
# still fully visible without scrolling inside the textarea.
INLINE_TEXTAREA_OVERRIDES = {
    models.TextField: {'widget': UnfoldAdminExpandableTextareaWidget},
}


class InspectionInline(TabularInline):
    model = Inspection
    fk_name = 'equipment'
    extra = 0
    tab = True
    per_page = 10
    ordering = ('-performed_at',)
    fields = ('performed_by', 'performed_at', 'condition', 'comment')
    formfield_overrides = INLINE_TEXTAREA_OVERRIDES


class IncidentInline(StackedInline):
    model = Incident
    fk_name = 'equipment'
    extra = 0
    tab = True
    per_page = 5
    ordering = ('-created_at',)
    fields = (
        ('reported_by', 'assigned_to', 'status'),
        'description',
        ('resolved_at',),
        'resolution',
    )
    formfield_overrides = INLINE_TEXTAREA_OVERRIDES

    def get_queryset(self, request):
        # Same scoping as `IncidentAdmin`: an employee sees only own reports.
        qs = super().get_queryset(request)
        user = request.user
        if user.is_superuser or not is_employee(user):
            return qs
        return qs.filter(reported_by=user)


class EquipmentAdmin(TimestampsAdminMixin, SimpleHistoryAdmin, ExportActionModelAdmin, ModelAdmin):
    resource_classes = (EquipmentResource,)
    # Plain `ExportForm` (format + single hidden resource), not the default
    # `SelectableFieldsExportForm` — one resource per model is enough for
    # this project, so the per-column checkboxes only add UI noise.
    export_form_class = ExportForm
    list_display = (
        'inventory_number',
        'name',
        'category',
        'location',
        'status_display',
        'assigned_to',
        'next_inspection_display',
        'warranty_until',
    )
    list_filter = ('status', 'category', 'location', OverdueInspectionFilter)
    search_fields = ('inventory_number', 'name', 'serial_number')
    autocomplete_fields = ('assigned_to',)
    inlines = (InspectionInline, IncidentInline)
    actions_detail = ['equipment_card_pdf_action']
    actions_row = ['equipment_card_pdf_action']

    fieldsets = (
        ('Основне', {
            'fields': (
                'inventory_number',
                'name',
                'category',
                'location',
                'manufacturer',
                'model_name',
                'serial_number',
                'status',
                'note',
            ),
        }),
        ('Придбання та гарантія', {
            'fields': (
                'purchase_date',
                'warranty_until',
                'is_warranty_expiring_display',
            ),
        }),
        ('Обслуговування', {
            'fields': (
                'assigned_to',
                'inspection_interval_days',
                'last_inspection_display',
                'next_inspection_at_display',
                'is_inspection_overdue_display',
                'created_display',
                'updated_display',
            ),
        }),
    )
    readonly_fields = (
        'created_display',
        'updated_display',
        'last_inspection_display',
        'next_inspection_at_display',
        'is_inspection_overdue_display',
        'is_warranty_expiring_display',
    )

    @display(description='Статус', label=STATUS_LABELS)
    def status_display(self, obj):
        return obj.status, obj.get_status_display()

    @display(description='Наступний огляд', label={True: 'danger', False: 'success'})
    def next_inspection_display(self, obj):
        value = obj.next_inspection_at
        text = value.strftime('%d.%m.%Y') if value else '—'
        return obj.is_inspection_overdue, text

    @display(description='Наступний огляд')
    def next_inspection_at_display(self, obj):
        # Plain text for the change form; `next_inspection_display` (badge) is list-only.
        value = obj.next_inspection_at
        return value.strftime('%d.%m.%Y') if value else '—'

    @display(description='Останній огляд')
    def last_inspection_display(self, obj):
        value = obj.last_inspection_at
        if not value:
            return '—'
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        return value.strftime('%d.%m.%Y %H:%M')

    @display(description='Прострочено огляд', boolean=True)
    def is_inspection_overdue_display(self, obj):
        return obj.is_inspection_overdue

    @display(description='Гарантія спливає до 30 днів', boolean=True)
    def is_warranty_expiring_display(self, obj):
        return obj.is_warranty_expiring

    def get_queryset(self, request):
        qs = equipment_services.with_last_inspection(super().get_queryset(request))
        user = request.user
        if user.is_superuser:
            return qs
        if is_technician(user):
            return qs
        # Employee (or any other non-privileged user): only their own equipment.
        return qs.filter(assigned_to=user)

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        user = request.user
        if not user.is_superuser and is_technician(user):
            model_fields = [f.name for f in self.model._meta.fields if f.editable]
            for name in model_fields:
                if name not in TECHNICIAN_EDITABLE_FIELDS and name not in readonly:
                    readonly.append(name)
        return readonly

    def has_export_permission(self, request):
        # PLAN.md §1 "Звіти, експорт: адмін, технік" — Employee cannot export.
        user = request.user
        return user.is_superuser or is_technician(user)

    @action(
        description='Картка обладнання (PDF)',
        url_path='equipment-card-pdf',
        attrs={'target': '_blank'},
        icon='picture_as_pdf',
        permissions=['view'],
    )
    def equipment_card_pdf_action(self, request, object_id):
        """"Картка обладнання" PDF for one `Equipment` (Stage 4b).

        `permissions=['view']` (checked by `unfold.decorators.action` itself)
        gates the model-level `view_equipment` permission — an Employee has
        it (they can see their own equipment), so per-object scoping still
        has to happen here: `self.get_object` uses `self.get_queryset`
        (Employee → own equipment only), so a foreign equipment id yields
        `None` and a 404, exactly like opening its change page would.
        """
        equipment = self.get_object(request, object_id)
        if equipment is None:
            raise Http404('Обладнання не знайдено')

        pdf_bytes = equipment_card_pdf(equipment, user=request.user)
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="equipment_{equipment.inventory_number}.pdf"'
        return response
