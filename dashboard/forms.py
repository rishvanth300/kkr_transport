from django import forms
from django.contrib.auth.forms import SetPasswordForm, UserCreationForm
from django.contrib.auth.models import User
from django.db import transaction

from accounts.models import Staff


class StaffCreationForm(UserCreationForm):
    """Validate and create a Staff profile with a linked Django user."""

    display_name = forms.CharField(max_length=150)
    phone_number = forms.CharField(max_length=20, label="Phone number")

    class Meta:
        """Describe the built-in User fields represented by this form."""

        model = User
        fields = ("display_name", "phone_number")

    def __init__(self, *args, **kwargs):
        """Remove Django's internal username field from the public form."""
        super().__init__(*args, **kwargs)
        self.fields.pop("username", None)

    def clean(self):
        """Run Django's built-in password and confirmation validation."""
        return super().clean()

    def clean_phone_number(self):
        """Normalize and validate the phone-number login identifier."""
        phone_number = self.cleaned_data["phone_number"].strip()
        if not phone_number:
            raise forms.ValidationError("Phone number is required.")
        if (
            User.objects.filter(username=phone_number).exists()
            or Staff.objects.filter(phone_number=phone_number).exists()
        ):
            raise forms.ValidationError("A staff account with this phone number already exists.")
        return phone_number

    @transaction.atomic
    def save(self, commit=True):
        """Create a hashed Django user and its Staff profile atomically. """
        self.instance.username = self.cleaned_data["phone_number"]
        user = super().save(commit=False)
        if commit:
            user.save()
            Staff.objects.create(
                user=user,
                display_name=self.cleaned_data["display_name"],
                phone_number=user.username,
            )
        return user


class StaffEditForm(forms.ModelForm):
    """Edit a Staff profile and its linked phone-number login identifier."""

    class Meta:
        """Describe the Staff fields editable by a Super Admin."""

        model = Staff
        fields = ("display_name", "phone_number")

    def __init__(self, *args, **kwargs):
        """Initialize the form with the related User for uniqueness checks."""
        self.staff = kwargs.get("instance")
        super().__init__(*args, **kwargs)

    def clean_phone_number(self):
        """Reject phone numbers already used by another account."""
        phone_number = self.cleaned_data["phone_number"].strip()
        user_query = User.objects.filter(username=phone_number)
        staff_query = Staff.objects.filter(phone_number=phone_number)
        if self.staff is not None:
            user_query = user_query.exclude(pk=self.staff.user_id)
            staff_query = staff_query.exclude(pk=self.staff.pk)
        if user_query.exists() or staff_query.exists():
            raise forms.ValidationError("A staff account with this phone number already exists.")
        return phone_number

    @transaction.atomic
    def save(self, commit=True):
        """Save the profile and keep the User username synchronized."""
        staff = super().save(commit=False)
        staff.user.username = staff.phone_number
        if commit:
            staff.user.save(update_fields=["username"])
            staff.save()
        return staff


class StaffPasswordResetForm(SetPasswordForm):
    """Set a new hashed password for a Staff user's existing account."""

    def save(self, commit=True):
        """Hash and persist the replacement password using Django's API."""
        return super().save(commit=commit)
