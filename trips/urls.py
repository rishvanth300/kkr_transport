"""Trips URLs — Trip Sheet module (navigation ready)."""

from django.urls import path

from . import views

app_name = "trips"

urlpatterns = [
    path("add/", views.trip_sheet_add, name="add"),
]
