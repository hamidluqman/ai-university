from django.urls import path
from . import views

app_name = 'courses'

urlpatterns = [
    path('', views.courses_dashboard_view, name='course_list'),
    path('player/<str:category>/<int:node_id>/', views.course_player_view, name='course_player'),
    path('progress/update/<int:question_id>/', views.update_progress_ajax, name='update_progress'),
]