from django.http import Http404, HttpResponse

from unfold.admin import ModelAdmin
from unfold.decorators import action, display

from import_export.admin import ExportActionModelAdmin
from unfold.contrib.import_export.forms import ExportForm

from apps.admin.model_admin import TimestampsAdminMixin
from apps.equipment.models import Equipment
from apps.maintenance.choices import IncidentStatus, InspectionCondition
from apps.reports.pdf import inspection_act_pdf
from apps.reports.resources import IncidentResource, InspectionResource
from apps.users.permissions import is_employee, is_technician

CONDITION_LABELS = {
    InspectionCondition.GOOD: 'success',
    InspectionCondition.SATISFACTORY: 'warning',
    InspectionCondition.POOR: 'danger',
}

INCIDENT_STATUS_LABELS = {
    IncidentStatus.NEW: 'info',
    IncidentStatus.IN_PROGRESS: 'warning',
    IncidentStatus.RESOLVED: 'success',
    IncidentStatus.CLOSED: 'success',
}

# Fields an `Employee` cannot touch on their own `Incident`s (PLAN.md §1:
# "створення для свого обладнання, читання своїх" — employees may describe
# a problem, but not decide the outcome). Today the group has no
# `change_incident` permission, so this only matters on the add form and
# as future-proofing if employees ever get edit rights.
EMPLOYEE_READONLY_INCIDENT_FIELDS = ('status', 'assigned_to', 'resolution', 'resolved_at')


class InspectionAdmin(TimestampsAdminMixin, ExportActionModelAdmin, ModelAdmin):
    resource_classes = (InspectionResource,)
    # See `EquipmentAdmin.export_form_class` — plain form, no per-column checkboxes.
    export_form_class = ExportForm
    list_display = ('equipment', 'performed_by', 'performed_at', 'condition_display')
    list_filter = ('condition',)
    search_fields = ('equipment__inventory_number', 'equipment__name')
    autocomplete_fields = ('equipment',)
    date_hierarchy = 'performed_at'
    fields = ('equipment', 'performed_by', 'performed_at', 'condition', 'comment', 'created_display', 'updated_display')
    readonly_fields = ('created_display', 'updated_display')
    actions_detail = ['inspection_act_pdf_action']
    actions_row = ['inspection_act_pdf_action']

    @display(description='Стан', label=CONDITION_LABELS)
    def condition_display(self, obj):
        return obj.condition, obj.get_condition_display()

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser and 'performed_by' not in readonly:
            readonly.append('performed_by')
        return readonly

    def save_model(self, request, obj, form, change):
        if not change and not obj.performed_by_id:
            obj.performed_by = request.user
        super().save_model(request, obj, form, change)

    def has_export_permission(self, request):
        # PLAN.md §1 "Звіти, експорт: адмін, технік" — Employee cannot export.
        user = request.user
        return user.is_superuser or is_technician(user)

    @action(
        description='Акт огляду (PDF)',
        url_path='inspection-act-pdf',
        attrs={'target': '_blank'},
        icon='picture_as_pdf',
        permissions=['view'],
    )
    def inspection_act_pdf_action(self, request, object_id):
        """"Акт огляду" PDF for one `Inspection` (Stage 4b).

        `permissions=['view']` is the actual gate here: Employees have no
        `view_inspection` permission at all (PLAN.md §1 — they can only
        create/read their own `Incident`s), so `unfold.decorators.action`
        raises `PermissionDenied` (403) for them before this method body
        ever runs. `get_object` is still used (not a raw `.get(pk=...)`) so
        the 404-vs-403 behavior matches every other admin view.
        """
        inspection = self.get_object(request, object_id)
        if inspection is None:
            raise Http404('Огляд не знайдено')

        pdf_bytes = inspection_act_pdf(inspection, user=request.user)
        act_number = str(inspection.pk).split('-')[0]
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="inspection_act_{act_number}.pdf"'
        return response


class IncidentAdmin(TimestampsAdminMixin, ExportActionModelAdmin, ModelAdmin):
    resource_classes = (IncidentResource,)
    export_form_class = ExportForm
    list_display = ('equipment', 'reported_by', 'assigned_to', 'status_display', 'created_at', 'resolved_at')
    list_filter = ('status',)
    search_fields = ('equipment__inventory_number', 'equipment__name')
    autocomplete_fields = ('equipment',)
    date_hierarchy = 'created_at'
    fields = (
        'equipment',
        'reported_by',
        'assigned_to',
        'description',
        'status',
        'resolved_at',
        'resolution',
        'created_display',
        'updated_display',
    )
    readonly_fields = ('created_display', 'updated_display')

    @display(description='Статус', label=INCIDENT_STATUS_LABELS)
    def status_display(self, obj):
        return obj.status, obj.get_status_display()

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        user = request.user
        if user.is_superuser or not is_employee(user):
            return qs
        return qs.filter(reported_by=user)

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        user = request.user
        if not user.is_superuser:
            if 'reported_by' not in readonly:
                readonly.append('reported_by')
            if is_employee(user):
                for name in EMPLOYEE_READONLY_INCIDENT_FIELDS:
                    if name not in readonly:
                        readonly.append(name)
        return readonly

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'equipment' and not request.user.is_superuser and is_employee(request.user):
            kwargs['queryset'] = Equipment.objects.filter(assigned_to=request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if not change and not obj.reported_by_id:
            obj.reported_by = request.user
        super().save_model(request, obj, form, change)

    def has_export_permission(self, request):
        # PLAN.md §1 "Звіти, експорт: адмін, технік" — Employee cannot export.
        user = request.user
        return user.is_superuser or is_technician(user)
