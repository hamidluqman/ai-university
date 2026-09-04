from django.db import models
from accounts.models import User
from question_bank.models import Question

class LessonProgress(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lesson_progress')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='video_progress', null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.student.username} - {self.question.text[:30] if self.question else 'N/A'}"