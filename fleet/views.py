"""Fleet views for vehicle registration and driver entry points."""

from django.contrib import messages
from django.shortcuts import redirect, render

from dashboard.views import dashboard_access_required

from .forms import VehicleRegistrationForm
from .models import Vehicle


@dashboard_access_required
def vehicle_add(request):
    """Register a new vehicle. Accessible to Super Admin and Staff."""
    if request.method == "POST":
        form = VehicleRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Vehicle registered successfully.")
            return redirect("dashboard:trucks")
    else:
        form = VehicleRegistrationForm()

    return render(
        request,
        "fleet/vehicle_form.html",
        {
            "form": form,
            "is_super_admin": getattr(request, "is_super_admin", False),
            "staff_profile": getattr(request, "staff_profile", None),
            "active_nav": "trucks",
            "page_title": "Add Vehicle",
        },
    )


@dashboard_access_required
def driver_add(request):
    """Dedicated driver registration entry point (prepared for future module)."""
    return render(
        request,
        "fleet/driver_add.html",
        {
            "is_super_admin": getattr(request, "is_super_admin", False),
            "staff_profile": getattr(request, "staff_profile", None),
            "active_nav": "drivers",
        },
    )
