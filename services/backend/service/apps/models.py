# Mono-app aggregator: Django only sees the single app `apps`, so every
# domain package's models must be imported here explicitly (not `import *`)
# for `makemigrations apps` to find them and put them in one migration line.
from apps.equipment.models import Category, Location, Equipment  # NOQA
from apps.maintenance.models import Inspection, Incident  # NOQA

