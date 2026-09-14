from django.conf import settings
from django.shortcuts import redirect
from django.urls import path

from unfold.sites import UnfoldAdminSite

from apps.reports.views import summary_pdf_view


class CustomAdminSite(UnfoldAdminSite):
    site_header = f'{settings.PROJECT_NAME} Admin'
    site_title = f'{settings.PROJECT_NAME} Portal'
    index_title = 'Панель керування'

    def app_index(self, request, app_label, extra_context=None):
        # `/admin/apps/` would be a bare model list — the dashboard covers it.
        return redirect('admin_site:index')

    def get_urls(self):
        urls = super().get_urls()
        # Stage 4b: "Зведений звіт (PDF)" — plain admin view (not DRF/API,
        # see `apps/reports/views.py`), linked from `templates/admin/index.html`.
        custom_urls = [
            path('reports/summary.pdf', self.admin_view(summary_pdf_view), name='reports_summary_pdf'),
        ]
        return custom_urls + urls


admin_site = CustomAdminSite(name='admin_site')
