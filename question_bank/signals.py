# Backend/question_bank/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Question

@receiver(post_save, sender=Question)
def sync_question_learning_resource(sender, instance, created, **kwargs):
    """
    Placeholder for future resource syncing logic.
    Safely bypassed because learning_resources app is not installed.
    """
    pass