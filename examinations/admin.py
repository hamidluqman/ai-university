from django.contrib import admin
from .models import Exam, ExamAttempt, StudentAnswer, RetestPermission

@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ('title', 'creator', 'institution', 'exam_type', 'assessment_flow', 'scope_level', 'created_at')
    list_filter = ('exam_type', 'assessment_flow', 'scope_level', 'is_class_wide', 'institution')
    search_fields = ('title', 'creator__username', 'institution__name')
    filter_horizontal = ('questions',)

@admin.register(ExamAttempt)
class ExamAttemptAdmin(admin.ModelAdmin):
    list_display = ('student', 'exam', 'score', 'total_marks', 'percentage', 'is_passed', 'is_practice', 'submitted_at')
    list_filter = ('is_passed', 'is_practice', 'submitted_at')
    search_fields = ('student__username', 'exam__title')

@admin.register(StudentAnswer)
class StudentAnswerAdmin(admin.ModelAdmin):
    list_display = ('attempt', 'question', 'selected_option', 'is_correct')
    list_filter = ('is_correct',)

@admin.register(RetestPermission)
class RetestPermissionAdmin(admin.ModelAdmin):
    list_display = ('exam', 'granted_by', 'is_for_entire_class', 'granted_at')
    list_filter = ('is_for_entire_class', 'granted_at')