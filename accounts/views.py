from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST


class AccountLoginView(LoginView):
    """Authenticate both roles through the shared phone-number login form."""

    redirect_authenticated_user = True

    def get_success_url(self):
        """Return the dashboard URL matching the authenticated user's role.

        The method receives no additional parameters beyond ``self`` from
        Django's ``LoginView`` and returns a URL path after authentication.
        It checks the existing Django user and optional Staff profile without
        creating or changing database records.
        """
        if self.request.user.is_superuser:
            return reverse("dashboard:super_admin")
        if (
            self.request.user.is_active
            and hasattr(self.request.user, "staff_profile")
            and self.request.user.staff_profile.is_active
        ):
            return reverse("dashboard:home")
        return reverse("accounts:home")


@require_POST
@never_cache
def account_logout(request):
    """Terminate the current Django session and redirect to the login page.

    Args:
        request: The POST request containing the authenticated session.

    Returns:
        An HTTP redirect to the shared login URL. Django's ``logout`` removes
        the session data before the response is returned.
    """
    logout(request)
    return redirect("accounts:login")


@login_required
@never_cache
def home(request):
    """Send an authenticated user to the dashboard for the user's role.

    Args:
        request: The authenticated request supplied by Django.

    Returns:
        A redirect to the Super Admin or Staff dashboard, or the existing
        fallback page for an authenticated account without an application
        role. No database records are modified.
    """
    if request.user.is_superuser:
        return redirect("dashboard:super_admin")
    if (
        request.user.is_active
        and hasattr(request.user, "staff_profile")
        and request.user.staff_profile.is_active
    ):
        return redirect("dashboard:home")
    return render(request, "accounts/home.html")