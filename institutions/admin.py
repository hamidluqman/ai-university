from django.contrib import admin
from .models import Institution, AcademicSession, TeacherAssignment
from .forms import InstitutionForm, AcademicSessionForm, TeacherAssignmentForm


@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    form = InstitutionForm
    list_display = ("name", "code", "contact_email", "contact_phone", "is_active", "created_at")
    search_fields = ("name", "code", "contact_email")
    list_filter = ("is_active",)


@admin.register(AcademicSession)
class AcademicSessionAdmin(admin.ModelAdmin):
    form = AcademicSessionForm
    list_display = ("name", "institution", "start_date", "end_date", "is_active")
    search_fields = ("name", "institution__name", "institution__code")
    list_filter = ("is_active", "institution")


@admin.register(TeacherAssignment)
class TeacherAssignmentAdmin(admin.ModelAdmin):
    form = TeacherAssignmentForm
    list_display = ("teacher_profile", "institution", "board_subject", "competitive_exam", "academic_session")
    search_fields = ("teacher_profile__user__username", "institution__name")
    list_filter = ("institution", "academic_session")