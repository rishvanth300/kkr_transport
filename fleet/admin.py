from django.contrib import admin

from .models import Driver, Vehicle


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = (
        "vehicle_number",
        "vehicle_make",
        "vehicle_model",
        "manufacturing_year",
        "wheel_configuration",
        "fc_expiry_date",
        "insurance_expiry_date",
        "pollution_certificate_expiry_date",
        "created_at",
    )
    search_fields = ("vehicle_number", "vehicle_make", "vehicle_model")
    list_filter = ("vehicle_make", "wheel_configuration", "manufacturing_year")
    ordering = ("vehicle_number",)


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = (
        "driver_name",
        "mobile_number",
        "driving_licence_number",
        "licence_expiry_date",
        "assigned_vehicle",
        "created_at",
    )
    search_fields = (
        "driver_name",
        "mobile_number",
        "alternate_mobile_number",
        "driving_licence_number",
        "assigned_vehicle__vehicle_number",
    )
    list_filter = ("licence_expiry_date", "assigned_vehicle")
    autocomplete_fields = ("assigned_vehicle",)
    ordering = ("driver_name", "id")
