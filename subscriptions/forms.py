from django import forms
from .models import Subscription

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