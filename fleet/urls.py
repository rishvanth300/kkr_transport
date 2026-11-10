"""Fleet URLs for vehicle and driver management."""

from django.urls import path

from . import views

app_name = "fleet"

urlpatterns = [
    path("vehicles/add/", views.vehicle_add, name="vehicle_add"),
    path("drivers/add/", views.driver_add, name="driver_add"),
]
