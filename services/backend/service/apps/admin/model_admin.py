from rest_framework_api_key.admin import APIKeyModelAdmin


from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin

from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm
from unfold.admin import ModelAdmin
from unfold.decorators import display


class TimestampsAdminMixin:
    """Readonly `created_at`/`updated_at` with Ukrainian labels for change forms.

    `BaseModel` (libs) defines these fields without `verbose_name`, so admin
    classes reference `created_display`/`updated_display` instead of raw fields.
    """

    @display(description='Створено')
    def created_display(self, obj):
        return obj.created_at

    @display(description='Оновлено')
    def updated_display(self, obj):
        return obj.updated_at


class ApiKeyModelAdmin(APIKeyModelAdmin, ModelAdmin):
    compressed_fields = True


class UserAdmin(BaseUserAdmin, ModelAdmin):
    # Forms loaded from `unfold.forms`
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm


class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass
