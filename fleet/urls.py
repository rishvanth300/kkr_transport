"""Fleet URLs for vehicle and driver management."""

from django.urls import path

from . import views

app_name = "fleet"

urlpatterns = [
    path("vehicles/add/", views.vehicle_add, name="vehicle_add"),
    path("vehicles/<int:pk>/", views.vehicle_detail, name="vehicle_detail"),
    path("vehicles/<int:pk>/financial/", views.vehicle_financial, name="vehicle_financial"),
    path("drivers/", views.driver_list, name="driver_list"),
    path("drivers/add/", views.driver_add, name="driver_add"),
    path("drivers/<int:pk>/", views.driver_detail, name="driver_detail"),
    path("drivers/<int:pk>/edit/", views.driver_edit, name="driver_edit"),
]
