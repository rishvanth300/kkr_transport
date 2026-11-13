"""Fleet views for vehicle and driver management."""

from decimal import Decimal

from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from dashboard.views import dashboard_access_required
from dashboard.services import get_vehicle_financial_summary
from trips.services import get_driver_financial_summary

from .forms import DriverForm, VehicleRegistrationForm
from .models import Driver, Vehicle


def _base_context(request, active_nav):
    return {
        "is_super_admin": getattr(request, "is_super_admin", False),
        "staff_profile": getattr(request, "staff_profile", None),
        "active_nav": active_nav,
    }


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

    context = _base_context(request, "trucks")
    context.update({"form": form, "page_title": "Add Vehicle"})
    return render(request, "fleet/vehicle_form.html", context)


@dashboard_access_required
def vehicle_detail(request, pk):
    """Display vehicle details and currently assigned drivers."""
    vehicle = get_object_or_404(
        Vehicle.objects.prefetch_related("drivers"), pk=pk
    )
    assigned_drivers = vehicle.drivers.all()
    context = _base_context(request, "trucks")
    context.update(
        {
            "vehicle": vehicle,
            "assigned_drivers": assigned_drivers,
            "page_title": f"Vehicle {vehicle.vehicle_number}",
        }
    )
    return render(request, "fleet/vehicle_detail.html", context)


@dashboard_access_required
def vehicle_financial(request, pk):
    """Dedicated financial dashboard for a single vehicle."""
    vehicle = get_object_or_404(Vehicle, pk=pk)
    filters = {
        "period": request.GET.get("period") or "",
        "day": request.GET.get("day") or "",
        "month": request.GET.get("month") or "",
        "year": request.GET.get("year") or "",
        "date_from": request.GET.get("date_from") or "",
        "date_to": request.GET.get("date_to") or "",
    }
    summary = get_vehicle_financial_summary(vehicle, filters)
    context = _base_context(request, "trucks")
    context.update({
        "vehicle": vehicle,
        "summary": summary,
        "totals": summary["totals"],
        "trips": summary["trips"],
        "filters": filters,
        "page_title": f"Vehicle Financial - {vehicle.vehicle_number}",
    })
    return render(request, "fleet/vehicle_financial.html", context)


@dashboard_access_required
def driver_list(request):
    """List driver records with assignment details."""
    drivers = Driver.objects.select_related("assigned_vehicle").all()
    context = _base_context(request, "drivers")
    context.update({"drivers": drivers, "page_title": "Driver Records"})
    return render(request, "fleet/driver_list.html", context)


@dashboard_access_required
def driver_add(request):
    """Register a new driver. Accessible to Super Admin and Staff."""
    if request.method == "POST":
        form = DriverForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                driver = form.save()
            messages.success(request, "Driver registered successfully.")
            if "save_and_assign" in request.POST:
                return redirect("fleet:driver_edit", pk=driver.pk)
            return redirect("fleet:driver_list")
    else:
        form = DriverForm()

    context = _base_context(request, "drivers")
    context.update(
        {
            "form": form,
            "page_title": "Add Driver",
            "form_title": "Register New Driver",
            "submit_label": "Save Driver",
            "is_edit": False,
        }
    )
    return render(request, "fleet/driver_form.html", context)


@dashboard_access_required
def driver_detail(request, pk):
    """Display a driver's profile, trip history, advances and settlement summary."""
    driver = get_object_or_404(
        Driver.objects.select_related("assigned_vehicle"), pk=pk
    )
    finance = get_driver_financial_summary(driver, include_details=True)
    trip_rows = finance.get("trip_rows", [])
    total_trips = len(trip_rows)
    total_distance = sum(
        ((row["trip"].distance_km or Decimal("0.00")) for row in trip_rows),
        Decimal("0.00"),
    )
    allocations = list(
        driver.trip_sheets.prefetch_related(
            "bata_allocations__advance",
            "bata_allocations__allocated_by",
        ).order_by("-trip_date", "-id")
    )
    settlement_rows = []
    for trip in allocations:
        for allocation in trip.bata_allocations.all():
            settlement_rows.append({"trip": trip, "allocation": allocation})
    settlement_rows.sort(key=lambda item: item["allocation"].allocated_at, reverse=True)

    context = _base_context(request, "drivers")
    context.update({
        "driver": driver,
        "finance": finance,
        "trip_rows": trip_rows,
        "total_trips": total_trips,
        "total_distance": total_distance,
        "settlement_rows": settlement_rows,
        "page_title": "Driver Details",
    })
    return render(request, "fleet/driver_detail.html", context)


@dashboard_access_required
def driver_edit(request, pk):
    """Edit driver details and vehicle assignment without creating duplicates."""
    driver = get_object_or_404(Driver, pk=pk)
    if request.method == "POST":
        form = DriverForm(request.POST, instance=driver)
        if form.is_valid():
            with transaction.atomic():
                form.save()
            messages.success(request, "Driver details updated successfully.")
            return redirect("fleet:driver_detail", pk=driver.pk)
    else:
        form = DriverForm(instance=driver)

    context = _base_context(request, "drivers")
    context.update(
        {
            "form": form,
            "driver": driver,
            "page_title": "Edit Driver",
            "form_title": "Edit Driver Details",
            "submit_label": "Update Driver",
            "is_edit": True,
        }
    )
    return render(request, "fleet/driver_form.html", context)
