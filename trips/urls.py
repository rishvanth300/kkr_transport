"""Trips URLs - Trip Sheet module with truck-first workflow."""

from django.urls import path

from . import views

app_name = "trips"

urlpatterns = [
    path("", views.trip_dashboard, name="dashboard"),
    path("list/", views.trip_list, name="list"),
    path("add/", views.select_truck, name="add"),  # truck-first entry (preserves existing nav target)
    path("add/select-truck/", views.select_truck, name="select_truck"),
    path("add/form/", views.trip_sheet_create, name="create"),
    path("<int:pk>/", views.trip_detail, name="detail"),
    path("<int:pk>/edit/", views.trip_edit, name="edit"),
    path("<int:pk>/delete/", views.trip_delete, name="delete"),
    path("<int:pk>/print/", views.trip_print, name="print"),
    path("export/", views.trip_export, name="export"),
    path("driver-finance/", views.driver_finance, name="driver_finance"),
    path("driver-finance/<int:driver_id>/", views.driver_finance_detail, name="driver_finance_detail"),
    path("advances/add/", views.advance_create, name="advance_create"),
    path("payments/add/", views.payment_create, name="payment_create"),
]
