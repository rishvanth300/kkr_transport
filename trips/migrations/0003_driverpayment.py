# Generated manually for driver payment records (additive, no existing schema changes)

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("fleet", "0003_company"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("trips", "0002_trip_financial_enhancements"),
    ]

    operations = [
        migrations.CreateModel(
            name="DriverPayment",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                (
                    "payment_date",
                    models.DateField(default=django.utils.timezone.localdate),
                ),
                (
                    "payment_method",
                    models.CharField(
                        choices=[
                            ("cash", "Cash"),
                            ("bank", "Bank Transfer"),
                            ("upi", "UPI"),
                            ("cheque", "Cheque"),
                            ("other", "Other"),
                        ],
                        default="cash",
                        max_length=20,
                    ),
                ),
                ("reference", models.CharField(blank=True, max_length=100)),
                ("description", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "driver",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="payments",
                        to="fleet.driver",
                    ),
                ),
                (
                    "recorded_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="recorded_driver_payments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-payment_date", "-id"],
            },
        ),
    ]
