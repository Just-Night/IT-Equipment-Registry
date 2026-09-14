"""Non-DRF admin views (Stage 4b).

Plain Django views wired into `apps.admin.site.CustomAdminSite`
(`get_urls()`), not `api/v1/urls.py` — that file is reserved for the DRF API
(Stage 6, PLAN.md §4.4). Wrapped in `admin_site.admin_view(...)`, so only an
authenticated staff user can reach them at all; role-based scoping below
that is `apps.reports.pdf`'s job (which reuses
`apps.reports.dashboard.get_scoped_querysets` — the same Employee-only-sees-
their-own-equipment rule as the on-screen dashboard).
"""
from django.http import HttpResponse

from apps.reports.pdf import dashboard_summary_pdf


def summary_pdf_view(request):
    """"Зведений звіт" PDF, scoped to the current user's role."""
    pdf_bytes = dashboard_summary_pdf(request.user)
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="dashboard_summary.pdf"'
    return response
