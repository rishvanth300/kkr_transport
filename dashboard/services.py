"""Helpers for building dashboard statistics from existing database models."""

from accounts.models import Staff


def get_staff_metrics():
    """Return staff-related metrics derived from current Staff records."""
    staff_qs = Staff.objects.select_related("user")
    recent_staff = list(staff_qs[:5])
    return {
        "total_staff": staff_qs.count(),
        "active_staff": staff_qs.filter(is_active=True, user__is_active=True).count(),
        "inactive_staff": staff_qs.filter(is_active=False).count()
        + staff_qs.filter(user__is_active=False).count(),
        "recent_staff": recent_staff,
        "staff_members": list(staff_qs),
    }


def get_operational_metrics():
    """Return operational and financial metrics available in the current schema.

    Trucks, drivers, revenue, expenses, and audit-log models are not present in
    the current codebase, so these values are reported as unavailable rather than
    invented.
    """
    return {
        "total_trucks": None,
        "total_drivers": None,
        "total_revenue": None,
        "total_expenses": None,
        "trucks_available": False,
        "drivers_available": False,
        "financial_available": False,
        "audit_logs_available": False,
        "audit_logs": [],
    }
