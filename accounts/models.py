from django.conf import settings
from django.db import models


class Staff(models.Model):
    """Store staff-specific profile data linked to Django's authenticated user."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="staff_profile",
    )
    display_name = models.CharField(max_length=150)
    phone_number = models.CharField(max_length=20, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Configure newest-first ordering for staff management displays."""

        ordering = ["-created_at"]

    def __str__(self):
        """Return the staff member's display name for admin and debugging output."""
        return self.display_name
