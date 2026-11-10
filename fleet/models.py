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
    wheel_configuration = models.PositiveSmallIntegerField(
        "Wheel Configuration",
        choices=WHEEL_CHOICES,
    )
    fc_expiry_date = models.DateField("FC Expiry Date")
    insurance_expiry_date = models.DateField("Insurance Expiry Date")
    pollution_certificate_expiry_date = models.DateField(
        "Pollution Certificate Expiry Date"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["vehicle_number"]

    def __str__(self):
        return self.vehicle_number
