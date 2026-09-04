from django.db import models


# ==========================================================
# INSTITUTION MODEL
# ==========================================================

class Institution(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    address = models.TextField(blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    logo = models.ImageField(upload_to="institution_logos/", blank=True, null=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"


# ==========================================================
# ACADEMIC SESSION / BATCH MODEL
# ==========================================================

class AcademicSession(models.Model):
    institution = models.ForeignKey(
        Institution,
        on_delete=models.CASCADE,
        related_name="academic_sessions"
    )
    name = models.CharField(max_length=100)  # e.g., "Session 2025-2026", "Batch A"
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-start_date", "name"]

    def __str__(self):
        return f"{self.institution.code} - {self.name}"


# ==========================================================
# TEACHER SUBJECT ASSIGNMENT MODEL
# ==========================================================

class TeacherAssignment(models.Model):
    teacher_profile = models.ForeignKey(
        "accounts.TeacherProfile",
        on_delete=models.CASCADE,
        related_name="subject_assignments"
    )
    institution = models.ForeignKey(
        Institution,
        on_delete=models.CASCADE,
        related_name="teacher_assignments"
    )
    board_subject = models.ForeignKey(
        "question_bank.BoardSubject",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="assigned_teachers"
    )
    competitive_exam = models.ForeignKey(
        "question_bank.CompetitiveExam",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="assigned_teachers"
    )
    academic_session = models.ForeignKey(
        AcademicSession,
        on_delete=models.CASCADE,
        related_name="teacher_assignments"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["institution", "teacher_profile"]

    def __str__(self):
        subject = self.board_subject or self.competitive_exam
        return f"{self.teacher_profile.user.username} -> {subject} ({self.institution.code})"