"""Helpers for building dashboard statistics from existing database models."""

from datetime import datetime
from decimal import Decimal

from django.db.models import Sum, Count, F, DecimalField, ExpressionWrapper
from django.db.models.functions import Coalesce, TruncDay, TruncMonth, TruncYear

from accounts.models import Staff


def get_staff_metrics():
    """Return staff-related metrics derived from current Staff records."""
    staff_qs = Staff.objects.select_related("user")
    recent_staff = list(staff_qs[:5])
    return {
        "total_staff": staff_qs.count(),
        "active_staff": staff_qs.filter(is_active=True, user__is_active=True).count(),
        "inactive_staff": staff_qs.filter(is_active=False).count()
        + staff_qs.filter(user__is_active=False).count(),
        "recent_staff": recent_staff,
        "staff_members": list(staff_qs),
    }


def _parse_date(val):
    if not val:
        return None
    try:
        return datetime.strptime(val, "%Y-%m-%d").date()
    except Exception:
        return None


def resolve_date_range(filters):
    """
    Resolve date range from filters.
    Supports period=daily|monthly|yearly|custom with appropriate inputs.
    Falls back to custom date_from/date_to when period not specified.
    """
    filters = filters or {}
    period = (filters.get("period") or "").strip().lower()
    date_from = _parse_date(filters.get("date_from"))
    date_to = _parse_date(filters.get("date_to"))
    month = filters.get("month")
    year = filters.get("year")
    day = filters.get("day") or filters.get("date")

    if period == "daily":
        d = _parse_date(day) or date_from or date_to
        if d:
            return d, d, period
    elif period == "monthly":
        try:
            y = int(year) if year else (date_from.year if date_from else None)
            m = int(month) if month else (date_from.month if date_from else None)
            if y and m:
                start = datetime(y, m, 1).date()
                if m == 12:
                    end = datetime(y + 1, 1, 1).date()
                else:
                    end = datetime(y, m + 1, 1).date()
                # inclusive end = last day of month
                from datetime import timedelta
                end = end - timedelta(days=1)
                return start, end, period
        except Exception:
            pass
    elif period == "yearly":
        try:
            y = int(year) if year else (date_from.year if date_from else None)
            if y:
                return datetime(y, 1, 1).date(), datetime(y, 12, 31).date(), period
        except Exception:
            pass
    elif period == "custom":
        return date_from, date_to, period

    # Backward-compatible fallback: explicit date range/month/year fields
    if date_from or date_to:
        return date_from, date_to, "custom" if (date_from and date_to) else period
    try:
        if year and month:
            y = int(year); m = int(month)
            start = datetime(y, m, 1).date()
            from datetime import timedelta
            if m == 12:
                end = (datetime(y + 1, 1, 1).date() - timedelta(days=1))
            else:
                end = (datetime(y, m + 1, 1).date() - timedelta(days=1))
            return start, end, "monthly"
        if year:
            y = int(year)
            return datetime(y, 1, 1).date(), datetime(y, 12, 31).date(), "yearly"
    except Exception:
        pass
    return None, None, period or ""


def apply_trip_filters(qs, filters=None):
    filters = filters or {}
    company = (filters.get("company") or "").strip()
    driver = filters.get("driver") or ""
    vehicle = filters.get("vehicle") or ""

    date_from, date_to, _period = resolve_date_range(filters)
    if company:
        # company may be id (legacy) or name text
        if str(company).isdigit():
            # legacy: no longer supported, ignore numeric id filter
            pass
        else:
            qs = qs.filter(company_name__icontains=company)
    if driver:
        qs = qs.filter(driver_id=driver)
    if vehicle:
        qs = qs.filter(vehicle_id=vehicle)
    if date_from:
        qs = qs.filter(trip_date__gte=date_from)
    if date_to:
        qs = qs.filter(trip_date__lte=date_to)
    return qs


def _filtered_trip_qs(filters=None):
    from trips.models import TripSheet
    qs = TripSheet.objects.all()
    return apply_trip_filters(qs, filters)


def get_trip_financial_metrics(filters=None):
    """Aggregate trip financials from actual TripSheet records (no duplicate joins)."""
    from trips.models import TripSheet, DriverAdvance, DriverPayment
    from fleet.models import Vehicle

    qs = _filtered_trip_qs(filters)
    agg = qs.aggregate(
        total_trips=Count("id", distinct=True),
        total_revenue=Coalesce(Sum("total_revenue"), Decimal("0.00")),
        total_expenses=Coalesce(Sum("total_cost"), Decimal("0.00")),
        total_profit=Coalesce(Sum("profit"), Decimal("0.00")),
        total_diesel=Coalesce(Sum("diesel_cost"), Decimal("0.00")),
        total_distance=Coalesce(Sum("distance_km"), Decimal("0.00")),
        total_bata_earned=Coalesce(Sum("driver_bata"), Decimal("0.00")),
        total_vehicles_used=Count("vehicle", distinct=True),
    )

    driver_ids = list(qs.values_list("driver_id", flat=True).distinct())
    pending_bata = Decimal("0.00")
    if driver_ids:
        bata_map = {
            row["driver_id"]: (row["total"] or Decimal("0.00"))
            for row in TripSheet.objects.filter(driver_id__in=driver_ids)
            .values("driver_id")
            .annotate(total=Coalesce(Sum("driver_bata"), Decimal("0.00")))
        }
        adv_map = {
            row["driver_id"]: (row["total"] or Decimal("0.00"))
            for row in DriverAdvance.objects.filter(driver_id__in=driver_ids)
            .values("driver_id")
            .annotate(total=Coalesce(Sum("amount"), Decimal("0.00")))
        }
        pay_map = {
            row["driver_id"]: (row["total"] or Decimal("0.00"))
            for row in DriverPayment.objects.filter(driver_id__in=driver_ids)
            .values("driver_id")
            .annotate(total=Coalesce(Sum("amount"), Decimal("0.00")))
        }
        for did in driver_ids:
            bata = bata_map.get(did, Decimal("0.00"))
            paid = adv_map.get(did, Decimal("0.00")) + pay_map.get(did, Decimal("0.00"))
            pending_bata += max(bata - paid, Decimal("0.00"))

    agg["pending_driver_bata"] = pending_bata
    agg["financial_available"] = qs.exists()
    agg["total_vehicles"] = Vehicle.objects.count()
    agg["active_vehicles"] = agg["total_vehicles_used"] or 0
    return agg


def get_trip_chart_data(filters=None):
    """Monthly (or period-appropriate) revenue/expenses/profit series for Chart.js."""
    qs = _filtered_trip_qs(filters)
    date_from, date_to, period = resolve_date_range(filters or {})
    # choose truncation
    if period == "daily":
        trunc = TruncDay("trip_date")
        fmt = "%d %b %Y"
    elif period == "yearly":
        trunc = TruncMonth("trip_date")
        fmt = "%b %Y"
    else:
        trunc = TruncMonth("trip_date")
        fmt = "%b %Y"

    series = (
        qs.annotate(bucket=trunc)
        .values("bucket")
        .annotate(
            revenue=Coalesce(Sum("total_revenue"), Decimal("0.00")),
            expenses=Coalesce(Sum("total_cost"), Decimal("0.00")),
            profit=Coalesce(Sum("profit"), Decimal("0.00")),
        )
        .order_by("bucket")
    )
    labels, revenue, expenses, profit = [], [], [], []
    for row in series:
        b = row["bucket"]
        try:
            labels.append(b.strftime(fmt) if b else "")
        except Exception:
            labels.append(str(b) if b else "")
        revenue.append(float(row["revenue"] or 0))
        expenses.append(float(row["expenses"] or 0))
        profit.append(float(row["profit"] or 0))
    return {"labels": labels, "revenue": revenue, "expenses": expenses, "profit": profit}


def get_vehicle_distribution_data(filters=None):
    """Vehicle-wise revenue/expense/profit distribution for donut charts."""
    qs = _filtered_trip_qs(filters)
    rows = (
        qs.values("vehicle_id", "vehicle__vehicle_number")
        .annotate(
            revenue=Coalesce(Sum("total_revenue"), Decimal("0.00")),
            expenses=Coalesce(Sum("total_cost"), Decimal("0.00")),
            profit=Coalesce(Sum("profit"), Decimal("0.00")),
        )
        .order_by("vehicle__vehicle_number")
    )
    data = []
    for r in rows:
        rev = float(r["revenue"] or 0)
        exp = float(r["expenses"] or 0)
        prof = float(r["profit"] or 0)
        data.append({
            "vehicle_id": r["vehicle_id"],
            "vehicle_number": r["vehicle__vehicle_number"] or "Unknown",
            "revenue": rev,
            "expenses": exp,
            "profit": prof,
        })

    def pct(values):
        total = sum(values)
        if not total:
            return [0 for _ in values]
        return [(v / total * 100.0) if total else 0 for v in values]

    labels = [d["vehicle_number"] for d in data]
    revenues = [d["revenue"] for d in data]
    expenses = [d["expenses"] for d in data]
    profits_raw = [d["profit"] for d in data]
    # For profit donut, show positive contribution share; keep raw for display
    profits_for_chart = [max(p, 0.0) for p in profits_raw]
    return {
        "labels": labels,
        "revenue": revenues,
        "expenses": expenses,
        "profit": profits_raw,
        "profit_chart": profits_for_chart,
        "revenue_pct": pct(revenues),
        "expenses_pct": pct(expenses),
        "profit_pct": pct(profits_for_chart),
        "rows": data,
    }


def get_top_and_loss_trips(filters=None, limit=5):
    qs = _filtered_trip_qs(filters).select_related("driver", "vehicle")
    top = qs.order_by("-profit")[:limit]
    loss = qs.filter(profit__lt=0).order_by("profit")[:limit]
    return {"top_profit_trips": list(top), "loss_trips": list(loss)}


def get_operational_metrics(filters=None):
    """Return operational and financial metrics available in the current schema."""
    from fleet.models import Driver, Vehicle

    total_trucks = Vehicle.objects.count()
    total_drivers = Driver.objects.count()
    financial = get_trip_financial_metrics(filters)
    return {
        "total_trucks": total_trucks,
        "total_drivers": total_drivers,
        "total_revenue": financial["total_revenue"],
        "total_expenses": financial["total_expenses"],
        "total_profit": financial["total_profit"],
        "total_trips": financial["total_trips"],
        "total_diesel_expense": financial["total_diesel"],
        "total_distance": financial.get("total_distance", Decimal("0.00")),
        "pending_driver_bata": financial["pending_driver_bata"],
        "trucks_available": True,
        "drivers_available": True,
        "financial_available": financial["financial_available"],
        "audit_logs_available": False,
        "audit_logs": [],
    }


def get_vehicle_financial_summary(vehicle, filters=None):
    """Financial summary for a single vehicle (all figures from its trip records)."""
    from trips.models import TripSheet

    qs = TripSheet.objects.filter(vehicle=vehicle)
    qs = apply_trip_filters(qs, filters)
    agg = qs.aggregate(
        total_trips=Count("id", distinct=True),
        total_revenue=Coalesce(Sum("total_revenue"), Decimal("0.00")),
        total_expenses=Coalesce(Sum("total_cost"), Decimal("0.00")),
        net_profit=Coalesce(Sum("profit"), Decimal("0.00")),
        total_distance=Coalesce(Sum("distance_km"), Decimal("0.00")),
        diesel_expenses=Coalesce(Sum("diesel_cost"), Decimal("0.00")),
        toll_expenses=Coalesce(Sum("toll_cost"), Decimal("0.00")),
        loading_expenses=Coalesce(Sum("loading_cost"), Decimal("0.00")),
        unloading_expenses=Coalesce(Sum("unloading_cost"), Decimal("0.00")),
        driver_bata=Coalesce(Sum("driver_bata"), Decimal("0.00")),
        maintenance_expenses=Coalesce(Sum("maintenance_cost"), Decimal("0.00")),
        other_expenses=Coalesce(Sum("other_expenses"), Decimal("0.00")),
        load_commission=Coalesce(Sum("load_commission"), Decimal("0.00")),
    )
    # Keep expense breakdown explicit; include commission in total_expenses via stored total_cost
    trips = list(
        qs.select_related("driver").order_by("-trip_date", "-id")
    )
    return {
        "vehicle": vehicle,
        "totals": agg,
        "trips": trips,
        "financial_available": qs.exists(),
    }
