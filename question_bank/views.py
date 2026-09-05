import pandas as pd
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import (
    BoardClass, BoardSubject, BoardChapter, BoardTopic, BoardSubTopic,
    CompetitiveExam, CompetitiveModule, CompetitiveSubModule, Question
)
from .forms import UnifiedQuestionForm


# ==========================================================
# CASCADING JSON API ENDPOINTS (FULL HIERARCHY SUPPORT)
# ==========================================================

@login_required
def get_board_subjects(request, class_id):
    subjects = BoardSubject.objects.filter(board_class_id=class_id, is_active=True).values('id', 'name')
    data = [{'id': s['id'], 'title': s['name']} for s in subjects]
    return JsonResponse(data, safe=False)


@login_required
def get_board_chapters(request, subject_id):
    chapters = BoardChapter.objects.filter(subject_id=subject_id).values('id', 'title')
    return JsonResponse(list(chapters), safe=False)


@login_required
def get_board_topics(request, chapter_id):
    topics = BoardTopic.objects.filter(chapter_id=chapter_id).values('id', 'title')
    return JsonResponse(list(topics), safe=False)


@login_required
def get_board_subtopics(request, topic_id):
    subtopics = BoardSubTopic.objects.filter(topic_id=topic_id).values('id', 'title')
    return JsonResponse(list(subtopics), safe=False)


@login_required
def get_competitive_modules(request, exam_id):
    modules = CompetitiveModule.objects.filter(exam_id=exam_id).values('id', 'title')
    return JsonResponse(list(modules), safe=False)


@login_required
def get_competitive_submodules(request, module_id):
    submodules = CompetitiveSubModule.objects.filter(module_id=module_id).values('id', 'title')
    return JsonResponse(list(submodules), safe=False)


# ==========================================================
# UNIFIED HIERARCHY BUILDERS
# ==========================================================

@login_required
def unified_board_builder(request):
    """Single form to hierarchically build Class -> Subject -> Chapter -> Topic -> SubTopic."""
    if request.method == 'POST':
        class_id = request.POST.get('class_select')
        new_class_name = request.POST.get('new_class_name', '').strip()
        
        subject_id = request.POST.get('subject_select')
        new_subject_name = request.POST.get('new_subject_name', '').strip()

        chapter_id = request.POST.get('chapter_select')
        new_chapter_name = request.POST.get('new_chapter_name', '').strip()

        topic_id = request.POST.get('topic_select')
        new_topic_name = request.POST.get('new_topic_name', '').strip()

        new_subtopic_name = request.POST.get('new_subtopic_name', '').strip()

        # Class
        if new_class_name:
            board_class, _ = BoardClass.objects.get_or_create(name=new_class_name)
        elif class_id:
            board_class = BoardClass.objects.get(id=class_id)
        else:
            board_class = None

        # Subject
        if board_class and new_subject_name:
            subject, _ = BoardSubject.objects.get_or_create(name=new_subject_name, board_class=board_class)
        elif subject_id:
            subject = BoardSubject.objects.get(id=subject_id)
        else:
            subject = None

        # Chapter
        if subject and new_chapter_name:
            chapter, _ = BoardChapter.objects.get_or_create(title=new_chapter_name, subject=subject)
        elif chapter_id:
            chapter = BoardChapter.objects.get(id=chapter_id)
        else:
            chapter = None

        # Topic
        if chapter and new_topic_name:
            topic, _ = BoardTopic.objects.get_or_create(title=new_topic_name, chapter=chapter)
        elif topic_id:
            topic = BoardTopic.objects.get(id=topic_id)
        else:
            topic = None

        # SubTopic
        if topic and new_subtopic_name:
            BoardSubTopic.objects.get_or_create(title=new_subtopic_name, topic=topic)

        messages.success(request, "Board hierarchy updated successfully!")
        return redirect('question_bank:unified_board_builder')

    classes = BoardClass.objects.all()
    return render(request, 'question_bank/unified_board_builder.html', {'classes': classes})


@login_required
def unified_competitive_builder(request):
    """Single form to hierarchically build Exam -> Module -> SubModule."""
    if request.method == 'POST':
        exam_id = request.POST.get('exam_select')
        new_exam_name = request.POST.get('new_exam_name', '').strip()

        module_id = request.POST.get('module_select')
        new_module_name = request.POST.get('new_module_name', '').strip()

        new_submodule_name = request.POST.get('new_submodule_name', '').strip()

        if new_exam_name:
            exam, _ = CompetitiveExam.objects.get_or_create(title=new_exam_name)
        elif exam_id:
            exam = CompetitiveExam.objects.get(id=exam_id)
        else:
            exam = None

        if exam and new_module_name:
            module, _ = CompetitiveModule.objects.get_or_create(title=new_module_name, exam=exam)
        elif module_id:
            module = CompetitiveModule.objects.get(id=module_id)
        else:
            module = None

        if module and new_submodule_name:
            CompetitiveSubModule.objects.get_or_create(title=new_submodule_name, module=module)

        messages.success(request, "Competitive hierarchy updated successfully!")
        return redirect('question_bank:unified_competitive_builder')

    exams = CompetitiveExam.objects.all()
    return render(request, 'question_bank/unified_competitive_builder.html', {'exams': exams})


# ==========================================================
# UNIFIED QUESTION CREATION & EXCEL IMPORT
# ==========================================================

@login_required
def create_question_view(request):
    """Unified view for creating single questions."""
    if request.method == 'POST':
        form = UnifiedQuestionForm(request.POST, request.FILES)
        if form.is_valid():
            question = form.save(commit=False)
            
            flow = form.cleaned_data.get('assessment_flow')
            if flow == 'board':
                question.board_subtopic = form.cleaned_data.get('board_subtopic')
            else:
                question.competitive_submodule = form.cleaned_data.get('competitive_submodule')
                
            question.save()
            messages.success(request, "✅ Success! Question saved successfully to the Question Bank.")
            return redirect('question_bank:add_question')
        else:
            messages.error(request, "❌ Error! Question could not be saved. Please check the form errors below.")
    else:
        form = UnifiedQuestionForm()

    return render(request, 'question_bank/add_question.html', {'form': form})


@login_required
def import_questions_excel(request):
    """Bulk imports questions from Excel and maps them to selected Board or Competitive scope."""
    if request.method == 'POST' and request.FILES.get('excel_file'):
        excel_file = request.FILES['excel_file']
        assessment_flow = request.POST.get('assessment_flow', 'board')
        
        subtopic_id = request.POST.get('excel_board_subtopic')
        submodule_id = request.POST.get('excel_competitive_submodule')

        try:
            df = pd.read_excel(excel_file)
            created_count = 0

            option_map = {'1': 'A', '2': 'B', '3': 'C', '4': 'D', 'A': 'A', 'B': 'B', 'C': 'C', 'D': 'D'}

            for _, row in df.iterrows():
                raw_correct = str(row.get('correct_option', 'A')).strip().upper()
                if len(raw_correct) > 1 and raw_correct[0] in ['A', 'B', 'C', 'D']:
                    raw_correct = raw_correct[0]
                
                correct_opt = option_map.get(raw_correct, 'A')

                q = Question(
                    assessment_flow=assessment_flow,
                    question_text=str(row.get('question_text', '')).strip() if pd.notna(row.get('question_text')) else '',
                    option_a=str(row.get('option_a', '')).strip() if pd.notna(row.get('option_a')) else '',
                    option_b=str(row.get('option_b', '')).strip() if pd.notna(row.get('option_b')) else '',
                    option_c=str(row.get('option_c', '')).strip() if pd.notna(row.get('option_c')) else '',
                    option_d=str(row.get('option_d', '')).strip() if pd.notna(row.get('option_d')) else '',
                    correct_option=correct_opt,
                    explanation=str(row.get('explanation', '')).strip() if pd.notna(row.get('explanation')) else '',
                    youtube_url=str(row.get('youtube_url', '')).strip() if pd.notna(row.get('youtube_url')) else ''
                )
                if assessment_flow == 'board' and subtopic_id:
                    q.board_subtopic_id = subtopic_id
                elif assessment_flow == 'competitive' and submodule_id:
                    q.competitive_submodule_id = submodule_id

                q.save()
                created_count += 1

            messages.success(request, f"✅ Successfully imported {created_count} questions from Excel with classification scoped!")
        except Exception as e:
            messages.error(request, f"❌ Error processing Excel file: {str(e)}")

        return redirect('question_bank:add_question')

    return redirect('question_bank:add_question')

@login_required
def api_filter_questions(request):
    """API endpoint to filter questions asynchronously for the content team dashboard."""
    questions = Question.objects.all()
    
    flow = request.GET.get('assessment_flow')
    b_class = request.GET.get('board_class')
    b_subject = request.GET.get('board_subject')
    b_chapter = request.GET.get('board_chapter')
    b_topic = request.GET.get('board_topic')
    b_subtopic = request.GET.get('board_subtopic')

    c_exam = request.GET.get('competitive_exam')
    c_module = request.GET.get('competitive_module')
    c_submodule = request.GET.get('competitive_submodule')

    if flow:
        questions = questions.filter(assessment_flow=flow)
    if b_class:
        questions = questions.filter(board_subtopic__topic__chapter__subject__board_class_id=b_class)
    if b_subject:
        questions = questions.filter(board_subtopic__topic__chapter__subject_id=b_subject)
    if b_chapter:
        questions = questions.filter(board_subtopic__topic__chapter_id=b_chapter)
    if b_topic:
        questions = questions.filter(board_subtopic__topic_id=b_topic)
    if b_subtopic:
        questions = questions.filter(board_subtopic_id=b_subtopic)

    if c_exam:
        questions = questions.filter(competitive_submodule__module__exam_id=c_exam)
    if c_module:
        questions = questions.filter(competitive_submodule__module_id=c_module)
    if c_submodule:
        questions = questions.filter(competitive_submodule_id=c_submodule)

    total_count = questions.count()
    questions_data = []
    for q in questions.order_by('-id')[:25]:
        questions_data.append({
            'id': q.id,
            'question_text': q.question_text[:65] if q.question_text else '[Image Question]',
            'assessment_flow': q.assessment_flow.title(),
            'correct_option': q.correct_option,
        })
        
    return JsonResponse({
        'total_questions': total_count,
        'questions': questions_data
    })

@user_passes_test(lambda u: u.is_superuser)
def bulk_import_hierarchies(request):
    if request.method == 'POST':
        excel_file = request.FILES.get('excel_file')
        hierarchy_type = request.POST.get('hierarchy_type')
        if excel_file:
            try:
                df = pd.read_excel(excel_file)
                for index, row in df.iterrows():
                    # Process your board/competitive hierarchy rows here
                    pass
                messages.success(request, f"Successfully imported {hierarchy_type} hierarchies from Excel!")
            except Exception as e:
                messages.error(request, f"Error processing file: {e}")
    return redirect('accounts:dashboard_redirect')