from decimal import Decimal

from django import forms
from django.conf import settings
from django.utils import timezone

from fleet.models import Driver, Vehicle
from .models import TripSheet, DriverAdvance, DriverPayment, get_default_bata_percentage


class TruckSelectionForm(forms.Form):
    vehicle = forms.ModelChoiceField(
        queryset=Vehicle.objects.all().order_by("vehicle_number"),
        label="Select Truck",
        empty_label="Search and select vehicle number",
        widget=forms.Select(attrs={"class": "search-select", "data-searchable": "1"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["vehicle"].label_from_instance = lambda obj: obj.vehicle_number


class TripSheetForm(forms.ModelForm):
    """Trip sheet form.

    - Company Name and Load Type are free-text inputs.
    - Driver Bata is calculated automatically from Bata Percentage of Total Revenue.
    - Distance and diesel cost are calculated automatically on save (and previewed in UI).
    """

    class Meta:
        model = TripSheet
        fields = [
            "trip_date", "company_name", "driver", "vehicle", "from_location", "to_location", "load_type",
            "starting_km", "closing_km",
            "total_revenue",
            "diesel_quantity", "diesel_price_per_litre",
            "bata_percentage",
            "loading_cost", "unloading_cost", "toll_cost",
            "load_commission", "maintenance_cost", "other_expenses", "other_expense_note",
        ]
        widgets = {
            "trip_date": forms.DateInput(attrs={"type": "date"}),
            "company_name": forms.TextInput(attrs={"placeholder": "Enter company name"}),
            "from_location": forms.TextInput(attrs={"placeholder": "From location"}),
            "to_location": forms.TextInput(attrs={"placeholder": "To location"}),
            "load_type": forms.TextInput(attrs={"placeholder": "Enter load type"}),
            "starting_km": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "closing_km": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "total_revenue": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "diesel_quantity": forms.NumberInput(attrs={"step": "0.001", "min": "0"}),
            "diesel_price_per_litre": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "bata_percentage": forms.NumberInput(attrs={"step": "0.01", "min": "0", "max": "100"}),
            "loading_cost": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "unloading_cost": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "toll_cost": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "load_commission": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "maintenance_cost": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "other_expenses": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "other_expense_note": forms.TextInput(attrs={"placeholder": "Description/note for other expenses"}),
        }

    def __init__(self, *args, **kwargs):
        self.selected_vehicle = kwargs.pop("selected_vehicle", None)
        super().__init__(*args, **kwargs)
        self.fields["driver"].queryset = Driver.objects.all().order_by("driver_name", "id")
        self.fields["vehicle"].queryset = Vehicle.objects.all().order_by("vehicle_number")
        self.fields["driver"].empty_label = "Select driver"
        self.fields["vehicle"].empty_label = "Select vehicle"
        self.fields["trip_date"].initial = self.fields["trip_date"].initial or timezone.localdate()

        # Defaults / required flags
        if not self.instance.pk and (self.initial.get("bata_percentage") in (None, "")):
            self.fields["bata_percentage"].initial = get_default_bata_percentage()
        self.fields["bata_percentage"].required = False
        self.fields["company_name"].required = True
        self.fields["load_type"].required = False

        optional_money = [
            "loading_cost", "unloading_cost", "toll_cost",
            "load_commission", "maintenance_cost", "other_expenses",
        ]
        for name in optional_money:
            self.fields[name].required = False
        self.fields["diesel_quantity"].required = False
        self.fields["diesel_price_per_litre"].required = False
        self.fields["total_revenue"].required = False
        self.fields["other_expense_note"].required = False

        if self.selected_vehicle:
            self.fields["vehicle"].initial = self.selected_vehicle

    def clean_company_name(self):
        value = (self.cleaned_data.get("company_name") or "").strip()
        if not value:
            raise forms.ValidationError("Company name is required.")
        return value

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("starting_km")
        close = cleaned.get("closing_km")
        if start is not None and close is not None and close < start:
            self.add_error("closing_km", "Closing KM cannot be less than Starting KM.")

        numeric_non_negative = [
            "total_revenue", "diesel_quantity", "diesel_price_per_litre", "loading_cost",
            "unloading_cost", "toll_cost", "bata_percentage", "load_commission",
            "maintenance_cost", "other_expenses",
        ]
        for name in numeric_non_negative:
            val = cleaned.get(name)
            if val is not None and val < 0:
                self.add_error(name, "Value cannot be negative.")

        # Normalize optionals to 0
        for name in ["loading_cost", "unloading_cost", "toll_cost", "load_commission", "maintenance_cost", "other_expenses", "total_revenue", "diesel_quantity", "diesel_price_per_litre"]:
            if cleaned.get(name) in (None, ""):
                cleaned[name] = Decimal("0")
        if cleaned.get("bata_percentage") in (None, ""):
            cleaned["bata_percentage"] = get_default_bata_percentage()
        if cleaned.get("bata_percentage") is not None and cleaned["bata_percentage"] > Decimal("100"):
            self.add_error("bata_percentage", "Bata percentage cannot exceed 100.")
        if not cleaned.get("other_expense_note"):
            cleaned["other_expense_note"] = ""
        if cleaned.get("load_type") is None:
            cleaned["load_type"] = ""
        cleaned["load_type"] = (cleaned.get("load_type") or "").strip()

        vehicle = cleaned.get("vehicle") or self.selected_vehicle or getattr(self.instance, "vehicle", None)
        driver = cleaned.get("driver")
        if vehicle is None:
            self.add_error("vehicle", "Vehicle selection is required.")
        if driver is None:
            self.add_error("driver", "Driver selection is required.")
        # Company is free-text (required) - no FK ownership validation.
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.selected_vehicle:
            instance.vehicle = self.selected_vehicle
        if commit:
            instance.save()
        return instance


class DriverAdvanceForm(forms.ModelForm):
    allocate_trip = forms.ModelChoiceField(
        queryset=TripSheet.objects.none(), required=False, label="Allocate to Trip (optional)",
        empty_label="Do not allocate now"
    )
    allocate_amount = forms.DecimalField(
        required=False, min_value=Decimal("0.01"), decimal_places=2, max_digits=12,
        label="Allocation Amount"
    )

    class Meta:
        model = DriverAdvance
        fields = ["driver", "amount", "payment_date", "payment_method", "reference", "description"]
        widgets = {
            "payment_date": forms.DateInput(attrs={"type": "date"}),
            "amount": forms.NumberInput(attrs={"step": "0.01", "min": "0.01"}),
            "reference": forms.TextInput(attrs={"placeholder": "Reference / receipt no."}),
            "description": forms.TextInput(attrs={"placeholder": "Description"}),
        }

    def __init__(self, *args, **kwargs):
        driver = kwargs.pop("driver", None)
        super().__init__(*args, **kwargs)
        self.fields["driver"].queryset = Driver.objects.all().order_by("driver_name")
        self.fields["payment_date"].initial = timezone.localdate()
        qs = TripSheet.objects.select_related("vehicle").order_by("-trip_date", "-id")
        if driver:
            qs = qs.filter(driver=driver)
            self.fields["driver"].initial = driver
        self.fields["allocate_trip"].queryset = qs

    def clean(self):
        cleaned = super().clean()
        trip = cleaned.get("allocate_trip")
        amt = cleaned.get("allocate_amount")
        advance_amt = cleaned.get("amount") or Decimal("0")
        if trip and not amt:
            self.add_error("allocate_amount", "Enter allocation amount for selected trip.")
        if amt and not trip:
            self.add_error("allocate_trip", "Select a trip to allocate against.")
        if trip and amt:
            driver = cleaned.get("driver")
            if driver and trip.driver_id != driver.id:
                self.add_error("allocate_trip", "Selected trip does not belong to this driver.")
            if amt > advance_amt:
                self.add_error("allocate_amount", "Allocation cannot exceed advance amount.")
            outstanding = trip.bata_outstanding
            if amt > outstanding:
                self.add_error("allocate_amount", f"Allocation exceeds trip outstanding bata ({outstanding}).")
        return cleaned


class DriverPaymentForm(forms.ModelForm):
    class Meta:
        model = DriverPayment
        fields = ["driver", "amount", "payment_date", "payment_method", "reference", "description"]
        widgets = {
            "payment_date": forms.DateInput(attrs={"type": "date"}),
            "amount": forms.NumberInput(attrs={"step": "0.01", "min": "0.01"}),
            "reference": forms.TextInput(attrs={"placeholder": "Reference number (optional)"}),
            "description": forms.TextInput(attrs={"placeholder": "Description (optional)"}),
        }
        labels = {
            "driver": "Driver",
            "amount": "Payment amount",
            "payment_date": "Payment date",
            "payment_method": "Payment method",
            "reference": "Reference number (optional)",
            "description": "Description (optional)",
        }

    def __init__(self, *args, **kwargs):
        driver = kwargs.pop("driver", None)
        super().__init__(*args, **kwargs)
        self.fields["driver"].queryset = Driver.objects.all().order_by("driver_name")
        self.fields["payment_date"].initial = timezone.localdate()
        self.fields["reference"].required = False
        self.fields["description"].required = False
        if driver:
            self.fields["driver"].initial = driver

    def clean_amount(self):
        amount = self.cleaned_data.get("amount")
        if amount is None or amount <= Decimal("0"):
            raise forms.ValidationError("Payment amount must be greater than zero.")
        return amount
