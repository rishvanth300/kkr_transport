from django.contrib import admin
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import include, path


def root_redirect(request):
    """Send visitors from the root URL to the login page."""
    return redirect("accounts:login")


def healthz(request):
    """Return a simple response to confirm the application is running."""
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("", root_redirect, name="root"),
    path("healthz", healthz, name="healthz"),
    path("accounts/", include("accounts.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("admin/", admin.site.urls),
]
