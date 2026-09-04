from django.utils import timezone

def verify_user_subscription_status(user):
    """
    Returns a tuple: (has_access, is_expired, message)
    """
    if not user.is_authenticated:
        return False, False, "Authentication required."
    
    if user.is_superuser or getattr(user, 'role', None) == 'superadmin':
        return True, False, "Admin Access"

    profile = getattr(user, 'profile', None)
    role = getattr(user, 'role', None) or (profile.role if profile else None)

    # Case 1: Institutional Members (Teacher, Institution Student, Institution Admin)
    if role in ['TEACHER', 'INSTITUTION_STUDENT', 'INSTITUTION_ADMIN', 'institution_admin', 'teacher']:
        inst = getattr(profile, 'institution', None) if profile else None
        if not inst and hasattr(user, 'institution'):
            inst = user.institution
            
        if not inst:
            return False, False, "No institution assigned."
        
        # Check through related_name 'subscriptions' or single instance
        sub = inst.subscriptions.filter(payment_status='approved', is_active=True).order_by('-id').first()
        if not sub:
            sub = inst.subscriptions.order_by('-id').first()
            
        if sub:
            if sub.is_valid():
                return True, False, "Active Institutional Access"
            elif sub.payment_status == 'pending':
                return False, False, "Payment pending verification."
            else:
                expiry_str = sub.end_date.strftime('%b %d, %Y at %I:%M %p') if sub.end_date else "N/A"
                return False, True, f"Your institution's subscription expired or is pending on {expiry_str}."
        return False, False, "Institution has no active plan."

    # Case 2: Independent Students
    elif role in ['INDEPENDENT_STUDENT', 'student']:
        sub = getattr(user, 'personal_subscription', None)
        if not sub:
            sub = user.subscriptions.filter(payment_status='approved', is_active=True).order_by('-id').first()
            if not sub:
                sub = user.subscriptions.order_by('-id').first()
                
        if sub:
            if sub.is_valid():
                return True, False, "Active Personal Access"
            elif sub.payment_status == 'pending':
                return False, False, "Payment pending verification."
            else:
                expiry_str = sub.end_date.strftime('%b %d, %Y at %I:%M %p') if sub.end_date else "N/A"
                return False, True, f"Your subscription expired or is pending on {expiry_str}."
        return False, False, "No active subscription found."

    return False, False, "Unauthorized Role"