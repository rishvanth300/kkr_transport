from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def healthz(request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("healthz", healthz, name="healthz"),
    path("accounts/", include("accounts.urls")),
    path("fleet/", include("fleet.urls")),
    path("trips/", include("trips.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("reports/", include("reports.urls")),
    path("admin/", admin.site.urls),
]
