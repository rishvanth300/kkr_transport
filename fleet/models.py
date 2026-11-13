from django.db import models


class Vehicle(models.Model):
    """Registered vehicle/truck record for fleet management."""

    WHEEL_CHOICES = [
        (6, "6 wheels"),
        (10, "10 wheels"),
        (12, "12 wheels"),
    ]

    vehicle_number = models.CharField(
        "Vehicle Number (Registration Number)",
        max_length=20,
        unique=True,
    )
    vehicle_make = models.CharField("Vehicle Make", max_length=100)
    vehicle_model = models.CharField("Vehicle Model", max_length=100)
    manufacturing_year = models.PositiveIntegerField("Manufacturing Year")
    wheel_configuration = models.PositiveSmallIntegerField("Wheel Configuration",choices=WHEEL_CHOICES,)
    fc_expiry_date = models.DateField("FC Expiry Date")
    insurance_expiry_date = models.DateField("Insurance Expiry Date")
    pollution_certificate_expiry_date = models.DateField("Pollution Certificate Expiry Date")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["vehicle_number"]

    def __str__(self):
        return self.vehicle_number


class Driver(models.Model):
    """Registered driver record with optional vehicle assignment."""

    driver_name = models.CharField("Driver Name", max_length=150)
    mobile_number = models.CharField("Mobile Number", max_length=15)
    alternate_mobile_number = models.CharField("Alternate Mobile Number", max_length=15, blank=True)
    address = models.TextField("Address")
    driving_licence_number = models.CharField("Driving Licence Number", max_length=30, unique=True)
    licence_expiry_date = models.DateField("Licence Expiry Date")
    assigned_vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="drivers",
        verbose_name="Assigned Truck",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["driver_name", "id"]

    def __str__(self):
        return self.driver_name
