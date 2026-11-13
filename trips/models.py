from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, Sum
from django.utils import timezone


Q2 = Decimal("0.01")
Q3 = Decimal("0.001")


def q2(value):
    if value is None:
        return None
    return Decimal(value).quantize(Q2, rounding=ROUND_HALF_UP)


def q3(value):
    if value is None:
        return None
    return Decimal(value).quantize(Q3, rounding=ROUND_HALF_UP)


def get_default_bata_percentage():
    val = getattr(settings, "DEFAULT_DRIVER_BATA_PERCENTAGE", Decimal("15.00"))
    try:
        return q2(val)
    except Exception:
        return Decimal("15.00")


class TripSheet(models.Model):
    """
    Trip sheet with server-authoritative financial calculations.

    Profit clarity (no double counting):
    - Trip expenses (total_cost) = diesel + toll + loading + unloading + driver_bata
      + load_commission + maintenance + other_expenses.
    - driver_bata is a trip expense calculated from revenue by bata_percentage.
    - Driver advances and bata allocations/settlements are separate financial
      transactions and are NEVER added to trip expenses or deducted from company profit.
    """

    trip_date = models.DateField()
    company_name = models.CharField("Company Name", max_length=200)
    driver = models.ForeignKey(
        "fleet.Driver", on_delete=models.PROTECT, related_name="trip_sheets"
    )
    vehicle = models.ForeignKey(
        "fleet.Vehicle", on_delete=models.PROTECT, related_name="trip_sheets"
    )
    from_location = models.CharField(max_length=150)
    to_location = models.CharField(max_length=150)
    load_type = models.CharField("Load Type", max_length=100, blank=True, default="")

    starting_km = models.DecimalField(max_digits=12, decimal_places=2)
    closing_km = models.DecimalField(max_digits=12, decimal_places=2)
    distance_km = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    diesel_quantity = models.DecimalField(max_digits=10, decimal_places=3, default=Decimal("0.000"))
    diesel_price_per_litre = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    diesel_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    mileage = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    loading_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    unloading_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    toll_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    bata_percentage = models.DecimalField(
        "Bata Percentage",
        max_digits=5,
        decimal_places=2,
        default=get_default_bata_percentage,
        help_text="Percentage of trip revenue applied as driver bata for this trip.",
    )
    driver_bata = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    load_commission = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    maintenance_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    other_expenses = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    other_expense_note = models.CharField(max_length=255, blank=True)

    total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    profit = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_trip_sheets"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-trip_date", "-id"]
        indexes = [
            models.Index(fields=["trip_date"]),
            models.Index(fields=["company_name", "trip_date"]),
            models.Index(fields=["driver", "trip_date"]),
            models.Index(fields=["vehicle", "trip_date"]),
        ]

    def __str__(self):
        return f"Trip #{self.pk or 'new'} - {self.vehicle} ({self.trip_date})"

    @property
    def company(self):
        """Backward-compatible accessor for templates/views using trip.company.name."""
        name = self.company_name or ""

        class _CompanyName:
            def __init__(self, n):
                self.name = n

            def __str__(self):
                return self.name

        return _CompanyName(name)

    def clean(self):
        errors = {}
        if not (self.company_name or "").strip():
            errors["company_name"] = "Company name is required."
        if self.closing_km is not None and self.starting_km is not None:
            if self.closing_km < self.starting_km:
                errors["closing_km"] = "Closing KM cannot be less than Starting KM."
        money_fields = [
            "total_revenue", "diesel_price_per_litre", "loading_cost", "unloading_cost",
            "toll_cost", "driver_bata", "load_commission", "maintenance_cost", "other_expenses",
        ]
        for field in money_fields:
            val = getattr(self, field, None)
            if val is not None and val < 0:
                errors[field] = "Value cannot be negative."
        if self.diesel_quantity is not None and self.diesel_quantity < 0:
            errors["diesel_quantity"] = "Diesel quantity cannot be negative."
        if self.bata_percentage is not None and self.bata_percentage < 0:
            errors["bata_percentage"] = "Bata percentage cannot be negative."
        if errors:
            raise ValidationError(errors)

    def recalculate(self, save=False):
        from .services import calculate_trip_financials
        calculate_trip_financials(self)
        if save and self.pk:
            self.save(update_fields=[
                "distance_km", "diesel_cost", "mileage", "bata_percentage", "driver_bata",
                "total_cost", "profit", "updated_at",
            ])

    @property
    def total_expenses(self):
        return self.total_cost

    @property
    def bata_allocated_amount(self):
        # Use annotated/cached value when provided to avoid per-row aggregate queries.
        cached = self.__dict__.get("allocated_total")
        if cached is None:
            cached = self.__dict__.get("bata_allocated_total")
        if cached is not None:
            return q2(cached or Decimal("0.00"))
        agg = self.bata_allocations.aggregate(total=Sum("amount_allocated"))
        return q2(agg["total"] or Decimal("0.00"))

    @property
    def bata_settled_amount(self):
        """Settled payments applied against this trip's bata (alias)."""
        return self.bata_allocated_amount

    @property
    def bata_outstanding(self):
        outstanding = (self.driver_bata or Decimal("0.00")) - self.bata_allocated_amount
        if outstanding < 0:
            outstanding = Decimal("0.00")
        return q2(outstanding)


class DieselEntry(models.Model):
    """Individual diesel fill-up; supports multiple entries per trip (extensible)."""

    trip_sheet = models.ForeignKey(
        TripSheet, on_delete=models.CASCADE, related_name="diesel_entries"
    )
    quantity_litres = models.DecimalField(max_digits=10, decimal_places=3)
    price_per_litre = models.DecimalField(max_digits=10, decimal_places=2)
    cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    filled_at = models.DateTimeField(null=True, blank=True)
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def clean(self):
        if self.quantity_litres is not None and self.quantity_litres < 0:
            raise ValidationError({"quantity_litres": "Diesel quantity cannot be negative."})
        if self.price_per_litre is not None and self.price_per_litre < 0:
            raise ValidationError({"price_per_litre": "Diesel price cannot be negative."})

    def save(self, *args, **kwargs):
        qty = self.quantity_litres or Decimal("0")
        price = self.price_per_litre or Decimal("0")
        self.cost = q2(qty * price)
        super().save(*args, **kwargs)


class DriverAdvance(models.Model):
    """Advance payment transaction to a driver (separate from trip expenses)."""

    PAYMENT_METHOD_CHOICES = [
        ("cash", "Cash"),
        ("bank", "Bank Transfer"),
        ("upi", "UPI"),
        ("cheque", "Cheque"),
        ("other", "Other"),
    ]

    driver = models.ForeignKey(
        "fleet.Driver", on_delete=models.PROTECT, related_name="advances"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateField(default=timezone.localdate)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default="cash")
    reference = models.CharField(max_length=100, blank=True)
    description = models.CharField(max_length=255, blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="recorded_driver_advances"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-payment_date", "-id"]

    def __str__(self):
        return f"Advance {self.amount} to {self.driver} on {self.payment_date}"

    def clean(self):
        if self.amount is not None and self.amount <= 0:
            raise ValidationError({"amount": "Advance amount must be greater than zero."})

    @property
    def allocated_amount(self):
        cached = self.__dict__.get("allocated_total")
        if cached is not None:
            return q2(cached or Decimal("0.00"))
        agg = self.allocations.aggregate(total=Sum("amount_allocated"))
        return q2(agg["total"] or Decimal("0.00"))

    @property
    def unallocated_amount(self):
        remaining = (self.amount or Decimal("0.00")) - self.allocated_amount
        if remaining < 0:
            remaining = Decimal("0.00")
        return q2(remaining)


class DriverBataAllocation(models.Model):
    """Allocation of a driver advance/payment against trip bata (partial allowed)."""

    advance = models.ForeignKey(
        DriverAdvance, on_delete=models.PROTECT, related_name="allocations"
    )
    trip_sheet = models.ForeignKey(
        TripSheet, on_delete=models.PROTECT, related_name="bata_allocations"
    )
    amount_allocated = models.DecimalField(max_digits=12, decimal_places=2)
    allocated_at = models.DateTimeField(auto_now_add=True)
    allocated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="bata_allocations_made"
    )
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-allocated_at", "-id"]
        constraints = [
            models.CheckConstraint(
                check=Q(amount_allocated__gt=0), name="bata_alloc_amount_gt_zero"
            ),
        ]

    def __str__(self):
        return f"{self.amount_allocated} allocated to Trip #{self.trip_sheet_id}"

    def clean(self):
        if self.amount_allocated is None or self.amount_allocated <= 0:
            raise ValidationError({"amount_allocated": "Allocation amount must be greater than zero."})
        if not self.advance_id or not self.trip_sheet_id:
            return
        # Ensure allocation is for the same driver as the trip
        if self.advance.driver_id != self.trip_sheet.driver_id:
            raise ValidationError("Advance and trip must belong to the same driver.")
        # Prevent over-allocation of advance (excluding self on update)
        adv_alloc_qs = self.advance.allocations.all()
        if self.pk:
            adv_alloc_qs = adv_alloc_qs.exclude(pk=self.pk)
        adv_allocated = adv_alloc_qs.aggregate(total=Sum("amount_allocated"))["total"] or Decimal("0.00")
        if adv_allocated + self.amount_allocated > self.advance.amount:
            raise ValidationError({"amount_allocated": "Allocation exceeds advance unallocated balance."})
        # Prevent over-allocation against trip bata outstanding
        trip_alloc_qs = self.trip_sheet.bata_allocations.all()
        if self.pk:
            trip_alloc_qs = trip_alloc_qs.exclude(pk=self.pk)
        trip_allocated = trip_alloc_qs.aggregate(total=Sum("amount_allocated"))["total"] or Decimal("0.00")
        trip_bata = self.trip_sheet.driver_bata or Decimal("0.00")
        if trip_allocated + self.amount_allocated > trip_bata:
            raise ValidationError({"amount_allocated": "Allocation exceeds trip outstanding bata."})


class DriverPayment(models.Model):
    """Other driver payment transaction (separate from advances and trip expenses)."""

    PAYMENT_METHOD_CHOICES = [
        ("cash", "Cash"),
        ("bank", "Bank Transfer"),
        ("upi", "UPI"),
        ("cheque", "Cheque"),
        ("other", "Other"),
    ]

    driver = models.ForeignKey(
        "fleet.Driver", on_delete=models.PROTECT, related_name="payments"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateField(default=timezone.localdate)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default="cash")
    reference = models.CharField(max_length=100, blank=True)
    description = models.CharField(max_length=255, blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="recorded_driver_payments"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-payment_date", "-id"]

    def __str__(self):
        return f"Payment {self.amount} to {self.driver} on {self.payment_date}"

    def clean(self):
        if self.amount is not None and self.amount <= 0:
            raise ValidationError({"amount": "Payment amount must be greater than zero."})
