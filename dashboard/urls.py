from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    path("super-admin/", views.super_admin, name="super_admin"),
    path("super-admin/staff/new/", views.create_staff, name="create_staff"),
    path(
        "super-admin/staff/<int:staff_id>/toggle-status/",
        views.toggle_staff_status,
        name="toggle_staff_status",
    ),
    path(
        "super-admin/staff/<int:staff_id>/",
        views.staff_detail,
        name="staff_detail",
    ),
    path(
        "super-admin/staff/<int:staff_id>/edit/",
        views.edit_staff,
        name="edit_staff",
    ),
    path(
        "super-admin/staff/<int:staff_id>/reset-password/",
        views.reset_staff_password,
        name="reset_staff_password",
    ),
]
