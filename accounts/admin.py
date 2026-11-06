from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from .models import Staff


class StaffInline(admin.StackedInline):
    model = Staff
    extra = 0


class CustomUserAdmin(UserAdmin):
    inlines = [StaffInline]


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ("display_name", "user", "phone_number", "created_at")
    search_fields = ("display_name", "user__username", "phone_number")


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
