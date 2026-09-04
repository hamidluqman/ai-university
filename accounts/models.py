from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    ROLE_CHOICES = (
        ('superadmin', 'Superadmin'),
        ('institution_admin', 'Institution Admin'),
        ('teacher', 'Teacher'),
        ('student', 'Student'),
        ('content_team', 'Content Team'),
    )
    full_name = models.CharField(max_length=255, blank=True, default='')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    phone = models.CharField(max_length=20, blank=True, null=True)
    is_active_user = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.full_name or self.username} ({self.get_role_display()})"


class InstitutionAdminProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='institution_admin_profile')
    institution = models.ForeignKey('institutions.Institution', on_delete=models.CASCADE)
    designation = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class TeacherProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='teacher_profile')
    institution = models.ForeignKey('institutions.Institution', on_delete=models.CASCADE)
    employee_id = models.CharField(max_length=50)
    assigned_classes = models.ManyToManyField('question_bank.BoardClass', blank=True)
    assigned_subjects = models.ManyToManyField('question_bank.BoardSubject', blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.full_name or self.user.username} - {self.institution.name}"


class StudentProfile(models.Model):
    STUDENT_TYPES = (
        ('institutional', 'Institutional'),
        ('independent', 'Independent'),
    )
    ASSESSMENT_FLOWS = (
        ('board', 'Board Exam Only'),
        ('competitive', 'Competitive Exam Only'),
        ('both', 'Both (Board & Competitive)'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    student_type = models.CharField(max_length=20, choices=STUDENT_TYPES, default='independent')
    institution = models.ForeignKey('institutions.Institution', on_delete=models.CASCADE, blank=True, null=True)
    roll_number = models.CharField(max_length=50, blank=True, null=True)

    # Academic Alignment (Multi-assignment support)
    assessment_flow = models.CharField(max_length=20, choices=ASSESSMENT_FLOWS, default='board')
    assigned_classes = models.ManyToManyField('question_bank.BoardClass', blank=True)
    assigned_subjects = models.ManyToManyField('question_bank.BoardSubject', blank=True)
    competitive_exams = models.ManyToManyField('question_bank.CompetitiveExam', blank=True)

    is_active = models.BooleanField(default=True)

    def __str__(self):
        type_label = self.get_student_type_display()
        name = self.user.full_name or self.user.username
        return f"{name} ({type_label} Student)"