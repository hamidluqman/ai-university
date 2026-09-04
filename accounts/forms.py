from django import forms
from django.db import transaction
from .models import User, TeacherProfile, StudentProfile, InstitutionAdminProfile
from institutions.models import Institution
from question_bank.models import BoardClass, BoardSubject, CompetitiveExam


class CustomUserCreationBaseForm(forms.ModelForm):
    full_name = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter full name'})
    )
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter username'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'name@example.com'})
    )
    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+1234567890'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}),
        required=True
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm Password'}),
        required=True
    )

    class Meta:
        model = User
        fields = ['full_name', 'username', 'email', 'phone', 'password']

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match.")
        return cleaned_data

    def save_user_with_role(self, role):
        user = super().save(commit=False)
        user.role = role
        user.set_password(self.cleaned_data["password"])
        user.save()
        return user


# ==========================================================
# INSTITUTION + ADMIN ACCOUNT CREATION FORM
# ==========================================================

class InstitutionWithAdminCreationForm(CustomUserCreationBaseForm):
    admin_username = forms.CharField(
        label="Admin Username", 
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Admin username'})
    )
    institution_name = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Oxford Public School'})
    )
    institution_code = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. INST-001'})
    )
    contact_email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'info@institution.com'})
    )
    contact_phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+1234567890'})
    )
    address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Full address...'})
    )

    def save(self, commit=True):
        with transaction.atomic():
            institution = Institution.objects.create(
                name=self.cleaned_data['institution_name'],
                code=self.cleaned_data['institution_code'],
                contact_email=self.cleaned_data['contact_email'],
                contact_phone=self.cleaned_data.get('contact_phone', ''),
                address=self.cleaned_data.get('address', '')
            )
            
            admin_user = User.objects.create_user(
                username=self.cleaned_data['admin_username'],
                email=self.cleaned_data['email'],
                password=self.cleaned_data['password'],
                full_name=self.cleaned_data['full_name'],
                phone=self.cleaned_data.get('phone', ''),
                role="institution_admin"
            )
            
            InstitutionAdminProfile.objects.create(
                user=admin_user,
                institution=institution,
                designation="Primary Admin"
            )
            return institution, admin_user


class ContentTeamCreationForm(CustomUserCreationBaseForm):
    def save(self, commit=True):
        return self.save_user_with_role(role="content_team")


class TeacherCreationForm(CustomUserCreationBaseForm):
    institution = forms.ModelChoiceField(
        queryset=Institution.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Assigned Institution"
    )
    employee_id = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. EMP-1002'})
    )
    assigned_classes = forms.ModelMultipleChoiceField(
        queryset=BoardClass.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'style': 'height: 120px;'}),
        label="Assigned Classes (Hold Ctrl to select multiple)"
    )
    assigned_subjects = forms.ModelMultipleChoiceField(
        queryset=BoardSubject.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'style': 'height: 150px;'}),
        label="Assigned Subjects (Hold Ctrl to select multiple)"
    )

    def __init__(self, *args, **kwargs):
        self.creator_institution = kwargs.pop('institution', None)
        super().__init__(*args, **kwargs)
        if self.creator_institution:
            self.fields['institution'].initial = self.creator_institution
            self.fields['institution'].widget = forms.HiddenInput()

    def save(self, commit=True):
        user = self.save_user_with_role(role="teacher")
        target_institution = self.creator_institution or self.cleaned_data.get('institution')
        
        teacher_profile = TeacherProfile.objects.create(
            user=user,
            institution=target_institution,
            employee_id=self.cleaned_data['employee_id']
        )
        if self.cleaned_data.get('assigned_classes'):
            teacher_profile.assigned_classes.set(self.cleaned_data['assigned_classes'])
        if self.cleaned_data.get('assigned_subjects'):
            teacher_profile.assigned_subjects.set(self.cleaned_data['assigned_subjects'])
            
        return user


class StudentCreationForm(CustomUserCreationBaseForm):
    student_type = forms.ChoiceField(
        choices=StudentProfile.STUDENT_TYPES,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_student_type'})
    )
    institution = forms.ModelChoiceField(
        queryset=Institution.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_institution'}),
        label="Institution (Required for Institutional Students)"
    )
    roll_number = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'id_roll_number', 'placeholder': 'e.g. ROLL-2026-01'})
    )

    assessment_flow = forms.ChoiceField(
        choices=StudentProfile.ASSESSMENT_FLOWS,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_assessment_flow'})
    )
    assigned_classes = forms.ModelMultipleChoiceField(
        queryset=BoardClass.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'id': 'id_assigned_classes', 'style': 'height: 110px;'}),
        label="Board Classes (Hold Ctrl to select multiple)"
    )
    assigned_subjects = forms.ModelMultipleChoiceField(
        queryset=BoardSubject.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'id': 'id_assigned_subjects', 'style': 'height: 130px;'}),
        label="Board Subjects (Hold Ctrl to select multiple)"
    )
    competitive_exams = forms.ModelMultipleChoiceField(
        queryset=CompetitiveExam.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'id': 'id_competitive_exams', 'style': 'height: 120px;'}),
        label="Competitive Exams (Hold Ctrl to select multiple)"
    )

    def __init__(self, *args, **kwargs):
        self.creator_institution = kwargs.pop('institution', None)
        super().__init__(*args, **kwargs)
        if self.creator_institution:
            self.fields['student_type'].initial = 'institutional'
            self.fields['student_type'].widget = forms.HiddenInput()
            self.fields['institution'].initial = self.creator_institution
            self.fields['institution'].widget = forms.HiddenInput()

    def save(self, commit=True):
        user = self.save_user_with_role(role="student")
        student_type = self.cleaned_data.get('student_type') or ('institutional' if self.creator_institution else 'independent')
        target_institution = self.creator_institution or (self.cleaned_data.get('institution') if student_type == 'institutional' else None)

        student_profile = StudentProfile.objects.create(
            user=user,
            student_type=student_type,
            institution=target_institution,
            roll_number=self.cleaned_data.get('roll_number', ''),
            assessment_flow=self.cleaned_data.get('assessment_flow')
        )
        if self.cleaned_data.get('assigned_classes'):
            student_profile.assigned_classes.set(self.cleaned_data['assigned_classes'])
        if self.cleaned_data.get('assigned_subjects'):
            student_profile.assigned_subjects.set(self.cleaned_data['assigned_subjects'])
        if self.cleaned_data.get('competitive_exams'):
            student_profile.competitive_exams.set(self.cleaned_data['competitive_exams'])

        return user