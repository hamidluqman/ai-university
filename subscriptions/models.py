from django.db import models
from django.utils import timezone
from accounts.models import User
from institutions.models import Institution


def get_default_end_date():
    return timezone.now() + timezone.timedelta(days=30)


class SubscriptionPlan(models.Model):
    PLAN_TYPES = [
        ('INDEPENDENT_STUDENT', 'Independent Student'),
        ('INSTITUTION', 'Institution'),
    ]

    name = models.CharField(max_length=255, unique=True)
    plan_type = models.CharField(max_length=50, choices=PLAN_TYPES)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    duration_days = models.IntegerField(default=30, help_text="Duration of the plan in days")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    def __str__(self):
        return f"{self.name} ({self.get_plan_type_display()}) - PKR {self.price}"


class Subscription(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='subscriptions'
    )
    institution = models.ForeignKey(
        Institution, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='subscriptions'
    )
    plan = models.ForeignKey(
        SubscriptionPlan, 
        on_delete=models.PROTECT,
        related_name='subscriptions'
    )
    
    # Payment verification fields
    payment_reference = models.CharField(max_length=255, blank=True, null=True, help_text="Bank transaction ID or receipt number")
    receipt_image = models.ImageField(upload_to='receipts/', blank=True, null=True, help_text="Uploaded screenshot of the payment")
    
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    is_active = models.BooleanField(default=False)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(default=get_default_end_date, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    def is_valid(self):
        if not self.is_active or self.payment_status != 'approved':
            return False
        if self.end_date and timezone.now() > self.end_date:
            return False
        return True

    def is_feature_accessible(self):
        return self.is_valid()

    def __str__(self):
        target = self.institution.name if self.institution else (self.user.username if self.user else "Unassigned")
        return f"Sub: {target} - Plan: {self.plan.name} [{self.payment_status}]"