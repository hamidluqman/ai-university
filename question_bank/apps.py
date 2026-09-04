from django.apps import AppConfig


class QuestionBankConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'question_bank'

    def ready(self):
        try:
            import question_bank.signals  # noqa
        except ModuleNotFoundError:
            pass