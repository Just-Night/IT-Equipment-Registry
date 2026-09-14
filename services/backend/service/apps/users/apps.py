from django.contrib.auth.apps import AuthConfig


class UsersAuthConfig(AuthConfig):
    """`django.contrib.auth` with a Ukrainian breadcrumb label (registered in
    `INSTALLED_APPS` instead of the plain `'django.contrib.auth'`)."""

    verbose_name = 'Панель керування'
