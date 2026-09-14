from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage


class MediaStorage(S3Boto3Storage):
    location = "media"
    default_acl = "public-read"
    file_overwrite = False
    querystring_auth = False
    custom_domain = getattr(settings, "S3_CUSTOM_DOMAIN", None)


class StaticStorage(S3Boto3Storage):
    location = "static"
    default_acl = "private"
    file_overwrite = True
    querystring_auth = True
    querystring_expire = 3600
    custom_domain = None
