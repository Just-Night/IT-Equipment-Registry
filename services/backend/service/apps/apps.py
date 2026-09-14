from django.apps import AppConfig


class AppsConfig(AppConfig):
    """Single project app (mono-app, see CLAUDE.md). `verbose_name` is what the
    admin shows in breadcrumbs instead of the bare label "Apps"."""

    name = 'apps'
    verbose_name = 'Панель керування'
