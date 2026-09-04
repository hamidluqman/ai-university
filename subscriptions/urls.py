from django.urls import path
from . import views

app_name = 'subscriptions'

urlpatterns = [
    path('my-subscription/', views.user_subscription_tab_view, name='user_subscription_tab'),
    path('user-tab/', views.admin_subscription_panel, name='user_tab'),
    path('plans/', views.subscription_plans_view, name='subscription_plans'),
    path('admin-panel/', views.admin_subscription_panel, name='admin_subscription_panel'),
    path('approve/<int:subscription_id>/', views.approve_subscription, name='approve_subscription'),
    path('reject/<int:subscription_id>/', views.reject_subscription, name='reject_subscription'),
    path('submit-payment/', views.submit_payment_view, name='submit_payment'),
    path('submit-payment/<int:subscription_id>/', views.submit_payment_view, name='submit_payment_with_id'),
    path('add-subscription/', views.add_subscription_view, name='add_subscription'),
]