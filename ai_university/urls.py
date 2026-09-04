from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static
from accounts import views as accounts_views

urlpatterns = [
    path('', RedirectView.as_view(url='/accounts/login/', permanent=False)),
    path('admin/', admin.site.urls),
    path('question-bank/', include(('question_bank.urls', 'question_bank'), namespace='question_bank')),
    
    # Global alias for admin panel compatibility
    path('accounts/hub/global/', accounts_views.user_management_hub, name='user_management_hub'),

    path('accounts/', include(('accounts.urls', 'accounts'), namespace='accounts')),
    path('examinations/', include(('examinations.urls', 'examinations'), namespace='examinations')),
    path('subscriptions/', include(('subscriptions.urls', 'subscriptions'), namespace='subscriptions')),
    path('courses/', include(('courses.urls', 'courses'), namespace='courses')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)