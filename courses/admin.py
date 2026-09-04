from django.contrib import admin
from .models import LessonProgress

@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ('student', 'question', 'is_completed', 'completed_at')
    list_filter = ('is_completed',)
    search_fields = ('student__username', 'question__text')
    autocomplete_fields = ['question']  # Eliminates the popup green '+' button and uses a search widget