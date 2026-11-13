# Generated manually for trip sheet financial enhancements

from decimal import Decimal, ROUND_HALF_UP

from django.db import migrations, models
import trips.models


def forwards(apps, schema_editor):
    TripSheet = apps.get_model("trips", "TripSheet")
    # Copy company name from FK and preserve historical bata calculation/percentage
    for trip in TripSheet.objects.select_related("company").all().iterator():
        name = ""
        try:
            if getattr(trip, "company_id", None) and getattr(trip, "company", None):
                name = trip.company.name or ""
        except Exception:
            name = ""
        trip.company_name = name
        revenue = trip.total_revenue or Decimal("0.00")
        bata = trip.driver_bata or Decimal("0.00")
        if revenue > 0:
            pct = (Decimal(bata) / Decimal(revenue)) * Decimal("100")
        else:
            pct = Decimal("0.00")
        # clamp and quantize
        if pct < 0:
            pct = Decimal("0.00")
        trip.bata_percentage = pct.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        trip.save(update_fields=["company_name", "bata_percentage"])


def backwards(apps, schema_editor):
    # No safe reverse data migration for removed FK/company mapping
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("fleet", "0003_company"),
        ("trips", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="tripsheet",
            name="company_name",
            field=models.CharField(default="", max_length=200, verbose_name="Company Name"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="tripsheet",
            name="bata_percentage",
            field=models.DecimalField(
                decimal_places=2,
                default=trips.models.get_default_bata_percentage,
                help_text="Percentage of trip revenue applied as driver bata for this trip.",
                max_digits=5,
                verbose_name="Bata Percentage",
            ),
        ),
        migrations.AlterField(
            model_name="tripsheet",
            name="load_type",
            field=models.CharField(blank=True, default="", max_length=100, verbose_name="Load Type"),
        ),
        migrations.RunPython(forwards, backwards),
        migrations.RemoveIndex(
            model_name="tripsheet",
            name="trips_trips_company_6929c5_idx",
        ),
        migrations.RemoveField(
            model_name="tripsheet",
            name="company",
        ),
        migrations.AddIndex(
            model_name="tripsheet",
            index=models.Index(fields=["company_name", "trip_date"], name="trips_trips_company_d65813_idx"),
        ),
    ]