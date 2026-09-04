from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('dashboard/', views.dashboard_redirect, name='dashboard_redirect'),
    path('', views.user_management_hub, name='user_management_hub'),
    path('hub/', views.user_management_hub, name='user_management_hub'),
    path('user-hub/', views.user_management_hub, name='user_hub'),
    path('add-institution/', views.create_institution_view, name='create_institution'),
    path('add-teacher/', views.create_teacher_view, name='create_teacher'),
    path('add-student/', views.create_student_view, name='create_student'),
    path('add-content-team/', views.create_content_team_view, name='create_content_team'),
    path('institution/delete/<int:institution_id>/', views.delete_institution_view, name='delete_institution'),
    path('teacher/delete/<int:teacher_id>/', views.delete_teacher_view, name='delete_teacher'),
    path('student/delete/<int:student_id>/', views.delete_student_view, name='delete_student'),
    path('teachers/create/', views.create_teacher_view, name='create_teacher'),
    path('profile/settings/', views.superadmin_profile_view, name='superadmin_profile'),
    path('content-team/delete/<int:user_id>/', views.delete_content_team_view, name='delete_content_team'),
    path('teacher/class/<int:class_id>/roster/', views.class_roster_view, name='class_roster'),
    path('teacher/exam/<int:exam_id>/results/', views.exam_results_view, name='exam_results'),
    path('teacher/profile/settings/', views.teacher_profile_view, name='teacher_profile'),
    path('institution/dashboard/', views.institution_dashboard_view, name='institution_dashboard'),
    path('exam/delete/<int:exam_id>/', views.delete_exam_view, name='delete_exam'),
    path('dashboard/institutional-student/', views.institutional_student_dashboard, name='institutional_student_dashboard'),
    path('courses/', views.student_courses_view, name='student_courses'),
    path('assessments/', views.student_assessments_view, name='student_assessments'),
    path('results/', views.student_results_view, name='student_results'),
    path('weak-topics/', views.student_weak_topics_view, name='student_weak_topics'),
    path('independent/courses/', views.independent_student_courses_view, name='independent_student_courses'),
    path('start/<int:pk>/', views.start_exam_for_topic, name='start_exam'),
    path('independent/exam/start/<int:pk>/', views.start_exam_for_topic, name='start_exam'),
    path('student/weak-topics/', views.student_weak_topics_view, name='student_weak_topics'),
    path('student/profile/', views.independent_student_profile_view, name='independent_student_profile'),
    path('superadmin/subscriptions/approvals/', views.manage_subscription_requests, name='manage_subscription_requests'),
    path('superadmin/subscriptions/manage/', views.manage_subscription_requests, name='manage_subscription_requests'),
]