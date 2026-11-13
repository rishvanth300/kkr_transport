from decimal import Decimal
from io import BytesIO

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum, Count
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from dashboard.views import dashboard_access_required
from fleet.models import Vehicle, Driver

from .forms import TruckSelectionForm, TripSheetForm, DriverAdvanceForm, DriverPaymentForm
from .models import TripSheet, DriverAdvance, DriverBataAllocation, DriverPayment
from .services import (
    save_trip_sheet, trip_queryset_for_request,
    get_driver_financial_summary, get_driver_financial_summaries, get_driver_outstanding_bata,
    create_advance_and_allocate,
)


def _base(request, active_nav="trips"):
    return {
        "is_super_admin": getattr(request, "is_super_admin", False),
        "staff_profile": getattr(request, "staff_profile", None),
        "active_nav": active_nav,
    }


def _trip_filters(request, qs):
    from django.db.models import Q

    q = (request.GET.get("q") or "").strip()
    company = (request.GET.get("company") or "").strip()
    driver = request.GET.get("driver") or ""
    vehicle = request.GET.get("vehicle") or ""
    load_type = (request.GET.get("load_type") or "").strip()
    date_from = request.GET.get("date_from") or ""
    date_to = request.GET.get("date_to") or ""
    month = request.GET.get("month") or ""
    year = request.GET.get("year") or ""

    if q:
        qs = qs.filter(
            Q(driver__driver_name__icontains=q)
            | Q(vehicle__vehicle_number__icontains=q)
            | Q(company_name__icontains=q)
            | Q(from_location__icontains=q)
            | Q(to_location__icontains=q)
            | Q(load_type__icontains=q)
            | Q(id__icontains=q)
        )
    if company:
        qs = qs.filter(company_name__icontains=company)
    if driver:
        qs = qs.filter(driver_id=driver)
    if vehicle:
        qs = qs.filter(vehicle_id=vehicle)
    if load_type:
        qs = qs.filter(load_type__icontains=load_type)
    if date_from:
        qs = qs.filter(trip_date__gte=date_from)
    if date_to:
        qs = qs.filter(trip_date__lte=date_to)
    if month:
        qs = qs.filter(trip_date__month=month)
    if year:
        qs = qs.filter(trip_date__year=year)
    return qs


def _trip_summary(qs):
    agg = qs.aggregate(
        total_trips=Count("id"),
        total_revenue=Coalesce(Sum("total_revenue"), Decimal("0.00")),
        total_cost=Coalesce(Sum("total_cost"), Decimal("0.00")),
        total_profit=Coalesce(Sum("profit"), Decimal("0.00")),
        total_diesel=Coalesce(Sum("diesel_cost"), Decimal("0.00")),
        total_bata=Coalesce(Sum("driver_bata"), Decimal("0.00")),
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
    return agg


def _company_options():
    return (
        TripSheet.objects.exclude(company_name="")
        .order_by("company_name")
        .values_list("company_name", flat=True)
        .distinct()
    )


def _load_type_options():
    return (
        TripSheet.objects.exclude(load_type="")
        .order_by("load_type")
        .values_list("load_type", flat=True)
        .distinct()
    )


@dashboard_access_required
def trip_dashboard(request):
    qs = _trip_filters(request, trip_queryset_for_request(request))
    summary = _trip_summary(qs)
    recent_trips = qs.order_by("-trip_date", "-id")[:10]
    ctx = _base(request, "trips")
    ctx.update({
        "summary": summary,
        "recent_trips": recent_trips,
        "companies": _company_options(),
        "drivers": Driver.objects.order_by("driver_name"),
        "vehicles": Vehicle.objects.order_by("vehicle_number"),
        "load_types": _load_type_options(),
        "filters": request.GET,
    })
    return render(request, "trips/trip_dashboard.html", ctx)


@dashboard_access_required
def trip_list(request):
    qs = _trip_filters(request, trip_queryset_for_request(request)).order_by("-trip_date", "-id")
    summary = _trip_summary(qs)
    ctx = _base(request, "trips")
    ctx.update({
        "trips": qs,
        "summary": summary,
        "companies": _company_options(),
        "drivers": Driver.objects.order_by("driver_name"),
        "vehicles": Vehicle.objects.order_by("vehicle_number"),
        "load_types": _load_type_options(),
        "filters": request.GET,
    })
    return render(request, "trips/trip_list.html", ctx)


@dashboard_access_required
def select_truck(request):
    """Step 1 (truck-first): user must select an existing vehicle before entering trip details."""
    vehicles = Vehicle.objects.order_by("vehicle_number")
    if request.method == "POST":
        form = TruckSelectionForm(request.POST)
        if form.is_valid():
            vehicle = form.cleaned_data["vehicle"]
            # store validated selection in session for normal workflow continuity
            request.session["trip_selected_vehicle_id"] = vehicle.id
            request.session["trip_selected_vehicle_at"] = timezone.now().isoformat()
            return redirect(f"{reverse('trips:create')}?vehicle={vehicle.id}")
    else:
        form = TruckSelectionForm()
    ctx = _base(request, "trips")
    ctx.update({
        "form": form,
        "vehicles": vehicles,
        "page_title": "Select Truck",
    })
    return render(request, "trips/select_truck.html", ctx)


def _get_selected_vehicle_for_create(request):
    """Resolve and validate selected vehicle from session/query; enforce truck-first workflow."""
    vid = request.GET.get("vehicle") or request.session.get("trip_selected_vehicle_id")
    if not vid:
        return None, "missing"
    try:
        vehicle = Vehicle.objects.get(pk=int(vid))
    except (Vehicle.DoesNotExist, ValueError, TypeError):
        request.session.pop("trip_selected_vehicle_id", None)
        return None, "invalid"
    # keep session in sync with explicit selection
    request.session["trip_selected_vehicle_id"] = vehicle.id
    return vehicle, "ok"


@dashboard_access_required
@require_http_methods(["GET", "POST"])
def trip_sheet_create(request):
    vehicle, state = _get_selected_vehicle_for_create(request)

    if request.method == "POST":
        post = request.POST.copy()
        # Prefer user-selected vehicle in form; fall back to truck-first selection
        if not post.get("vehicle") and vehicle is not None:
            post["vehicle"] = str(vehicle.id)
        selected = Vehicle.objects.filter(pk=post.get("vehicle")).first() or vehicle
        form = TripSheetForm(post, selected_vehicle=selected)
        if form.is_valid():
            trip = form.save(commit=False)
            trip.vehicle = form.cleaned_data.get("vehicle") or selected
            trip.created_by = request.user
            try:
                with transaction.atomic():
                    save_trip_sheet(trip)
            except ValidationError as e:
                if hasattr(e, "message_dict"):
                    for field, errs in e.message_dict.items():
                        for err in errs:
                            if field in form.fields:
                                form.add_error(field, err)
                            else:
                                form.add_error(None, err)
                else:
                    form.add_error(None, str(e))
            except Exception as e:
                form.add_error(None, f"Unable to save trip sheet: {e}")
            else:
                # clear workflow marker after successful save
                request.session.pop("trip_selected_vehicle_id", None)
                request.session.pop("trip_selected_vehicle_at", None)
                messages.success(request, "Trip sheet saved successfully.")
                return redirect("trips:detail", pk=trip.pk)
    else:
        form = TripSheetForm(selected_vehicle=vehicle)

    ctx = _base(request, "trips")
    ctx.update({
        "form": form,
        "selected_vehicle": vehicle,
        "is_edit": False,
        "page_title": "Add Trip Sheet",
    })
    return render(request, "trips/trip_sheet_form.html", ctx)


@dashboard_access_required
def trip_detail(request, pk):
    trip = get_object_or_404(trip_queryset_for_request(request), pk=pk)
    allocations = trip.bata_allocations.select_related("advance", "allocated_by").order_by("-allocated_at")
    # Driver settlement context for this trip
    bata_earned = trip.driver_bata or Decimal("0.00")
    advance_paid = trip.bata_allocated_amount  # allocated/paid against this trip's bata
    remaining_bata = trip.bata_outstanding
    # Previous outstanding = driver's total outstanding across trips excluding this trip's remaining bata
    driver_total_outstanding = get_driver_outstanding_bata(trip.driver)
    previous_outstanding = driver_total_outstanding - remaining_bata
    if previous_outstanding < 0:
        previous_outstanding = Decimal("0.00")
    ctx = _base(request, "trips")
    ctx.update({
        "trip": trip,
        "allocations": allocations,
        "page_title": f"Trip #{trip.id}",
        "settlement": {
            "bata_earned": bata_earned,
            "previous_outstanding": previous_outstanding,
            "advance_paid": advance_paid,
            "remaining_bata": remaining_bata,
        },
    })
    return render(request, "trips/trip_detail.html", ctx)


@dashboard_access_required
@require_http_methods(["GET", "POST"])
def trip_edit(request, pk):
    trip = get_object_or_404(trip_queryset_for_request(request), pk=pk)
    if request.method == "POST":
        post = request.POST.copy()
        if not post.get("vehicle"):
            post["vehicle"] = str(trip.vehicle_id)
        form = TripSheetForm(post, instance=trip, selected_vehicle=trip.vehicle)
        if form.is_valid():
            updated = form.save(commit=False)
            updated.vehicle = form.cleaned_data.get("vehicle") or trip.vehicle
            try:
                with transaction.atomic():
                    save_trip_sheet(updated)
            except ValidationError as e:
                if hasattr(e, "message_dict"):
                    for field, errs in e.message_dict.items():
                        for err in errs:
                            if field in form.fields:
                                form.add_error(field, err)
                            else:
                                form.add_error(None, err)
                else:
                    form.add_error(None, str(e))
            except Exception as e:
                form.add_error(None, f"Unable to update trip sheet: {e}")
            else:
                messages.success(request, "Trip sheet updated successfully.")
                return redirect("trips:detail", pk=trip.pk)
    else:
        form = TripSheetForm(instance=trip, selected_vehicle=trip.vehicle)
    ctx = _base(request, "trips")
    ctx.update({
        "form": form,
        "trip": trip,
        "selected_vehicle": trip.vehicle,
        "is_edit": True,
        "page_title": f"Edit Trip #{trip.id}",
    })
    return render(request, "trips/trip_sheet_form.html", ctx)


@dashboard_access_required
@require_POST
def trip_delete(request, pk):
    trip = get_object_or_404(trip_queryset_for_request(request), pk=pk)
    # Financial integrity: block delete if settlements/allocations exist; superadmin can proceed only if safe.
    if trip.bata_allocations.exists():
        messages.error(request, "Cannot delete trip with driver bata allocations. Reverse settlements first.")
        return redirect("trips:detail", pk=pk)
    if not request.is_super_admin:
        messages.error(request, "Only Super Admin can delete trip sheets.")
        return redirect("trips:detail", pk=pk)
    trip.delete()
    messages.success(request, "Trip sheet deleted.")
    return redirect("trips:list")


@dashboard_access_required
def trip_print(request, pk):
    trip = get_object_or_404(trip_queryset_for_request(request), pk=pk)
    bata_earned = trip.driver_bata or Decimal("0.00")
    advance_paid = trip.bata_allocated_amount
    remaining_bata = trip.bata_outstanding
    driver_total_outstanding = get_driver_outstanding_bata(trip.driver)
    previous_outstanding = driver_total_outstanding - remaining_bata
    if previous_outstanding < 0:
        previous_outstanding = Decimal("0.00")
    ctx = _base(request, "trips")
    ctx.update({
        "trip": trip,
        "allocations": trip.bata_allocations.select_related("advance"),
        "settlement": {
            "bata_earned": bata_earned,
            "previous_outstanding": previous_outstanding,
            "advance_paid": advance_paid,
            "remaining_bata": remaining_bata,
        },
    })
    return render(request, "trips/trip_sheet_print.html", ctx)


@dashboard_access_required
def driver_finance(request):
    drivers = list(Driver.objects.order_by("driver_name"))
    summaries = get_driver_financial_summaries(drivers, include_details=False)
    ctx = _base(request, "trips")
    ctx.update({"summaries": summaries, "drivers": drivers, "page_title": "Driver Bata & Advances"})
    return render(request, "trips/driver_finance.html", ctx)


@dashboard_access_required
def driver_finance_detail(request, driver_id):
    driver = get_object_or_404(Driver, pk=driver_id)
    summary = get_driver_financial_summary(driver)
    ctx = _base(request, "trips")
    ctx.update({"summary": summary, "driver": driver, "page_title": f"Driver Finance - {driver.driver_name}"})
    return render(request, "trips/driver_finance_detail.html", ctx)


@dashboard_access_required
@require_http_methods(["GET", "POST"])
def advance_create(request):
    # Staff and Super Admin can record advances (audited). Kept within existing dashboard access.
    driver_id = request.GET.get("driver") or request.POST.get("driver")
    driver = Driver.objects.filter(pk=driver_id).first() if driver_id else None
    if request.method == "POST":
        form = DriverAdvanceForm(request.POST, driver=driver)
        if form.is_valid():
            allocs = []
            trip = form.cleaned_data.get("allocate_trip")
            amt = form.cleaned_data.get("allocate_amount")
            if trip and amt:
                allocs.append({"trip": trip, "amount": amt, "note": "Allocated at advance entry"})
            try:
                create_advance_and_allocate(
                    driver=form.cleaned_data["driver"],
                    amount=form.cleaned_data["amount"],
                    payment_date=form.cleaned_data["payment_date"],
                    payment_method=form.cleaned_data["payment_method"],
                    reference=form.cleaned_data.get("reference"),
                    description=form.cleaned_data.get("description"),
                    recorded_by=request.user,
                    allocations=allocs,
                )
            except ValidationError as e:
                if hasattr(e, "message_dict"):
                    for field, errs in e.message_dict.items():
                        target = field if field in form.fields else None
                        for err in errs:
                            form.add_error(target, err)
                else:
                    form.add_error(None, str(e))
            except Exception as e:
                form.add_error(None, f"Unable to record advance: {e}")
            else:
                messages.success(request, "Driver advance recorded successfully.")
                did = form.cleaned_data["driver"].id
                return redirect("trips:driver_finance_detail", driver_id=did)
    else:
        form = DriverAdvanceForm(driver=driver)
    ctx = _base(request, "trips")
    ctx.update({"form": form, "driver": driver, "page_title": "Record Driver Advance"})
    return render(request, "trips/advance_form.html", ctx)


@dashboard_access_required
@require_http_methods(["GET", "POST"])
def payment_create(request):
    driver_id = request.GET.get("driver") or request.POST.get("driver")
    driver = Driver.objects.filter(pk=driver_id).first() if driver_id else None
    if request.method == "POST":
        form = DriverPaymentForm(request.POST, driver=driver)
        if form.is_valid():
            try:
                payment = form.save(commit=False)
                payment.recorded_by = request.user
                payment.full_clean()
                payment.save()
            except ValidationError as e:
                if hasattr(e, "message_dict"):
                    for field, errs in e.message_dict.items():
                        target = field if field in form.fields else None
                        for err in errs:
                            form.add_error(target, err)
                else:
                    form.add_error(None, str(e))
            except Exception as e:
                form.add_error(None, f"Unable to record payment: {e}")
            else:
                messages.success(request, "Driver payment recorded successfully.")
                return redirect("trips:driver_finance_detail", driver_id=payment.driver_id)
    else:
        form = DriverPaymentForm(driver=driver)
    ctx = _base(request, "trips")
    ctx.update({"form": form, "driver": driver, "page_title": "Record Payment"})
    return render(request, "trips/payment_form.html", ctx)


@dashboard_access_required
def trip_export(request):
    """Download trip sheets as an Excel workbook, separated by truck (one sheet per truck)."""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
        from openpyxl.utils import get_column_letter
    except Exception:
        messages.error(request, "Excel export is unavailable because 'openpyxl' is not installed.")
        return redirect(request.GET.get("next") or "trips:list")

    qs = _trip_filters(request, trip_queryset_for_request(request)).select_related(
        "vehicle", "driver"
    ).order_by("vehicle__vehicle_number", "-trip_date", "-id")

    wb = Workbook()
    # remove default sheet, we'll add per-truck sheets
    wb.remove(wb.active)

    header_fill = PatternFill("solid", fgColor="0B5A8E")
    header_font = Font(color="FFFFFF", bold=True)
    truck_fill = PatternFill("solid", fgColor="E8F4FB")
    total_fill = PatternFill("solid", fgColor="FFF4CC")
    border = Border(
        left=Side(style="thin", color="D0D7DE"),
        right=Side(style="thin", color="D0D7DE"),
        top=Side(style="thin", color="D0D7DE"),
        bottom=Side(style="thin", color="D0D7DE"),
    )

    headers = [
        "Trip ID", "Trip Date", "Vehicle No", "Driver", "Company", "From", "To", "Load Type",
        "Starting KM", "Closing KM", "Distance (KM)",
        "Revenue", "Diesel Qty (L)", "Diesel Price/L", "Diesel Cost",
        "Loading Cost", "Unloading Cost", "Toll Cost", "Driver Bata %", "Driver Bata",
        "Load Commission", "Maintenance Cost", "Other Expenses", "Other Expense Note",
        "Total Cost", "Profit",
    ]

    trucks = {}
    for trip in qs:
        key = trip.vehicle_id
        trucks.setdefault(key, {"vehicle": trip.vehicle, "trips": []})["trips"].append(trip)

    if not trucks:
        ws = wb.create_sheet(title="Trip Sheets")
        ws.append(["No trip sheet records found for the selected filters."])
        ws["A1"].font = Font(bold=True)
    else:
        for data in trucks.values():
            vehicle = data["vehicle"]
            trips = data["trips"]
            raw_title = (vehicle.vehicle_number or f"Truck-{vehicle.id}")[:31]
            safe_title = "".join(c for c in raw_title if c not in '[]:*?/\\') or f"Truck-{vehicle.id}"
            # ensure unique sheet title
            title = safe_title
            suffix = 1
            while title in wb.sheetnames:
                suffix += 1
                title = f"{safe_title[:28]}-{suffix}"
            ws = wb.create_sheet(title=title)

            ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(headers))
            title_cell = ws.cell(row=1, column=1, value=f"Truck: {vehicle.vehicle_number}  |  Make/Model: {vehicle.vehicle_make} {vehicle.vehicle_model}  |  Trips: {len(trips)}")
            title_cell.font = Font(bold=True, size=12, color="0B5A8E")
            title_cell.fill = truck_fill
            title_cell.alignment = Alignment(horizontal="left", vertical="center")
            ws.row_dimensions[1].height = 22

            for col_idx, header in enumerate(headers, start=1):
                cell = ws.cell(row=2, column=col_idx, value=header)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                cell.border = border
            ws.row_dimensions[2].height = 28
            ws.freeze_panes = "A3"

            totals = {
                "distance": Decimal("0.00"), "revenue": Decimal("0.00"), "diesel_cost": Decimal("0.00"),
                "total_cost": Decimal("0.00"), "profit": Decimal("0.00"),
            }

            row_num = 3
            for t in trips:
                vals = [
                    t.id,
                    t.trip_date,
                    t.vehicle.vehicle_number,
                    getattr(t.driver, "driver_name", ""),
                    t.company_name,
                    t.from_location,
                    t.to_location,
                    t.load_type,
                    float(t.starting_km or 0),
                    float(t.closing_km or 0),
                    float(t.distance_km or 0),
                    float(t.total_revenue or 0),
                    float(t.diesel_quantity or 0),
                    float(t.diesel_price_per_litre or 0),
                    float(t.diesel_cost or 0),
                    float(t.loading_cost or 0),
                    float(t.unloading_cost or 0),
                    float(t.toll_cost or 0),
                    float(t.bata_percentage or 0),
                    float(t.driver_bata or 0),
                    float(t.load_commission or 0),
                    float(t.maintenance_cost or 0),
                    float(t.other_expenses or 0),
                    t.other_expense_note or "",
                    float(t.total_cost or 0),
                    float(t.profit or 0),
                ]
                for col_idx, value in enumerate(vals, start=1):
                    cell = ws.cell(row=row_num, column=col_idx, value=value)
                    cell.border = border
                    if col_idx in (2,):
                        cell.number_format = "yyyy-mm-dd"
                    elif col_idx >= 9 and col_idx != 24:
                        cell.number_format = "#,##0.00"
                totals["distance"] += (t.distance_km or Decimal("0.00"))
                totals["revenue"] += (t.total_revenue or Decimal("0.00"))
                totals["diesel_cost"] += (t.diesel_cost or Decimal("0.00"))
                totals["total_cost"] += (t.total_cost or Decimal("0.00"))
                totals["profit"] += (t.profit or Decimal("0.00"))
                row_num += 1

            # Totals row for easy identification
            ws.cell(row=row_num, column=1, value="TOTALS").font = Font(bold=True)
            for col_idx in range(1, len(headers) + 1):
                c = ws.cell(row=row_num, column=col_idx)
                c.fill = total_fill
                c.border = border
                c.font = Font(bold=True)
            ws.cell(row=row_num, column=11, value=float(totals["distance"])).number_format = "#,##0.00"
            ws.cell(row=row_num, column=12, value=float(totals["revenue"])).number_format = "#,##0.00"
            ws.cell(row=row_num, column=15, value=float(totals["diesel_cost"])).number_format = "#,##0.00"
            ws.cell(row=row_num, column=25, value=float(totals["total_cost"])).number_format = "#,##0.00"
            profit_cell = ws.cell(row=row_num, column=26, value=float(totals["profit"]))
            profit_cell.number_format = "#,##0.00"
            profit_cell.font = Font(bold=True, color="B42318" if totals["profit"] < 0 else "078A72")

            widths = [8, 12, 14, 16, 16, 14, 14, 12, 11, 11, 12, 12, 12, 12, 12, 12, 12, 12, 10, 12, 12, 13, 13, 22, 12, 12]
            for i, w in enumerate(widths, start=1):
                ws.column_dimensions[get_column_letter(i)].width = w
            ws.auto_filter.ref = f"A2:{get_column_letter(len(headers))}{max(row_num - 1, 2)}"

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    response = HttpResponse(
        output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    filename = f"trip_sheets_by_truck_{timezone.localdate().isoformat()}.xlsx"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
