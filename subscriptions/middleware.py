from django.shortcuts import redirect
from django.urls import reverse
from .utils import verify_user_subscription_status

class SubscriptionCheckMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Prevent infinite redirect loops for subscription, admin, and static asset routes
        exempt_paths = ['/admin/', '/static/', '/media/', '/subscriptions/']
        if any(request.path.startswith(path) for path in exempt_paths):
            return self.get_response(request)

        protected_routes = ['/question_bank/', '/create-question/', '/exam/', '/examinations/']

        if any(request.path.startswith(route) for route in protected_routes):
            has_access, is_expired, message = verify_user_subscription_status(request.user)

            if not has_access:
                if "pending" in message.lower():
                    return redirect('subscriptions:user_subscription_tab')
                
                if is_expired:
                    request.session['show_expiration_modal'] = True
                    request.session['expiration_message'] = message
                    
                return redirect('subscriptions:subscription_plans')

        return self.get_response(request)