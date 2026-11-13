from functools import wraps

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from accounts.models import Staff

from .forms import StaffCreationForm, StaffEditForm, StaffPasswordResetForm
from .services import (
    get_operational_metrics, get_staff_metrics, get_trip_financial_metrics,
    get_trip_chart_data, get_top_and_loss_trips, get_vehicle_distribution_data,
    resolve_date_range,
)


def superadmin_required(view):
    """Restrict a view to authenticated Django superusers."""

    @wraps(view)
    def wrapped(request, *args, **kwargs):
        """Apply the Super Admin authorization check to one request."""
        if not request.user.is_authenticated:
            return redirect("accounts:login")
        if not request.user.is_superuser:
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapped


def staff_required(view):
    """Restrict a view to active, non-superuser Staff profiles."""

    @wraps(view)
    def wrapped(request, *args, **kwargs):
        """Apply the Staff authorization check to one request."""
        if not request.user.is_authenticated:
            return redirect("accounts:login")
        staff = Staff.objects.filter(
            user=request.user, is_active=True, user__is_active=True
        ).first()
        if staff is None or request.user.is_superuser:
            raise PermissionDenied
        request.staff_profile = staff
        return view(request, *args, **kwargs)

    return wrapped


@superadmin_required
@never_cache
def super_admin(request):
    """Render the Super Admin dashboard with database-backed staff records."""
    from fleet.models import Driver, Vehicle

    drivers_qs = Driver.objects.select_related("assigned_vehicle")
    assigned_drivers = drivers_qs.filter(assigned_vehicle__isnull=False).count()
    unassigned_drivers = drivers_qs.filter(assigned_vehicle__isnull=True).count()
    context = {
        "is_super_admin": True,
        "active_nav": "dashboard",
        "vehicles": Vehicle.objects.all(),
        **get_staff_metrics(),
        **get_operational_metrics(),
        "chart_data": get_trip_chart_data(),
        "vehicle_distribution": get_vehicle_distribution_data(),
        "driver_visual": {
            "labels": ["Assigned", "Unassigned"],
            "values": [assigned_drivers, unassigned_drivers],
            "total": drivers_qs.count(),
        },
    }
    return render(request, "dashboard/super_admin.html", context)


@superadmin_required
@never_cache
def create_staff(request):
    """Display and process the Super Admin-only staff registration form."""
    if request.method == "POST":
        form = StaffCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Staff account created successfully.")
            return redirect("dashboard:super_admin")
    else:
        form = StaffCreationForm()
    return render(
        request,
        "dashboard/create_staff.html",
        {"form": form, "is_super_admin": True, "active_nav": "staff_create"},
    )


@superadmin_required
@require_POST
@never_cache
def toggle_staff_status(request, staff_id):
    """Toggle a staff profile and its linked User account between active states.

    Args:
        request: An authenticated Super Admin POST request.
        staff_id: The primary key of the Staff profile to update.

    Returns:
        A redirect to the staff management dashboard. The related User and
        Staff rows are updated together so login availability stays aligned.
    """
    staff = get_object_or_404(Staff.objects.select_related("user"), pk=staff_id)
    staff.is_active = not staff.is_active
    staff.user.is_active = staff.is_active
    staff.user.save(update_fields=["is_active"])
    staff.save(update_fields=["is_active"])
    status = "activated" if staff.is_active else "deactivated"
    messages.success(request, f"{staff.display_name} has been {status}.")
    return redirect("dashboard:super_admin")


@superadmin_required
@never_cache
def staff_detail(request, staff_id):
    """Display one staff member's non-sensitive account details.

    Args:
        request: An authenticated Super Admin request.
        staff_id: The Staff primary key selected from the dashboard.

    Returns:
        A rendered detail page containing database-backed identity and status
        fields only; password data is never added to the context.
    """
    staff = get_object_or_404(Staff.objects.select_related("user"), pk=staff_id)
    return render(
        request,
        "dashboard/staff_detail.html",
        {"staff": staff, "is_super_admin": True, "active_nav": "staff"},
    )


@superadmin_required
@never_cache
def edit_staff(request, staff_id):
    """Display and process Super Admin edits to staff name and phone number.

    Args:
        request: A GET request for the form or POST data from the edit form.
        staff_id: The Staff primary key being edited.

    Returns:
        The form response with validation errors, or a redirect to the detail
        page after the User and Staff records are updated atomically.
    """
    staff = get_object_or_404(Staff.objects.select_related("user"), pk=staff_id)
    if request.method == "POST":
        form = StaffEditForm(request.POST, instance=staff)
        if form.is_valid():
            form.save()
            messages.success(request, "Staff details updated successfully.")
            return redirect("dashboard:staff_detail", staff_id=staff.id)
    else:
        form = StaffEditForm(instance=staff)
    return render(
        request,
        "dashboard/edit_staff.html",
        {"form": form, "staff": staff, "is_super_admin": True, "active_nav": "staff"},
    )


@superadmin_required
@never_cache
def reset_staff_password(request, staff_id):
    """Display and process a new password for one staff account.

    Args:
        request: A GET request for the write-only form or POST password data.
        staff_id: The Staff primary key whose password is being replaced.

    Returns:
        The form response with validation errors, or a redirect after Django
        hashes and saves the replacement password.
    """
    staff = get_object_or_404(Staff.objects.select_related("user"), pk=staff_id)
    if request.method == "POST":
        form = StaffPasswordResetForm(staff.user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Staff password reset successfully.")
            return redirect("dashboard:staff_detail", staff_id=staff.id)
    else:
        form = StaffPasswordResetForm(staff.user)
    return render(
        request,
        "dashboard/reset_staff_password.html",
        {"form": form, "staff": staff, "is_super_admin": True, "active_nav": "staff"},
    )


def dashboard_access_required(view):
    """Allow authenticated superusers or active staff to access dashboard pages."""

    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("accounts:login")
        if request.user.is_superuser:
            request.staff_profile = None
            request.is_super_admin = True
            return view(request, *args, **kwargs)
        staff = Staff.objects.filter(
            user=request.user, is_active=True, user__is_active=True
        ).first()
        if staff is None:
            raise PermissionDenied
        request.staff_profile = staff
        request.is_super_admin = False
        return view(request, *args, **kwargs)

    return wrapped


@never_cache
def home(request):
    """Render the dashboard entry point for the authenticated user's role.

    Super Admins are sent to the Super Admin dashboard. Active staff users see
    the staff dashboard. Unauthenticated users are redirected to login and any
    other authenticated account is denied access.
    """
    if not request.user.is_authenticated:
        return redirect("accounts:login")
    if request.user.is_superuser:
        return redirect("dashboard:super_admin")

    staff = Staff.objects.filter(
        user=request.user, is_active=True, user__is_active=True
    ).first()
    if staff is None:
        raise PermissionDenied

    from fleet.models import Driver, Vehicle

    drivers_qs = Driver.objects.select_related("assigned_vehicle")
    assigned_drivers = drivers_qs.filter(assigned_vehicle__isnull=False).count()
    unassigned_drivers = drivers_qs.filter(assigned_vehicle__isnull=True).count()
    context = {
        "staff": staff,
        "staff_profile": staff,
        "is_super_admin": False,
        "active_nav": "dashboard",
        "vehicles": Vehicle.objects.all(),
        **get_operational_metrics(),
        "chart_data": get_trip_chart_data(),
        "vehicle_distribution": get_vehicle_distribution_data(),
        "driver_visual": {
            "labels": ["Assigned", "Unassigned"],
            "values": [assigned_drivers, unassigned_drivers],
            "total": drivers_qs.count(),
        },
    }
    return render(request, "dashboard/index.html", context)


@dashboard_access_required
@never_cache
def trucks(request):
    """Render the trucks overview and registered vehicle list."""
    from fleet.models import Vehicle

    context = {
        "staff_profile": getattr(request, "staff_profile", None),
        "is_super_admin": request.is_super_admin,
        "active_nav": "trucks",
        "vehicles": Vehicle.objects.all(),
        **get_operational_metrics(),
    }
    return render(request, "dashboard/trucks.html", context)


@dashboard_access_required
@never_cache
def drivers(request):
    """Render driver records for the current authorized role."""
    from fleet.models import Driver

    context = {
        "staff_profile": getattr(request, "staff_profile", None),
        "is_super_admin": request.is_super_admin,
        "active_nav": "drivers",
        "drivers": Driver.objects.select_related("assigned_vehicle").all(),
        **get_operational_metrics(),
    }
    return render(request, "dashboard/drivers.html", context)



@dashboard_access_required
@never_cache
def financial_overview(request):
    """Render the company-wide financial overview with vehicle-wise charts."""
    from fleet.models import Driver
    from trips.models import TripSheet

    filters = {
        "period": request.GET.get("period") or "",
        "day": request.GET.get("day") or "",
        "month": request.GET.get("month") or "",
        "year": request.GET.get("year") or "",
        "date_from": request.GET.get("date_from") or "",
        "date_to": request.GET.get("date_to") or "",
        "company": request.GET.get("company") or "",
        "driver": request.GET.get("driver") or "",
        "vehicle": request.GET.get("vehicle") or "",
    }
    date_from, date_to, period = resolve_date_range(filters)
    financial = get_trip_financial_metrics(filters)
    chart = get_trip_chart_data(filters)
    vehicle_dist = get_vehicle_distribution_data(filters)
    top_loss = get_top_and_loss_trips(filters)
    company_options = (
        TripSheet.objects.exclude(company_name="")
        .order_by("company_name")
        .values_list("company_name", flat=True)
        .distinct()
    )
    context = {
        "staff_profile": getattr(request, "staff_profile", None),
        "is_super_admin": request.is_super_admin,
        "active_nav": "financial",
        **get_operational_metrics(filters),
        "financial": financial,
        "chart_data": chart,
        "vehicle_distribution": vehicle_dist,
        "top_profit_trips": top_loss["top_profit_trips"],
        "loss_trips": top_loss["loss_trips"],
        "companies": company_options,
        "drivers": Driver.objects.order_by("driver_name"),
        "filters": filters,
        "resolved_date_from": date_from,
        "resolved_date_to": date_to,
        "resolved_period": period,
    }
    return render(request, "dashboard/financial.html", context)


@dashboard_access_required
@never_cache
def audit_logs(request):
    """Render recent audit logs for the current authorized role."""
    context = {
        "staff_profile": getattr(request, "staff_profile", None),
        "is_super_admin": request.is_super_admin,
        "active_nav": "audit",
        **get_operational_metrics(),
    }
    return render(request, "dashboard/audit_logs.html", context)
