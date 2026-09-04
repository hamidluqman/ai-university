from django import forms
from accounts.models import User
from .models import Institution, AcademicSession, TeacherAssignment


class InstitutionForm(forms.ModelForm):
    class Meta:
        model = Institution
        fields = ["name", "code", "address", "contact_email", "contact_phone", "logo", "is_active"]


class AcademicSessionForm(forms.ModelForm):
    class Meta:
        model = AcademicSession
        fields = ["institution", "name", "start_date", "end_date", "is_active"]


class TeacherAssignmentForm(forms.ModelForm):
    class Meta:
        model = TeacherAssignment
        fields = ["teacher_profile", "institution", "board_subject", "competitive_exam", "academic_session"]