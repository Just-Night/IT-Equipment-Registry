"""Role helpers.

Roles are implemented as Django `Group`s (`Technician`, `Employee`) plus
`is_superuser` for the admin role (see PLAN.md §1 "Ролі та права").

DRF permission classes that use these helpers are added in Stage 6 — this
module intentionally only contains the plain helper functions needed by
services/admin code in earlier stages.
"""
from apps.users.choices import GROUP_EMPLOYEE, GROUP_TECHNICIAN


def is_admin(user) -> bool:
    """Admin role == Django superuser.

    Kept intentionally simple, as agreed in the task: `is_staff` alone does
    not make a user an admin for this project's role model.
    """
    return bool(user and user.is_authenticated and user.is_superuser)


def is_technician(user) -> bool:
    """True if the user belongs to the `Technician` group.

    Membership in a group is checked explicitly: a superuser does NOT count
    as a technician unless they are also added to the `Technician` group.
    """
    return bool(user and user.is_authenticated and user.groups.filter(name=GROUP_TECHNICIAN).exists())


def is_employee(user) -> bool:
    """True if the user belongs to the `Employee` group.

    Same rule as `is_technician`: superuser status alone does not count.
    """
    return bool(user and user.is_authenticated and user.groups.filter(name=GROUP_EMPLOYEE).exists())
