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

    Vehicle records are available via the fleet app. Driver, trip-based diesel,
    revenue/expense, and audit-log models are not yet implemented; diesel cost
    must be derived from actual Trip Sheet records in the upcoming module.
    """
    from fleet.models import Vehicle

    total_trucks = Vehicle.objects.count()
    return {
        "total_trucks": total_trucks,
        "total_drivers": None,
        "total_revenue": None,
        "total_expenses": None,
        "trucks_available": True,
        "drivers_available": False,
        "financial_available": False,
        "audit_logs_available": False,
        "audit_logs": [],
    }
