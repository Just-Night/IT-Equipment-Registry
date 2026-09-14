from django.conf import settings
from django.urls import include, path
from django.conf.urls.static import static

from apps.admin.admins import admin_site

from .health_check import urlpatterns as health_check_urls
from .docs import urlpatterns as docs_urlpatterns

# Ініціалізація основного списку URL
urlpatterns = [
    path("__debug__/", include("debug_toolbar.urls")),
    path("oauth/", include("social_django.urls", namespace="social")),
    path("api/", include([
        path("health-check/", include(health_check_urls)),
        path("docs/", include(docs_urlpatterns)),
    ])),
]
# Додавання адміністративного маршруту залежно від середовища
if settings.ENVIRONMENT == settings.ENVIRONMENT_PRODUCTION:
    urlpatterns.append(path("", admin_site.urls))
else:
    urlpatterns.append(path("admin/", admin_site.urls))


# Додавання статичних і медіа файлів
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
# Beautiful 403 inside the admin layout (see apps/admin/errors.py).
handler403 = 'apps.admin.errors.permission_denied'
