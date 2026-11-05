from functools import wraps

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from accounts.models import Staff

from .forms import StaffCreationForm, StaffEditForm, StaffPasswordResetForm


def superadmin_required(view):
    """Restrict a view to authenticated Django superusers.

    Args:
        view: The protected view callable.

    Returns:
        A wrapper that redirects anonymous users to login and raises HTTP 403
        for authenticated non-superusers before calling the original view.
    """

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
    """Restrict a view to active, non-superuser Staff profiles.

    Args:
        view: The protected view callable.

    Returns:
        A wrapper that loads the active Staff profile, attaches it to the
        request, and invokes the view, or denies unauthorized access.
    """

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
    """Render the Super Admin dashboard with database-backed staff records.

    Args:
        request: An authenticated Super Admin request.

    Returns:
        The rendered dashboard response. Staff profiles and their linked User
        records are queried dynamically with ``select_related``.
    """
    return render(
        request,
        "dashboard/super_admin.html",
        {"staff_members": Staff.objects.select_related("user")},
    )


@superadmin_required
@never_cache
def create_staff(request):
    """Display and process the Super Admin-only staff registration form.

    Args:
        request: A GET request to display the form or a POST request carrying
            submitted staff details.

    Returns:
        The form page with validation errors, or a redirect to the dashboard
        after the form saves both records successfully.
    """
    if request.method == "POST":
        form = StaffCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Staff account created successfully.")
            return redirect("dashboard:super_admin")
    else:
        form = StaffCreationForm()
    return render(request, "dashboard/create_staff.html", {"form": form})


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
    return render(request, "dashboard/staff_detail.html", {"staff": staff})


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
    return render(request, "dashboard/edit_staff.html", {"form": form, "staff": staff})


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
        {"form": form, "staff": staff},
    )


@staff_required
@never_cache
def home(request):
    """Render the authenticated Staff dashboard for the current profile.

    Args:
        request: A request authorized by ``staff_required``.

    Returns:
        The Staff dashboard response using the profile loaded by the decorator.
    """
    return render(request, "dashboard/index.html", {"staff": request.staff_profile})
