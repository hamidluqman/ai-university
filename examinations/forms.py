from django import forms
from .models import Exam
from question_bank.models import BoardSubject, BoardChapter, BoardTopic, BoardSubTopic, CompetitiveModule, CompetitiveSubModule

class ExamCreationForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = [
            'title', 'exam_type', 'assessment_flow', 'scope_level',
            'board_subject', 'board_topic', 'board_subtopic',
            'competitive_module', 'competitive_submodule',
            'total_questions', 'duration_minutes', 'passing_percentage',
            'start_time', 'end_time', 'is_class_wide'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'exam_type': forms.Select(attrs={'class': 'form-select'}),
            'assessment_flow': forms.Select(attrs={'class': 'form-select'}),
            'scope_level': forms.Select(attrs={'class': 'form-select'}),
            'board_subject': forms.Select(attrs={'class': 'form-select'}),
            'board_topic': forms.Select(attrs={'class': 'form-select'}),
            'board_subtopic': forms.Select(attrs={'class': 'form-select'}),
            'competitive_module': forms.Select(attrs={'class': 'form-select'}),
            'competitive_submodule': forms.Select(attrs={'class': 'form-select'}),
            'total_questions': forms.NumberInput(attrs={'class': 'form-control'}),
            'duration_minutes': forms.NumberInput(attrs={'class': 'form-control'}),
            'passing_percentage': forms.NumberInput(attrs={'class': 'form-control'}),
            'start_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'end_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'is_class_wide': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        subject_qs = BoardSubject.objects.filter(is_active=True)
        
        if user and not user.is_superuser:
            profile = getattr(user, 'profile', None)
            if profile and hasattr(profile, 'assigned_subjects') and profile.assigned_subjects.exists():
                subject_qs = profile.assigned_subjects.filter(is_active=True)

        self.fields['board_subject'].queryset = subject_qs
        self.fields['board_topic'].queryset = BoardTopic.objects.none()
        self.fields['board_subtopic'].queryset = BoardSubTopic.objects.none()

        if 'board_subject' in self.data:
            try:
                subject_id = int(self.data.get('board_subject'))
                self.fields['board_topic'].queryset = BoardTopic.objects.filter(chapter__subject_id=subject_id)
            except (ValueError, TypeError):
                pass

        if 'board_topic' in self.data:
            try:
                topic_id = int(self.data.get('board_topic'))
                self.fields['board_subtopic'].queryset = BoardSubTopic.objects.filter(topic_id=topic_id)
            except (ValueError, TypeError):
                pass