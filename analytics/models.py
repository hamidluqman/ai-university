from django.db import models


class StudentAnalytics(models.Model):
    student = models.OneToOneField('accounts.StudentProfile', on_delete=models.CASCADE, related_name='analytics')
    total_exams_taken = models.PositiveIntegerField(default=0)
    average_score = models.FloatField(default=0.0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Analytics: {self.student.user.username}"