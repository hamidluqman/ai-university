from django.urls import path
from . import views

app_name = 'examinations'

urlpatterns = [
    path('start/board/<int:pk>/', views.start_board_exam_for_topic, name='start_board_exam'),
    path('start/competitive/<int:pk>/', views.start_competitive_exam_for_topic, name='start_competitive_exam'),
    path('take/<int:exam_id>/', views.take_exam_view, name='take_exam'),
    path('create/', views.create_exam_view, name='create_exam'),
    path('take/<int:exam_id>/submit/', views.take_exam_view, name='submit_exam'),
    path('result/<int:attempt_id>/', views.exam_result_view, name='exam_result'),
    path('result/<int:attempt_id>/remedial-videos/', views.exam_remedial_videos_view, name='exam_remedial_videos'),
    path('dashboard/', views.results_dashboard, name='results_dashboard'),
    path('official-exams/', views.official_exams_view, name='official_exams'),
    path('teacher-exams/', views.teacher_exams_view, name='teacher_exams'),
    path('practice-setup/', views.student_practice_setup_view, name='practice_setup'),
    path('practice-setup/<int:subtopic_id>/', views.student_practice_setup_view, name='practice_setup'),
    path('practice/start/<int:subtopic_id>/', views.start_subtopic_practice_view, name='start_practice'),
    path('grant-retest/<int:exam_id>/', views.grant_retest_view, name='grant_retest'),
    path('download-pdf/', views.download_results_pdf, name='download_pdf'),
    path('download-teacher-pdf/', views.download_teacher_results_pdf, name='download_teacher_results_pdf'),
    path('download-pdf-alt/', views.download_results_pdf, name='download_results_pdf'),
    path('api/analytics/performance/', views.class_performance_analytics_api, name='api_performance_analytics'),
    path('api/analytics/weaknesses/', views.topic_weakness_analytics_api, name='api_weakness_analytics'),
    path('ajax/load-topics/', views.ajax_load_topics, name='ajax_load_topics'),
    path('ajax/load-subtopics/', views.ajax_load_subtopics, name='ajax_load_subtopics'),
    path('exam/delete/<int:exam_id>/', views.delete_exam_view, name='delete_exam'),
    path('results/', views.results_dashboard, name='results_dashboard'),
]