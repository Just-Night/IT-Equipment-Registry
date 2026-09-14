"""Custom `handler403`: render the "access denied" page inside the Unfold
admin layout (sidebar, header, theme) instead of a bare standalone page.

Wired in `api/urls.py` (`handler403`). Falls back to the standalone
`403.html` for anonymous users, where there is no admin chrome to show.
"""
from django.shortcuts import render

from apps.admin.site import admin_site


def permission_denied(request, exception=None):
    if not request.user.is_authenticated:
        return render(request, '403.html', status=403)
    context = admin_site.each_context(request)
    context.update({'title': 'Доступ заборонено'})
    return render(request, 'admin/403.html', context, status=403)
