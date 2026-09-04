from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from question_bank.models import Question
from .models import LessonProgress

@login_required
def courses_dashboard_view(request):
    """Restricts course access based on superadmin permissions and student active subscriptions"""
    selected_class = request.GET.get('class', '').strip()
    selected_subject = request.GET.get('subject', '').strip()
    selected_exam = request.GET.get('exam', '').strip()
    selected_module = request.GET.get('module', '').strip()
    search_query = request.GET.get('q', '').strip()

    video_questions = Question.objects.exclude(youtube_url__isnull=True).exclude(youtube_url='')

    if not request.user.is_superuser and not request.user.is_staff:
        allowed_classes = getattr(request.user, 'allowed_board_classes', None)
        allowed_exams = getattr(request.user, 'allowed_competitive_exams', None)

        if allowed_classes is not None or allowed_exams is not None:
            video_questions = video_questions.filter(
                Q(board_subtopic__topic__chapter__subject__board_class__in=allowed_classes) |
                Q(competitive_submodule__module__exam__in=allowed_exams)
            )

    if search_query:
        video_questions = video_questions.filter(
            Q(question_text__icontains=search_query) |
            Q(board_subtopic__title__icontains=search_query) |
            Q(competitive_submodule__title__icontains=search_query)
        )

    board_tree = {}
    comp_tree = {}
    
    available_classes = set()
    available_subjects = set()
    available_exams = set()
    available_modules = set()

    for q in video_questions:
        if q.board_subtopic_id:
            sub = q.board_subtopic
            topic = getattr(sub, 'topic', None)
            chapter = getattr(topic, 'chapter', None) if topic else None
            subject = getattr(chapter, 'subject', None) if chapter else None
            
            b_class = 'Class 9th'
            if subject:
                b_class = getattr(subject, 'board_class', None) or getattr(subject, 'class_name', None) or str(subject)
            elif chapter:
                b_class = getattr(chapter, 'board_class', None) or 'Board Class'

            subject_name = str(subject) if subject else 'General Subject'
            
            available_classes.add(str(b_class))
            available_subjects.add(subject_name)

            if selected_class and selected_class != str(b_class):
                continue
            if selected_subject and selected_subject != subject_name:
                continue

            chapter_name = str(chapter) if chapter else 'General Chapter'
            topic_name = str(topic) if topic else 'General Topic'
            subtopic_name = getattr(sub, 'title', None) or str(sub)
            subtopic_id = sub.id

            board_tree.setdefault(str(b_class), {}).setdefault(subject_name, {}).setdefault(chapter_name, {}).setdefault(topic_name, {})[(subtopic_name, subtopic_id)] = \
                board_tree.setdefault(str(b_class), {}).setdefault(subject_name, {}).setdefault(chapter_name, {}).setdefault(topic_name, {}).get((subtopic_name, subtopic_id), []) + [q]
            
        elif q.competitive_submodule_id:
            submod = q.competitive_submodule
            module = getattr(submod, 'module', None)
            exam = getattr(module, 'exam', None) if module else 'ISSB'
            
            exam_name = str(exam) if exam else 'Competitive Exam'
            module_name = str(module) if module else 'General Module'

            available_exams.add(exam_name)
            available_modules.add(module_name)

            if selected_exam and selected_exam != exam_name:
                continue
            if selected_module and selected_module != module_name:
                continue

            submodule_name = str(submod)
            submodule_id = submod.id

            comp_tree.setdefault(exam_name, {}).setdefault(module_name, {})[(submodule_name, submodule_id)] = \
                comp_tree.setdefault(exam_name, {}).setdefault(module_name, {}).get((submodule_name, submodule_id), []) + [q]

    progress_records = LessonProgress.objects.filter(student=request.user).order_by('-completed_at')

    context = {
        'board_tree': board_tree,
        'comp_tree': comp_tree,
        'progress_records': progress_records,
        'available_classes': sorted(list(available_classes)),
        'available_subjects': sorted(list(available_subjects)),
        'available_exams': sorted(list(available_exams)),
        'available_modules': sorted(list(available_modules)),
        'selected_class': selected_class,
        'selected_subject': selected_subject,
        'selected_exam': selected_exam,
        'selected_module': selected_module,
        'search_query': search_query,
    }
    return render(request, 'courses/dashboard.html', context)


@login_required
def course_player_view(request, category, node_id):
    """Streams video lectures securely"""
    if category == 'board':
        lessons = Question.objects.filter(board_subtopic_id=node_id).exclude(youtube_url__isnull=True).exclude(youtube_url='')
    else:
        lessons = Question.objects.filter(competitive_submodule_id=node_id).exclude(youtube_url__isnull=True).exclude(youtube_url='')

    context = {
        'course_title': "Video Lectures",
        'lessons': lessons,
        'category': category,
    }
    return render(request, 'courses/course_player.html', context)


@login_required
@require_POST
def update_progress_ajax(request, question_id):
    """Asynchronously marks a lesson progress record as completed"""
    try:
        question = Question.objects.get(pk=question_id)
        progress, created = LessonProgress.objects.get_or_create(
            student=request.user,
            question=question
        )
        progress.is_completed = True
        progress.save()
        return JsonResponse({'status': 'success', 'message': 'Progress saved successfully.'})
    except Question.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Question not found.'}, status=404)