import datetime

from django import forms

from .models import Vehicle


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

