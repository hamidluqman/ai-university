from django.db import models
from django.conf import settings
from question_bank.models import (
    BoardSubject, BoardTopic, BoardSubTopic, 
    CompetitiveModule, CompetitiveSubModule, Question
)

class Exam(models.Model):
    EXAM_TYPE_CHOICES = [
        ('quiz', 'Quiz'),
        ('midterm', 'Midterm'),
        ('final', 'Final'),
        ('practice', 'Practice'),
    ]

    ASSESSMENT_FLOW_CHOICES = [
        ('board', 'Board System'),
        ('competitive', 'Competitive System'),
    ]

    SCOPE_LEVEL_CHOICES = [
        ('subject', 'Subject / Module Level'),
        ('topic', 'Topic Level'),
        ('subtopic', 'Subtopic / Submodule Level'),
    ]

    title = models.CharField(max_length=255)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_exams')
    institution = models.ForeignKey('institutions.Institution', on_delete=models.CASCADE, null=True, blank=True, related_name='institution_exams')
    
    exam_type = models.CharField(max_length=20, choices=EXAM_TYPE_CHOICES, default='quiz')
    assessment_flow = models.CharField(max_length=20, choices=ASSESSMENT_FLOW_CHOICES)
    scope_level = models.CharField(max_length=20, choices=SCOPE_LEVEL_CHOICES)

    board_subject = models.ForeignKey(BoardSubject, on_delete=models.SET_NULL, null=True, blank=True, related_name='board_exams')
    board_topic = models.ForeignKey(BoardTopic, on_delete=models.SET_NULL, null=True, blank=True, related_name='topic_exams')
    board_subtopic = models.ForeignKey(BoardSubTopic, on_delete=models.SET_NULL, null=True, blank=True, related_name='subtopic_exams')

    competitive_module = models.ForeignKey(CompetitiveModule, on_delete=models.SET_NULL, null=True, blank=True, related_name='competitive_exams_module')
    competitive_submodule = models.ForeignKey(CompetitiveSubModule, on_delete=models.SET_NULL, null=True, blank=True, related_name='competitive_exams_submodule')

    questions = models.ManyToManyField(Question, related_name='exams', blank=True)
    total_questions = models.PositiveIntegerField(default=10)
    duration_minutes = models.PositiveIntegerField(default=30)
    passing_percentage = models.FloatField(default=50.0)
    
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    is_class_wide = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        super().clean()
        if self.assessment_flow == 'board':
            self.competitive_module = None
            self.competitive_submodule = None
            if self.scope_level == 'subject':
                self.board_topic = None
                self.board_subtopic = None
            elif self.scope_level == 'topic':
                self.board_subtopic = None
        elif self.assessment_flow == 'competitive':
            self.board_subject = None
            self.board_topic = None
            self.board_subtopic = None
            if self.scope_level in ['subject', 'topic']:
                self.competitive_submodule = None

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} ({self.get_assessment_flow_display()})"


class ExamAttempt(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='exam_attempts')
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='attempts')
    score = models.IntegerField(default=0)
    total_marks = models.IntegerField(default=0)
    percentage = models.FloatField(default=0.0)
    is_passed = models.BooleanField(default=False)
    is_practice = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.username} - {self.exam.title}"


class StudentAnswer(models.Model):
    attempt = models.ForeignKey(ExamAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_option = models.CharField(max_length=1, null=True, blank=True)
    is_correct = models.BooleanField(default=False)


class RetestPermission(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='retest_permissions')
    granted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    is_for_entire_class = models.BooleanField(default=True)
    granted_at = models.DateTimeField(auto_now_add=True)