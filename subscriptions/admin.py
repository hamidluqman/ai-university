from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from .models import SubscriptionPlan, Subscription

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'plan_type', 'price', 'duration_days', 'is_active')
    list_filter = ('plan_type', 'is_active')


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'plan', 'payment_status', 'payment_reference', 'is_active', 'start_date', 'end_date')
    list_filter = ('payment_status', 'is_active', 'plan__plan_type')
    search_fields = ('user__username', 'institution__name', 'payment_reference')
    readonly_fields = ('receipt_preview', 'created_at', 'updated_at')
    actions = ['approve_payments', 'reject_payments']
    
    fields = (
        'user', 
        'institution', 
        'plan', 
        'payment_status', 
        'payment_reference', 
        'receipt_image', 
        'receipt_preview', 
        'is_active', 
        'start_date', 
        'end_date'
    )

    def receipt_preview(self, obj):
        if obj.receipt_image:
            return format_html('<img src="{}" width="200" style="border-radius: 8px;" />', obj.receipt_image.url)
        return "No receipt uploaded yet."
    receipt_preview.short_description = "Receipt Preview"

    @admin.action(description="Approve selected payments & activate subscriptions")
    def approve_payments(self, request, queryset):
        for obj in queryset:
            obj.payment_status = 'approved'
            obj.is_active = True
            if not obj.start_date:
                obj.start_date = timezone.now()
            if not obj.end_date and obj.plan:
                obj.end_date = obj.start_date + timezone.timedelta(days=obj.plan.duration_days)
            obj.save()
        self.message_user(request, f"Successfully approved {queryset.count()} subscription payment(s).")

    @admin.action(description="Reject selected payments")
    def reject_payments(self, request, queryset):
        queryset.update(payment_status='rejected', is_active=False)
        self.message_user(request, f"Marked {queryset.count()} subscription payment(s) as rejected.")

    def save_model(self, request, obj, form, change):
        if obj.payment_status == 'approved' and not obj.is_active:
            obj.is_active = True
            if not obj.start_date:
                obj.start_date = timezone.now()
            if not obj.end_date and obj.plan:
                obj.end_date = obj.start_date + timezone.timedelta(days=obj.plan.duration_days)
        elif obj.payment_status != 'approved':
            obj.is_active = False
            
        super().save_model(request, obj, form, change)