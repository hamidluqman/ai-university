from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.urls import reverse
from django.utils.html import format_html, mark_safe
from .models import User, InstitutionAdminProfile, TeacherProfile, StudentProfile


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    change_list_template = "admin/accounts/user/change_list.html"

    fieldsets = UserAdmin.fieldsets + (
        ("AI University Role Info", {"fields": ("role", "phone", "is_active_user")}),
    )
    list_display = ("username", "email", "role", "is_active_user", "is_staff", "quick_add_links")
    list_filter = ("role", "is_active_user", "is_staff")

    def quick_add_links(self, obj):
        return mark_safe('<a class="button" href="/accounts/hub/">Open Management Hub</a>')
    quick_add_links.short_description = "Onboarding Hub"


@admin.register(InstitutionAdminProfile)
class InstitutionAdminProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "institution", "designation", "created_at")
    search_fields = ("user__username", "institution__name", "designation")


@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "employee_id", "institution", "is_active")
    search_fields = ("user__username", "employee_id", "institution__name")
    list_filter = ("is_active", "institution")


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "student_type", "institution", "roll_number", "is_active")
    search_fields = ("user__username", "roll_number", "institution__name")
    list_filter = ("student_type", "is_active", "institution")