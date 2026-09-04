from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect

def role_required(allowed_roles=[]):
    """
    Decorator to restrict view access based on user.role or superuser status.
    Ensures that authenticated users with valid roles or superuser status 
    can always access their dashboard/views, bypassing subscription locks on login.
    Usage: @role_required(['student', 'teacher'])
    """
    def check_role(user):
        if not user.is_authenticated:
            return False
        # Allow superusers, staff, or users matching allowed roles 
        # to proceed to their dashboards regardless of subscription pending/inactive states.
        if user.is_superuser or getattr(user, 'role', None) in allowed_roles:
            return True
        return False
    return user_passes_test(check_role, login_url='accounts:login')