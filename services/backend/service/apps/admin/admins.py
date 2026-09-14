from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from apps.admin.site import admin_site
from apps.admin import model_admin as main_model_admin

from apps.equipment.admin import CategoryAdmin, EquipmentAdmin, LocationAdmin
from apps.equipment.models import Category, Equipment, Location
from apps.maintenance.admin import IncidentAdmin, InspectionAdmin
from apps.maintenance.models import Incident, Inspection


admin_site.register(get_user_model(), main_model_admin.UserAdmin)
admin_site.register(Group, main_model_admin.GroupAdmin)

admin_site.register(Category, CategoryAdmin)
admin_site.register(Location, LocationAdmin)
admin_site.register(Equipment, EquipmentAdmin)

admin_site.register(Inspection, InspectionAdmin)
admin_site.register(Incident, IncidentAdmin)
