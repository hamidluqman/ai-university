from django import forms
from .models import (
    Question, BoardClass, BoardSubject, BoardChapter, BoardTopic, BoardSubTopic,
    CompetitiveExam, CompetitiveModule, CompetitiveSubModule
)


class UnifiedQuestionForm(forms.ModelForm):
    assessment_flow = forms.ChoiceField(
        choices=Question.FLOW_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select fw-bold', 'id': 'id_assessment_flow'}),
        label="Assessment Flow"
    )

    question_text = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter question statement (Optional if image is provided)...'}),
        label="Question Text",
        required=False
    )
    question_image = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control'}),
        label="Question Image (Optional)"
    )

    option_a = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Option A'}), required=False)
    option_a_image = forms.ImageField(required=False, widget=forms.FileInput(attrs={'class': 'form-control'}))

    option_b = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Option B'}), required=False)
    option_b_image = forms.ImageField(required=False, widget=forms.FileInput(attrs={'class': 'form-control'}))

    option_c = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Option C'}), required=False)
    option_c_image = forms.ImageField(required=False, widget=forms.FileInput(attrs={'class': 'form-control'}))

    option_d = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Option D'}), required=False)
    option_d_image = forms.ImageField(required=False, widget=forms.FileInput(attrs={'class': 'form-control'}))

    correct_option = forms.ChoiceField(
        choices=Question.OPTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Correct Option"
    )

    explanation = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Detailed explanation or solution hint...'}),
        required=False
    )
    youtube_url = forms.URLField(
        widget=forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://www.youtube.com/watch?v=...'}),
        required=False,
        label="YouTube Solution URL"
    )

    # Board Hierarchy Fields
    board_class = forms.ModelChoiceField(
        queryset=BoardClass.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_board_class'}),
        label="1. Board Class"
    )
    board_subject = forms.ModelChoiceField(
        queryset=BoardSubject.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_board_subject'}),
        label="2. Board Subject"
    )
    board_chapter = forms.ModelChoiceField(
        queryset=BoardChapter.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_board_chapter'}),
        label="3. Board Chapter"
    )
    board_topic = forms.ModelChoiceField(
        queryset=BoardTopic.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_board_topic'}),
        label="4. Board Topic"
    )
    board_subtopic = forms.ModelChoiceField(
        queryset=BoardSubTopic.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_board_subtopic'}),
        label="5. Board SubTopic"
    )

    # Competitive Hierarchy Fields
    competitive_exam = forms.ModelChoiceField(
        queryset=CompetitiveExam.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_competitive_exam'}),
        label="1. Competitive Exam"
    )
    competitive_module = forms.ModelChoiceField(
        queryset=CompetitiveModule.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_competitive_module'}),
        label="2. Competitive Module"
    )
    competitive_submodule = forms.ModelChoiceField(
        queryset=CompetitiveSubModule.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_competitive_submodule'}),
        label="3. Competitive SubModule"
    )

    class Meta:
        model = Question
        fields = [
            'assessment_flow', 'question_text', 'question_image',
            'option_a', 'option_a_image',
            'option_b', 'option_b_image',
            'option_c', 'option_c_image',
            'option_d', 'option_d_image',
            'correct_option', 'explanation', 'youtube_url'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Dynamic Queryset Population on POST to pass choice validation
        if 'board_class' in self.data:
            try:
                class_id = int(self.data.get('board_class'))
                self.fields['board_subject'].queryset = BoardSubject.objects.filter(board_class_id=class_id)
            except (ValueError, TypeError):
                pass

        if 'board_subject' in self.data:
            try:
                subject_id = int(self.data.get('board_subject'))
                self.fields['board_chapter'].queryset = BoardChapter.objects.filter(subject_id=subject_id)
            except (ValueError, TypeError):
                pass

        if 'board_chapter' in self.data:
            try:
                chapter_id = int(self.data.get('board_chapter'))
                self.fields['board_topic'].queryset = BoardTopic.objects.filter(chapter_id=chapter_id)
            except (ValueError, TypeError):
                pass

        if 'board_topic' in self.data:
            try:
                topic_id = int(self.data.get('board_topic'))
                self.fields['board_subtopic'].queryset = BoardSubTopic.objects.filter(topic_id=topic_id)
            except (ValueError, TypeError):
                pass

        if 'competitive_exam' in self.data:
            try:
                exam_id = int(self.data.get('competitive_exam'))
                self.fields['competitive_module'].queryset = CompetitiveModule.objects.filter(exam_id=exam_id)
            except (ValueError, TypeError):
                pass

        if 'competitive_module' in self.data:
            try:
                module_id = int(self.data.get('competitive_module'))
                self.fields['competitive_submodule'].queryset = CompetitiveSubModule.objects.filter(module_id=module_id)
            except (ValueError, TypeError):
                pass

    def clean(self):
        cleaned_data = super().clean()
        q_text = cleaned_data.get('question_text')
        q_image = cleaned_data.get('question_image')

        if not q_text and not q_image:
            raise forms.ValidationError("Question must contain either a text statement or an uploaded image statement.")
        return cleaned_data