from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import (
    BoardClass, BoardSubject, BoardChapter, BoardTopic, BoardSubTopic,
    CompetitiveExam, CompetitiveModule, CompetitiveSubModule, Question
)

# Clear previous registrations
for model in [BoardClass, BoardSubject, BoardChapter, BoardTopic, BoardSubTopic,
              CompetitiveExam, CompetitiveModule, CompetitiveSubModule, Question]:
    try:
        admin.site.unregister(model)
    except admin.sites.NotRegistered:
        pass


# ==========================================================
# DROPDOWN FILTER BASE CLASS
# ==========================================================

class DropdownFilter(admin.SimpleListFilter):
    template = 'admin/dropdown_filter.html'


# ==========================================================
# BOARD DROPDOWN FILTERS
# ==========================================================

class BoardClassDropdownFilter(DropdownFilter):
    title = _('Board Class')
    parameter_name = 'board_class'

    def lookups(self, request, model_admin):
        return [(c.id, c.name) for c in BoardClass.objects.all()]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(board_subtopic__topic__chapter__subject__board_class_id=self.value())
        return queryset


class BoardSubjectDropdownFilter(DropdownFilter):
    title = _('Board Subject')
    parameter_name = 'board_subject'

    def lookups(self, request, model_admin):
        class_id = request.GET.get('board_class')
        if class_id:
            subjects = BoardSubject.objects.filter(board_class_id=class_id)
        else:
            subjects = BoardSubject.objects.all()
        return [(s.id, f"{s.board_class.name} - {s.name}") for s in subjects]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(board_subtopic__topic__chapter__subject_id=self.value())
        return queryset


class BoardChapterDropdownFilter(DropdownFilter):
    title = _('Board Chapter')
    parameter_name = 'board_chapter'

    def lookups(self, request, model_admin):
        subject_id = request.GET.get('board_subject')
        if subject_id:
            chapters = BoardChapter.objects.filter(subject_id=subject_id)
        else:
            chapters = BoardChapter.objects.all()
        return [(c.id, c.title) for c in chapters]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(board_subtopic__topic__chapter_id=self.value())
        return queryset


class BoardTopicDropdownFilter(DropdownFilter):
    title = _('Board Topic')
    parameter_name = 'board_topic'

    def lookups(self, request, model_admin):
        chapter_id = request.GET.get('board_chapter')
        if chapter_id:
            topics = BoardTopic.objects.filter(chapter_id=chapter_id)
        else:
            topics = BoardTopic.objects.all()
        return [(t.id, t.title) for t in topics]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(board_subtopic__topic_id=self.value())
        return queryset


# ==========================================================
# COMPETITIVE DROPDOWN FILTERS
# ==========================================================

class CompetitiveExamDropdownFilter(DropdownFilter):
    title = _('Competitive Exam')
    parameter_name = 'competitive_exam'

    def lookups(self, request, model_admin):
        return [(e.id, e.title) for e in CompetitiveExam.objects.all()]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(competitive_submodule__module__exam_id=self.value())
        return queryset


class CompetitiveModuleDropdownFilter(DropdownFilter):
    title = _('Competitive Module')
    parameter_name = 'competitive_module'

    def lookups(self, request, model_admin):
        exam_id = request.GET.get('competitive_exam')
        if exam_id:
            modules = CompetitiveModule.objects.filter(exam_id=exam_id)
        else:
            modules = CompetitiveModule.objects.all()
        return [(m.id, m.title) for m in modules]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(competitive_submodule__module_id=self.value())
        return queryset


# ==========================================================
# HIERARCHY MODEL ADMINS
# ==========================================================

@admin.register(BoardClass)
class BoardClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')


@admin.register(BoardSubject)
class BoardSubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'board_class', 'code', 'is_active')


@admin.register(BoardChapter)
class BoardChapterAdmin(admin.ModelAdmin):
    list_display = ('title', 'chapter_number', 'subject')


@admin.register(BoardTopic)
class BoardTopicAdmin(admin.ModelAdmin):
    list_display = ('title', 'chapter', 'order')


@admin.register(BoardSubTopic)
class BoardSubTopicAdmin(admin.ModelAdmin):
    list_display = ('title', 'topic', 'order')


@admin.register(CompetitiveExam)
class CompetitiveExamAdmin(admin.ModelAdmin):
    list_display = ('title', 'code', 'is_active')


@admin.register(CompetitiveModule)
class CompetitiveModuleAdmin(admin.ModelAdmin):
    list_display = ('title', 'exam', 'order')


@admin.register(CompetitiveSubModule)
class CompetitiveSubModuleAdmin(admin.ModelAdmin):
    list_display = ('title', 'module', 'order')


# ==========================================================
# QUESTION BANK ADMIN
# ==========================================================

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    actions = ['delete_selected']

    list_display = (
        'get_statement',
        'assessment_flow',
        'get_board_classification',
        'get_competitive_classification',
        'correct_option',
        'has_video_resource',
        'created_at'
    )

    list_filter = (
        'assessment_flow',
        BoardClassDropdownFilter,
        BoardSubjectDropdownFilter,
        BoardChapterDropdownFilter,
        BoardTopicDropdownFilter,
        CompetitiveExamDropdownFilter,
        CompetitiveModuleDropdownFilter,
        'created_at'
    )

    search_fields = (
        'question_text',
        'option_a',
        'option_b',
        'option_c',
        'option_d',
        'explanation'
    )

    @admin.display(description='Question Statement')
    def get_statement(self, obj):
        if obj.question_text:
            return obj.question_text[:50] + ('...' if len(obj.question_text) > 50 else '')
        elif obj.question_image:
            return "📷 Image Question"
        return "[Empty Statement]"

    @admin.display(description='Board Scope')
    def get_board_classification(self, obj):
        if obj.board_subtopic:
            st = obj.board_subtopic
            t = st.topic
            c = t.chapter
            s = c.subject
            bc = s.board_class
            return f"{bc.name} → {s.name} → {c.title} → {t.title} → {st.title}"
        return "-"

    @admin.display(description='Competitive Scope')
    def get_competitive_classification(self, obj):
        if obj.competitive_submodule:
            sm = obj.competitive_submodule
            m = sm.module
            e = m.exam
            return f"{e.title} → {m.title} → {sm.title}"
        return "-"

    @admin.display(description='Video', boolean=True)
    def has_video_resource(self, obj):
        return bool(obj.youtube_url)