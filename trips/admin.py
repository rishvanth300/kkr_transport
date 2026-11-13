from django.contrib import admin
from .models import TripSheet, DieselEntry, DriverAdvance, DriverBataAllocation, DriverPayment


class DieselEntryInline(admin.TabularInline):
    model = DieselEntry
    extra = 0
    readonly_fields = ("cost", "created_at")
    fields = ("quantity_litres", "price_per_litre", "cost", "filled_at", "note")


class DriverBataAllocationInline(admin.TabularInline):
    model = DriverBataAllocation
    extra = 0
    readonly_fields = ("allocated_at", "allocated_by")
    fields = ("advance", "amount_allocated", "allocated_by", "note", "allocated_at")


@admin.register(TripSheet)
class TripSheetAdmin(admin.ModelAdmin):
    list_display = (
        "id", "trip_date", "vehicle", "company_name", "driver", "from_location", "to_location",
        "distance_km", "total_revenue", "total_cost", "profit", "diesel_cost",
    )
    list_filter = ("trip_date", "driver", "vehicle")
    search_fields = (
        "id", "vehicle__vehicle_number", "driver__driver_name", "company_name",
        "from_location", "to_location", "load_type",
    )
    list_select_related = ("vehicle", "driver", "created_by")
    ordering = ("-trip_date", "-id")
    date_hierarchy = "trip_date"
    readonly_fields = (
        "distance_km", "diesel_cost", "mileage", "driver_bata", "total_cost", "profit",
        "created_by", "created_at", "updated_at",
    )
    autocomplete_fields = ("driver", "vehicle")
    inlines = [DieselEntryInline, DriverBataAllocationInline]
    fieldsets = (
        ("Trip Information", {
            "fields": ("trip_date", "company_name", "driver", "vehicle", "from_location", "to_location", "load_type")
        }),
        ("Kilometer Details", {
            "fields": ("starting_km", "closing_km", "distance_km")
        }),
        ("Revenue & Driver Bata", {
            "fields": ("total_revenue", "bata_percentage", "driver_bata")
        }),
        ("Diesel Details", {
            "fields": ("diesel_quantity", "diesel_price_per_litre", "diesel_cost", "mileage")
        }),
        ("Trip Expense Details", {
            "fields": (
                "loading_cost", "unloading_cost", "toll_cost",
                "load_commission", "maintenance_cost", "other_expenses", "other_expense_note",
            )
        }),
        ("Financial Summary", {
            "fields": ("total_cost", "profit")
        }),
        ("Audit", {
            "fields": ("created_by", "created_at", "updated_at")
        }),
    )

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        from .services import calculate_trip_financials, sync_primary_diesel_entry
        calculate_trip_financials(obj)
        super().save_model(request, obj, form, change)
        sync_primary_diesel_entry(obj)
        calculate_trip_financials(obj)
        obj.save(update_fields=[
            "distance_km", "diesel_cost", "mileage", "bata_percentage", "driver_bata",
            "total_cost", "profit", "updated_at",
        ])

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        obj = form.instance
        from .services import calculate_trip_financials
        # if multiple diesel entries exist, aggregate
        if obj.diesel_entries.count() > 1:
            from django.db.models import Sum
            from decimal import Decimal
            from .models import q2, q3
            agg = obj.diesel_entries.aggregate(qty=Sum("quantity_litres"), cost=Sum("cost"))
            obj.diesel_quantity = q3(agg["qty"] or Decimal("0"))
            obj.diesel_cost = q2(agg["cost"] or Decimal("0"))
            obj.diesel_price_per_litre = q2((obj.diesel_cost / obj.diesel_quantity) if obj.diesel_quantity > 0 else Decimal("0"))
        calculate_trip_financials(obj)
        obj.save(update_fields=[
            "diesel_quantity", "diesel_price_per_litre", "distance_km", "diesel_cost",
            "mileage", "bata_percentage", "driver_bata", "total_cost", "profit", "updated_at",
        ])


@admin.register(DieselEntry)
class DieselEntryAdmin(admin.ModelAdmin):
    list_display = ("id", "trip_sheet", "quantity_litres", "price_per_litre", "cost", "filled_at")
    list_filter = ("filled_at",)
    search_fields = (
        "trip_sheet__id", "trip_sheet__vehicle__vehicle_number",
        "trip_sheet__driver__driver_name", "trip_sheet__company_name", "note",
    )
    list_select_related = ("trip_sheet", "trip_sheet__vehicle", "trip_sheet__driver")
    readonly_fields = ("cost", "created_at")


@admin.register(DriverAdvance)
class DriverAdvanceAdmin(admin.ModelAdmin):
    list_display = ("id", "driver", "amount", "payment_date", "payment_method", "reference", "recorded_by")
    list_filter = ("payment_date", "payment_method", "driver")
    search_fields = ("driver__driver_name", "reference", "description")
    readonly_fields = ("created_at", "allocated_amount_display", "unallocated_amount_display")
    fields = ("driver", "amount", "payment_date", "payment_method", "reference", "description", "recorded_by", "created_at", "allocated_amount_display", "unallocated_amount_display")

    def allocated_amount_display(self, obj):
        return obj.allocated_amount
    allocated_amount_display.short_description = "Allocated Amount"

    def unallocated_amount_display(self, obj):
        return obj.unallocated_amount
    unallocated_amount_display.short_description = "Unallocated Amount"


@admin.register(DriverBataAllocation)
class DriverBataAllocationAdmin(admin.ModelAdmin):
    list_display = ("id", "advance", "trip_sheet", "amount_allocated", "allocated_by", "allocated_at")
    list_filter = ("allocated_at",)
    search_fields = ("advance__driver__driver_name", "trip_sheet__id", "note")
    readonly_fields = ("allocated_at",)


@admin.register(DriverPayment)
class DriverPaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "driver", "amount", "payment_date", "payment_method", "reference", "recorded_by")
    list_filter = ("payment_date", "payment_method", "driver")
    search_fields = ("driver__driver_name", "reference", "description")
    readonly_fields = ("created_at",)
