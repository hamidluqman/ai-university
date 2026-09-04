from django.urls import path
from . import views

app_name = 'question_bank'

urlpatterns = [
    # Question Creation & Excel Import
    path('create/', views.create_question_view, name='create_question'),
    path('add/', views.create_question_view, name='add_question'),
    path('import-excel/', views.import_questions_excel, name='import_questions_excel'),
    
    # Hierarchy Builders
    path('board-builder/', views.unified_board_builder, name='unified_board_builder'),
    path('competitive-builder/', views.unified_competitive_builder, name='unified_competitive_builder'),
    
    # Cascade API Routes
    path('api/subjects/<int:class_id>/', views.get_board_subjects, name='api_get_subjects'),
    path('api/chapters/<int:subject_id>/', views.get_board_chapters, name='api_get_chapters'),
    path('api/topics/<int:chapter_id>/', views.get_board_topics, name='api_get_topics'),
    path('api/subtopics/<int:topic_id>/', views.get_board_subtopics, name='api_get_subtopics'),
    path('api/modules/<int:exam_id>/', views.get_competitive_modules, name='api_get_modules'),
    path('api/submodules/<int:module_id>/', views.get_competitive_submodules, name='api_get_submodules'),
    path('api/filter-questions/', views.api_filter_questions, name='api_filter_questions'),
]