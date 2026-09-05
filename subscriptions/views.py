from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from .models import SubscriptionPlan, Subscription
from .forms import PaymentSubmissionForm, SubscriptionPlanForm
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.admin.views.decorators import staff_member_required

User = get_user_model()


def is_superadmin(user):
    return user.is_superuser or getattr(user, 'role', None) == 'superadmin'


@login_required
def user_subscription_tab_view(request):
    """
    Dedicated view for the user's subscription tab showing status and payment options.
    """
    user = request.user
    subscriptions = []
    
    if getattr(user, 'role', None) == 'student':
        if hasattr(user, 'personal_subscription') and user.personal_subscription:
            subscriptions = [user.personal_subscription]
        else:
            subscriptions = Subscription.objects.filter(user=user)
    elif getattr(user, 'role', None) == 'institution_admin' and hasattr(user, 'institution_admin_profile'):
        inst = user.institution_admin_profile.institution
        subscriptions = Subscription.objects.filter(institution=inst)
    else:
        subscriptions = Subscription.objects.filter(user=user)

    return render(request, 'subscriptions/user_tab.html', {
        'subscriptions': subscriptions,
        'title': 'My Subscription & Payments'
    })


@login_required
def submit_payment_view(request, subscription_id=None):
    """
    Allows users to submit payment reference, plan selection, and receipt proof for a specific subscription.
    """
    user = request.user
    
    if subscription_id:
        subscription = get_object_or_404(Subscription, id=subscription_id)
    else:
        if getattr(user, 'role', None) == 'student' and hasattr(user, 'personal_subscription'):
            subscription = user.personal_subscription
        elif getattr(user, 'role', None) == 'institution_admin' and hasattr(user, 'institution_admin_profile'):
            inst = user.institution_admin_profile.institution
            subscription = Subscription.objects.filter(institution=inst).order_by('-id').first()
        else:
            subscription = Subscription.objects.filter(user=user).order_by('-id').first()

    if not subscription:
        messages.info(request, "Please choose a subscription plan first.")
        return redirect('subscriptions:subscription_plans')

    if request.method == 'POST':
        form = PaymentSubmissionForm(request.POST, request.FILES, instance=subscription)
        if form.is_valid():
            sub = form.save(commit=False)
            sub.payment_status = 'pending'
            sub.is_active = False
            sub.save()
            
            # Send notification email to Superadmin
            try:
                send_mail(
                    subject=f"New Payment Submission - #{sub.id}",
                    message=f"User {user.username} has submitted payment proof for plan '{sub.plan.name if sub.plan else 'N/A'}'. Reference: {sub.payment_reference}",
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'webmaster@localhost'),
                    recipient_list=[getattr(settings, 'ADMIN_EMAIL', 'admin@aiuniversity.com')],
                    fail_silently=True,
                )
            except Exception:
                pass

            messages.success(request, "Payment details submitted successfully! Awaiting Superadmin verification.")
            return redirect('subscriptions:user_subscription_tab')
    else:
        form = PaymentSubmissionForm(instance=subscription)

    return render(request, 'subscriptions/submit_payment.html', {
        'form': form,
        'subscription': subscription,
        'title': 'Submit Payment Verification'
    })


@login_required
def subscription_plans_view(request):
    plans = SubscriptionPlan.objects.filter(is_active=True)
    if request.method == 'POST':
        plan_id = request.POST.get('plan_id')
        payment_ref = request.POST.get('payment_reference', '').strip()
        plan = get_object_or_404(SubscriptionPlan, id=plan_id)

        student_profile = getattr(request.user, 'student_profile', None)
        institution = student_profile.institution if student_profile else None
        
        if getattr(request.user, 'role', None) == 'institution_admin' and hasattr(request.user, 'institution_admin_profile'):
            institution = request.user.institution_admin_profile.institution

        Subscription.objects.create(
            user=request.user if not institution else None,
            institution=institution,
            plan=plan,
            payment_reference=payment_ref,
            payment_status='pending',
            is_active=False
        )
        messages.success(request, "Payment request submitted! Awaiting Superadmin activation.")
        return redirect('subscriptions:user_subscription_tab')

    return render(request, 'subscriptions/plans.html', {'plans': plans})


@login_required
@user_passes_test(is_superadmin)
def admin_subscription_panel(request):
    context = {
        'pending_subscriptions': Subscription.objects.filter(payment_status='pending'),
        'active_subscriptions': Subscription.objects.filter(payment_status='approved', is_active=True),
        'expired_subscriptions': Subscription.objects.filter(payment_status='rejected'),
        'subscriptions': Subscription.objects.all(),
    }
    return render(request, 'subscriptions/admin_panel.html', context)


@login_required
@user_passes_test(is_superadmin)
def add_subscription_view(request):
    """
    View to handle manual admin addition or activation of a user subscription.
    """
    plans = SubscriptionPlan.objects.filter(is_active=True)
    users = User.objects.all()

    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        plan_id = request.POST.get('plan_id')
        payment_ref = request.POST.get('payment_reference', '').strip()
        
        target_user = get_object_or_404(User, id=user_id)
        plan = get_object_or_404(SubscriptionPlan, id=plan_id)
        
        duration = plan.duration_days if plan.duration_days else 30
        start = timezone.now()
        end = start + timedelta(days=duration)

        Subscription.objects.create(
            user=target_user,
            plan=plan,
            payment_reference=payment_ref or 'ADMIN-MANUAL-ACTIVATION',
            payment_status='approved',
            start_date=start,
            end_date=end,
            is_active=True
        )
        messages.success(request, f"Subscription successfully created and activated for {target_user.username}.")
        return redirect('subscriptions:admin_subscription_panel')

    return render(request, 'subscriptions/add_subscription.html', {
        'plans': plans,
        'users': users,
        'title': 'Add & Activate Subscription'
    })


@login_required
@user_passes_test(is_superadmin)
def approve_subscription(request, subscription_id):
    subscription = get_object_or_404(Subscription, id=subscription_id)
    
    # Target user or institution to clean up all related pending entries
    target_user = subscription.user
    target_institution = subscription.institution

    # Activate the specific subscription
    subscription.payment_status = 'approved'
    subscription.start_date = timezone.now()
    duration = subscription.plan.duration_days if subscription.plan else 30
    subscription.end_date = timezone.now() + timedelta(days=duration)
    subscription.is_active = True
    subscription.save()

    # Aggressively approve and clear ALL pending records for this user or institution
    if target_user:
        Subscription.objects.filter(user=target_user, payment_status__iexact='pending').update(
            payment_status='approved', is_active=True, start_date=timezone.now(), end_date=timezone.now() + timedelta(days=duration)
        )
    if target_institution:
        Subscription.objects.filter(institution=target_institution, payment_status__iexact='pending').update(
            payment_status='approved', is_active=True, start_date=timezone.now(), end_date=timezone.now() + timedelta(days=duration)
        )

    # Send approval email notification
    if target_user and target_user.email:
        try:
            send_mail(
                subject="Subscription Approved - AI University LMS",
                message=f"Your subscription for plan '{subscription.plan.name if subscription.plan else ''}' has been approved and activated successfully!",
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'webmaster@localhost'),
                recipient_list=[target_user.email],
                fail_silently=True,
            )
        except Exception:
            pass

    messages.success(request, f"Subscription #{subscription.id} and related records activated successfully!")
    return redirect('accounts:dashboard_redirect')


@login_required
@user_passes_test(is_superadmin)
def reject_subscription(request, subscription_id):
    subscription = get_object_or_404(Subscription, id=subscription_id)
    subscription.payment_status = 'rejected'
    subscription.is_active = False
    subscription.save()

    messages.warning(request, f"Subscription #{subscription.id} marked as rejected.")
    return redirect('subscriptions:admin_subscription_panel')

@staff_member_required
def add_subscription_plan(request):
    if request.method == 'POST':
        form = SubscriptionPlanForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Subscription plan created successfully!")
            return redirect('subscriptions:admin_subscription_panel')
    else:
        form = SubscriptionPlanForm()
    
    return render(request, 'subscriptions/add_plan.html', {'form': form})