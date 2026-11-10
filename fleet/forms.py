import datetime

from django import forms

from .models import Vehicle


class VehicleRegistrationForm(forms.ModelForm):
    """Validate and register a new vehicle."""

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
            "fc_expiry_date": forms.DateInput(attrs={"type": "date"}),
            "insurance_expiry_date": forms.DateInput(attrs={"type": "date"}),
            "pollution_certificate_expiry_date": forms.DateInput(attrs={"type": "date"}),
            "manufacturing_year": forms.NumberInput(attrs={"min": 1950}),
        }

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

    def clean_manufacturing_year(self):
        year = self.cleaned_data.get("manufacturing_year")
        if year is None:
            return year
        current_year = datetime.date.today().year + 1
        if year < 1950 or year > current_year:
            raise forms.ValidationError(
                f"Enter a valid manufacturing year between 1950 and {current_year}."
            )
        return year
