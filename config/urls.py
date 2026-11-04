"""Root URL configuration — TCMS (SRS §3 module routing).

Module prefixes are fixed here so each module PR only fills its own include().
Admin is at a non-default path in prod only (FR-ADM-001 — obscurity layer,
never the sole control). Health check (FR-ADM-005) is a trivial no-data view.
"""

from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def healthz(request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("healthz", healthz, name="healthz"),
    # Accounts / auth (M-01, M-02) — login, logout, profile/role
    path("accounts/", include("accounts.urls")),
    # Fleet master data (M-03 vehicles, M-04 drivers)
    path("fleet/", include("fleet.urls")),
    # Trips core (M-05)
    path("trips/", include("trips.urls")),
    # Dashboard & analytics (M-06)
    path("dashboard/", include("dashboard.urls")),
    # Reports & export (M-07, Admin/Office only)
    path("reports/", include("reports.urls")),
    # Django admin — local default; prod moves via BACKOFFICE_PATH env → /backoffice/
    path("admin/", admin.site.urls),
]
