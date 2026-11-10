"""Trips views — Trip Sheet module entry point (prepared)."""

from django.shortcuts import render

from dashboard.views import dashboard_access_required


@dashboard_access_required
def trip_sheet_add(request):
    """Dedicated Trip Sheet entry point. Form implementation in next module."""
    return render(
        request,
        "trips/trip_sheet_add.html",
        {
            "is_super_admin": getattr(request, "is_super_admin", False),
            "staff_profile": getattr(request, "staff_profile", None),
            "active_nav": "trips",
        },
    )
