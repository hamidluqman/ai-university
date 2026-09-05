from django import forms
from .models import Subscription
from .models import SubscriptionPlan

class SubscriptionPlanForm(forms.ModelForm):
    class Meta:
        model = SubscriptionPlan
        fields = ['name', 'plan_type', 'price', 'duration_days', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Pro Plan'}),
            'plan_type': forms.Select(attrs={'class': 'form-select'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00'}),
            'duration_days': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '30'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }


class PaymentSubmissionForm(forms.ModelForm):
    class Meta:
        model = Subscription
        fields = ['plan', 'payment_reference', 'receipt_image']
        widgets = {
            'plan': forms.Select(attrs={
                'class': 'form-select'
            }),
            'payment_reference': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Enter transaction ID, bank reference, or receipt number'
            }),
            'receipt_image': forms.FileInput(attrs={
                'class': 'form-control'
            }),
        }