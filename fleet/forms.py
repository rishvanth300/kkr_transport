import datetime
import re

from django import forms

from .models import Driver, Vehicle


MAKE_CHOICES = [
    ("", "Select make"),
    ("Tata", "Tata"),
    ("BharatBenz", "BharatBenz"),
    ("Ashok Leyland", "Ashok Leyland"),
    ("Eicher", "Eicher"),
    ("Mahindra", "Mahindra"),
    ("Volvo", "Volvo"),
    ("Other", "Other"),
]


class VehicleRegistrationForm(forms.ModelForm):
    """Validate and register a new vehicle."""

    vehicle_make = forms.ChoiceField(label="Vehicle Make", choices=MAKE_CHOICES)
    manufacturing_year = forms.TypedChoiceField(
        label="Manufacturing Year",
        coerce=int,
        choices=[],
    )

    class Meta:
        model = Vehicle
        fields = [
            "vehicle_number",
            "vehicle_make",
            "vehicle_model",
            "manufacturing_year",
            "wheel_configuration",
            "fc_expiry_date",
            "insurance_expiry_date",
            "pollution_certificate_expiry_date",
        ]
        widgets = {
            "vehicle_number": forms.TextInput(attrs={"placeholder": "e.g. TN01AB1234"}),
            "vehicle_model": forms.TextInput(attrs={"placeholder": "e.g. LPT 2818"}),
            "fc_expiry_date": forms.DateInput(attrs={"type": "date"}),
            "insurance_expiry_date": forms.DateInput(attrs={"type": "date"}),
            "pollution_certificate_expiry_date": forms.DateInput(attrs={"type": "date"}),
            "wheel_configuration": forms.Select(attrs={}),
        }
        labels = {
            "vehicle_number": "Vehicle Registration Number",
            "vehicle_model": "Vehicle Model",
            "wheel_configuration": "Wheel Configuration",
            "fc_expiry_date": "FC Expiry Date",
            "insurance_expiry_date": "Insurance Expiry Date",
            "pollution_certificate_expiry_date": "Pollution Certificate Expiry Date",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        current_year = datetime.date.today().year + 1
        year_choices = [("", "Select year")] + [
            (y, str(y)) for y in range(current_year, 1949, -1)
        ]
        self.fields["manufacturing_year"].choices = year_choices
        self.fields["wheel_configuration"].choices = [("", "Select configuration")] + list(
            Vehicle.WHEEL_CHOICES
        )
        # Ensure existing/custom make values remain selectable if editing or legacy
        if self.instance and self.instance.pk and self.instance.vehicle_make:
            existing = self.instance.vehicle_make
            if all(existing != val for val, _ in MAKE_CHOICES if val):
                self.fields["vehicle_make"].choices = MAKE_CHOICES + [(existing, existing)]

    def clean_vehicle_number(self):
        value = (self.cleaned_data.get("vehicle_number") or "").strip().upper()
        if not value:
            raise forms.ValidationError("Vehicle number is required.")
        qs = Vehicle.objects.filter(vehicle_number__iexact=value)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(
                "A vehicle with this registration number already exists."
            )
        return value

    def clean_vehicle_make(self):
        value = (self.cleaned_data.get("vehicle_make") or "").strip()
        if not value:
            raise forms.ValidationError("Vehicle make is required.")
        return value

    def clean_manufacturing_year(self):
        year = self.cleaned_data.get("manufacturing_year")
        if year in (None, "", 0):
            raise forms.ValidationError("Manufacturing year is required.")
        year = int(year)
        current_year = datetime.date.today().year + 1
        if year < 1950 or year > current_year:
            raise forms.ValidationError(
                f"Enter a valid manufacturing year between 1950 and {current_year}."
            )
        return year

    def clean_wheel_configuration(self):
        value = self.cleaned_data.get("wheel_configuration")
        if value in (None, ""):
            raise forms.ValidationError("Wheel configuration is required.")
        return value


def _normalize_mobile(value):
    digits = re.sub(r"\D", "", value or "")
    return digits


def _validate_mobile(value, field_label):
    digits = _normalize_mobile(value)
    if not digits:
        raise forms.ValidationError(f"{field_label} is required.")
    if len(digits) < 10 or len(digits) > 15:
        raise forms.ValidationError(
            f"Enter a valid {field_label.lower()} (10 to 15 digits)."
        )
    return digits


class DriverForm(forms.ModelForm):
    """Register or edit a driver and manage vehicle assignment."""

    assigned_vehicle = forms.ModelChoiceField(
        label="Assigned Truck",
        queryset=Vehicle.objects.none(),
        required=False,
        empty_label="Select truck",
    )

    class Meta:
        model = Driver
        fields = [
            "driver_name",
            "mobile_number",
            "alternate_mobile_number",
            "address",
            "driving_licence_number",
            "licence_expiry_date",
            "assigned_vehicle",
        ]
        widgets = {
            "driver_name": forms.TextInput(attrs={"placeholder": "Full name"}),
            "mobile_number": forms.TextInput(attrs={"placeholder": "10-digit mobile number"}),
            "alternate_mobile_number": forms.TextInput(
                attrs={"placeholder": "Alternate mobile (optional)"}
            ),
            "address": forms.Textarea(attrs={"rows": 3, "placeholder": "Address"}),
            "driving_licence_number": forms.TextInput(attrs={"placeholder": "Licence number"}),
            "licence_expiry_date": forms.DateInput(attrs={"type": "date"}),
        }
        labels = {
            "driver_name": "Driver Name",
            "mobile_number": "Mobile Number",
            "alternate_mobile_number": "Alternate Mobile Number (optional)",
            "address": "Address",
            "driving_licence_number": "Driving Licence Number",
            "licence_expiry_date": "Licence Expiry Date",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assigned_vehicle"].queryset = Vehicle.objects.order_by("vehicle_number")
        self.fields["assigned_vehicle"].label_from_instance = (
            lambda obj: f"{obj.vehicle_number} — {obj.vehicle_make} {obj.vehicle_model}"
        )
        self.fields["alternate_mobile_number"].required = False

    def clean_driver_name(self):
        value = (self.cleaned_data.get("driver_name") or "").strip()
        if not value:
            raise forms.ValidationError("Driver name is required.")
        return value

    def clean_mobile_number(self):
        return _validate_mobile(self.cleaned_data.get("mobile_number"), "Mobile number")

    def clean_alternate_mobile_number(self):
        value = (self.cleaned_data.get("alternate_mobile_number") or "").strip()
        if not value:
            return ""
        return _validate_mobile(value, "Alternate mobile number")

    def clean_address(self):
        value = (self.cleaned_data.get("address") or "").strip()
        if not value:
            raise forms.ValidationError("Address is required.")
        return value

    def clean_driving_licence_number(self):
        value = (self.cleaned_data.get("driving_licence_number") or "").strip().upper()
        if not value:
            raise forms.ValidationError("Driving licence number is required.")
        qs = Driver.objects.filter(driving_licence_number__iexact=value)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(
                "A driver with this driving licence number already exists."
            )
        return value

    def clean_licence_expiry_date(self):
        value = self.cleaned_data.get("licence_expiry_date")
        if not value:
            raise forms.ValidationError("Licence expiry date is required.")
        return value

    def clean_assigned_vehicle(self):
        vehicle = self.cleaned_data.get("assigned_vehicle")
        if vehicle and not Vehicle.objects.filter(pk=vehicle.pk).exists():
            raise forms.ValidationError("Selected vehicle is not available.")
        return vehicle

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
        return instance


