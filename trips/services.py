from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.db.models import DecimalField, OuterRef, Subquery, Sum, Value
from django.db.models.functions import Coalesce

from .models import (
    TripSheet, DieselEntry, DriverAdvance, DriverBataAllocation, DriverPayment, q2, q3
)

MONEY_FIELD = DecimalField(max_digits=12, decimal_places=2)
QTY_FIELD = DecimalField(max_digits=12, decimal_places=3)


def calculate_trip_financials(trip: TripSheet):
    """
    Compute and assign all derived financial fields on a TripSheet instance (no save).

    Clear, non-double-counting rules:
    - distance_km = closing_km - starting_km (>= 0)
    - diesel_cost = diesel_quantity * diesel_price_per_litre
    - mileage = distance_km / diesel_quantity when diesel_quantity > 0 (else None)
    - driver_bata = total_revenue * bata_percentage / 100 (trip expense, stored per trip)
    - total_cost (trip expenses) = diesel + loading + unloading + toll + driver_bata
      + load_commission + maintenance + other_expenses
    - profit = total_revenue - total_cost

    Driver advances/settlement allocations are separate transactions and are NEVER
    included in trip expenses or company profit.
    """
    start = trip.starting_km or Decimal("0")
    close = trip.closing_km or Decimal("0")
    distance = close - start
    if distance < 0:
        distance = Decimal("0")
    trip.distance_km = q2(distance)

    revenue = trip.total_revenue or Decimal("0")
    qty = trip.diesel_quantity or Decimal("0")
    price = trip.diesel_price_per_litre or Decimal("0")
    diesel_cost = qty * price
    trip.diesel_cost = q2(diesel_cost)

    if qty > 0 and distance > 0:
        trip.mileage = q2(distance / qty)
    else:
        trip.mileage = None

    # Driver bata is a percentage of trip revenue (actual % stored per trip for history)
    default_pct = getattr(settings, "DEFAULT_DRIVER_BATA_PERCENTAGE", Decimal("10.00"))
    try:
        pct = Decimal(trip.bata_percentage) if trip.bata_percentage is not None else Decimal(default_pct)
    except Exception:
        pct = Decimal(default_pct)
    if pct < 0:
        pct = Decimal("0")
    trip.bata_percentage = q2(pct)
    bata = q2(revenue * pct / Decimal("100"))
    trip.driver_bata = bata

    loading = trip.loading_cost or Decimal("0")
    unloading = trip.unloading_cost or Decimal("0")
    toll = trip.toll_cost or Decimal("0")
    commission = trip.load_commission or Decimal("0")
    maintenance = trip.maintenance_cost or Decimal("0")
    other = trip.other_expenses or Decimal("0")

    total_cost = diesel_cost + loading + unloading + toll + bata + commission + maintenance + other
    trip.total_cost = q2(total_cost)
    trip.profit = q2(revenue - total_cost)
    return trip


def sync_primary_diesel_entry(trip: TripSheet):
    """Keep a primary DieselEntry in sync with TripSheet diesel summary for extensibility."""
    qty = trip.diesel_quantity or Decimal("0")
    price = trip.diesel_price_per_litre or Decimal("0")
    # If there are multiple entries, treat them as source of truth (future use); do not overwrite.
    if trip.pk and trip.diesel_entries.count() > 1:
        agg = trip.diesel_entries.aggregate(
            total_qty=Coalesce(Sum("quantity_litres"), Decimal("0")),
            total_cost=Coalesce(Sum("cost"), Decimal("0")),
        )
        trip.diesel_quantity = q3(agg["total_qty"])
        trip.diesel_cost = q2(agg["total_cost"])
        if trip.distance_km and trip.diesel_quantity > 0:
            trip.mileage = q2(trip.distance_km / trip.diesel_quantity)
        elif trip.distance_km is not None and trip.diesel_quantity <= 0:
            trip.mileage = None
        return
    if qty > 0 or price > 0:
        entry, _ = DieselEntry.objects.get_or_create(
            trip_sheet=trip,
            defaults={
                "quantity_litres": q3(qty),
                "price_per_litre": q2(price),
                "cost": q2(qty * price),
            },
        )
        # ensure single primary entry reflects current summary
        DieselEntry.objects.filter(trip_sheet=trip).exclude(pk=entry.pk).delete()
        entry.quantity_litres = q3(qty)
        entry.price_per_litre = q2(price)
        entry.cost = q2(qty * price)
        entry.save(update_fields=["quantity_litres", "price_per_litre", "cost"])
    else:
        if trip.pk:
            DieselEntry.objects.filter(trip_sheet=trip).delete()


@transaction.atomic
def save_trip_sheet(trip: TripSheet, diesel_entries_data=None):
    """Validate, recalculate, and persist trip (and optional diesel entries) atomically."""
    calculate_trip_financials(trip)
    trip.full_clean()
    trip.save()
    if diesel_entries_data is not None:
        # future multi-entry support: replace entries with provided data
        trip.diesel_entries.all().delete()
        total_qty = Decimal("0")
        total_cost = Decimal("0")
        for item in diesel_entries_data:
            qty = Decimal(item.get("quantity_litres") or 0)
            price = Decimal(item.get("price_per_litre") or 0)
            if qty == 0 and price == 0:
                continue
            DieselEntry.objects.create(
                trip_sheet=trip,
                quantity_litres=q3(qty),
                price_per_litre=q2(price),
                note=item.get("note", ""),
            )
            total_qty += qty
            total_cost += (qty * price)
        trip.diesel_quantity = q3(total_qty)
        trip.diesel_price_per_litre = q2((total_cost / total_qty) if total_qty > 0 else Decimal("0"))
        trip.diesel_cost = q2(total_cost)
        calculate_trip_financials(trip)
        trip.save()
    else:
        sync_primary_diesel_entry(trip)
        # recalc in case entries affected aggregates (multi-entry guard)
        calculate_trip_financials(trip)
        trip.save()
    return trip


def _zero_money():
    return Value(Decimal("0.00"), output_field=MONEY_FIELD)


def get_driver_outstanding_bata(driver):
    """Return driver's balance due: max(bata earned - total paid, 0)."""
    total_bata = TripSheet.objects.filter(driver=driver).aggregate(
        total=Coalesce(Sum("driver_bata"), _zero_money())
    )["total"] or Decimal("0.00")
    total_advances = DriverAdvance.objects.filter(driver=driver).aggregate(
        total=Coalesce(Sum("amount"), _zero_money())
    )["total"] or Decimal("0.00")
    total_other = DriverPayment.objects.filter(driver=driver).aggregate(
        total=Coalesce(Sum("amount"), _zero_money())
    )["total"] or Decimal("0.00")
    return q2(max(total_bata - (total_advances + total_other), Decimal("0.00")))


def get_driver_financial_summaries(drivers, include_details=True):
    """Return financial summaries for drivers using set-based aggregates (avoids per-driver/trip N+1)."""
    driver_ids = [d.id for d in drivers]
    if not driver_ids:
        return []

    bata_by_driver = {
        row["driver_id"]: (row["total"] or Decimal("0.00"))
        for row in TripSheet.objects.filter(driver_id__in=driver_ids)
        .values("driver_id")
        .annotate(total=Coalesce(Sum("driver_bata"), _zero_money()))
    }
    advances_by_driver = {
        row["driver_id"]: (row["total"] or Decimal("0.00"))
        for row in DriverAdvance.objects.filter(driver_id__in=driver_ids)
        .values("driver_id")
        .annotate(total=Coalesce(Sum("amount"), _zero_money()))
    }
    payments_by_driver = {
        row["driver_id"]: (row["total"] or Decimal("0.00"))
        for row in DriverPayment.objects.filter(driver_id__in=driver_ids)
        .values("driver_id")
        .annotate(total=Coalesce(Sum("amount"), _zero_money()))
    }
    settled_by_driver = {
        row["trip_sheet__driver_id"]: (row["total"] or Decimal("0.00"))
        for row in DriverBataAllocation.objects.filter(trip_sheet__driver_id__in=driver_ids)
        .values("trip_sheet__driver_id")
        .annotate(total=Coalesce(Sum("amount_allocated"), _zero_money()))
    }
    advance_funded_settled_by_driver = {
        row["advance__driver_id"]: (row["total"] or Decimal("0.00"))
        for row in DriverBataAllocation.objects.filter(advance__driver_id__in=driver_ids)
        .values("advance__driver_id")
        .annotate(total=Coalesce(Sum("amount_allocated"), _zero_money()))
    }

    summaries = []
    for driver in drivers:
        total_bata = q2(bata_by_driver.get(driver.id, Decimal("0.00")))
        advance_given = q2(advances_by_driver.get(driver.id, Decimal("0.00")))
        other_payment = q2(payments_by_driver.get(driver.id, Decimal("0.00")))
        total_paid = q2(advance_given + other_payment)
        balance_due = q2(max(total_bata - total_paid, Decimal("0.00")))
        extra_advance = q2(max(total_paid - total_bata, Decimal("0.00")))

        total_settled = q2(settled_by_driver.get(driver.id, Decimal("0.00")))
        advance_funded_settled = q2(advance_funded_settled_by_driver.get(driver.id, Decimal("0.00")))
        unallocated_advance_amount = q2(max(advance_given - advance_funded_settled, Decimal("0.00")))

        trip_rows = []
        advances_qs = DriverAdvance.objects.none()
        payments_qs = DriverPayment.objects.none()
        if include_details:
            allocation_subquery = (
                DriverBataAllocation.objects.filter(trip_sheet=OuterRef("pk"))
                .values("trip_sheet")
                .annotate(total=Coalesce(Sum("amount_allocated"), _zero_money()))
                .values("total")[:1]
            )
            trips_qs = (
                TripSheet.objects.filter(driver=driver)
                .select_related("vehicle")
                .annotate(allocated_total=Coalesce(Subquery(allocation_subquery), _zero_money()))
                .order_by("-trip_date", "-id")
            )
            for t in trips_qs:
                allocated = q2(t.allocated_total or Decimal("0.00"))
                trip_rows.append({
                    "trip": t,
                    "bata": q2(t.driver_bata or Decimal("0.00")),
                    "allocated": allocated,
                    "settled": allocated,
                    "outstanding": q2(max((t.driver_bata or Decimal("0.00")) - allocated, Decimal("0.00"))),
                    "bata_percentage": q2(t.bata_percentage or Decimal("0.00")),
                })

            advance_alloc_subquery = (
                DriverBataAllocation.objects.filter(advance=OuterRef("pk"))
                .values("advance")
                .annotate(total=Coalesce(Sum("amount_allocated"), _zero_money()))
                .values("total")[:1]
            )
            advances_qs = (
                DriverAdvance.objects.filter(driver=driver)
                .select_related("recorded_by")
                .annotate(allocated_total=Coalesce(Subquery(advance_alloc_subquery), _zero_money()))
                .order_by("-payment_date", "-id")
            )
            payments_qs = (
                DriverPayment.objects.filter(driver=driver)
                .select_related("recorded_by")
                .order_by("-payment_date", "-id")
            )

        summaries.append({
            "driver": driver,
            "driver_bata": total_bata,
            "total_bata": total_bata,
            "total_bata_earned": total_bata,
            "advance_given": advance_given,
            "total_advances": advance_given,
            "total_advances_received": advance_given,
            "other_payment": other_payment,
            "total_other_payments": other_payment,
            "total_paid": total_paid,
            "balance_due": balance_due,
            "extra_advance": extra_advance,
            # Backward-compatible keys (now aligned to requested balance semantics)
            "total_outstanding": balance_due,
            "remaining_payable": balance_due,
            "outstanding_driver_payable": balance_due,
            "excess_advance_balance": extra_advance,
            "unallocated_advances": unallocated_advance_amount,
            # Allocation/settlement history (trip-level) preserved
            "total_allocated": total_settled,
            "total_settled": total_settled,
            "total_settled_payments": total_settled,
            "advance_funded_settled": advance_funded_settled,
            "trip_rows": trip_rows,
            "advances": advances_qs,
            "payments": payments_qs,
        })
    return summaries


def get_driver_financial_summary(driver, include_details=True):
    """
    Return driver bata/advance/settlement summary with clear, non-double-counting semantics.

    - Total Bata Earned: sum of trip driver_bata (trip expense, % of revenue per trip).
    - Total Advances Received: sum of DriverAdvance amounts (separate transactions).
    - Total Payments Settled: sum of DriverBataAllocation amounts applied against bata.
      (Advances fund settlements; allocations are the settled/applied payments. Counting
      settlements separately from advances prevents double subtraction.)
    - Remaining Payable (outstanding bata liability): max(Bata Earned - Settled, 0).
    - Excess Advance Balance (carry forward): max(Advances Received - Settled, 0).

    Advances/settlements are never included in trip expenses or company profit.
    """
    summaries = get_driver_financial_summaries([driver], include_details=include_details)
    return summaries[0] if summaries else {}


@transaction.atomic
def create_advance_and_allocate(driver, amount, payment_date, payment_method, reference, description, recorded_by, allocations=None):
    """Create a DriverAdvance transaction and optionally allocate to trip bata atomically."""
    adv = DriverAdvance(
        driver=driver,
        amount=q2(amount),
        payment_date=payment_date,
        payment_method=payment_method or "cash",
        reference=reference or "",
        description=description or "",
        recorded_by=recorded_by,
    )
    adv.full_clean()
    adv.save()
    allocations = allocations or []
    for alloc in allocations:
        trip = alloc["trip"]
        amt = q2(alloc["amount"])
        if amt <= 0:
            continue
        # lock rows to prevent race over-allocation
        trip_locked = TripSheet.objects.select_for_update().get(pk=trip.pk)
        adv_locked = DriverAdvance.objects.select_for_update().get(pk=adv.pk)
        allocation = DriverBataAllocation(
            advance=adv_locked,
            trip_sheet=trip_locked,
            amount_allocated=amt,
            allocated_by=recorded_by,
            note=alloc.get("note", ""),
        )
        allocation.full_clean()
        allocation.save()
    return adv


def trip_queryset_for_request(request):
    """Base trip queryset respecting role/scope (currently global for KKR staff/admin)."""
    qs = TripSheet.objects.select_related("driver", "vehicle", "created_by")
    # Existing system: Vehicle/Driver/Staff are under KKR Transport with no company-scope fields.
    # Super Admin sees all; Staff sees all operational records (same as existing fleet/dashboard access).
    return qs
