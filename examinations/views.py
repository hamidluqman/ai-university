import random
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.db.models import Avg, Count
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from io import BytesIO
from accounts.decorators import role_required
from django.db import models


from .models import Exam, ExamAttempt, StudentAnswer, RetestPermission
from .forms import ExamCreationForm
from .services import student_can_access_exam, get_available_exams
from question_bank.models import Question, BoardTopic, BoardSubTopic, BoardClass, BoardSubject, CompetitiveSubModule

def get_filtered_question_queryset(exam):
    queryset = Question.objects.all()
    if exam.assessment_flow == 'board':
        if exam.scope_level == 'subtopic' and exam.board_subtopic_id:
            queryset = queryset.filter(board_subtopic_id=exam.board_subtopic_id, competitive_submodule__isnull=True)
        elif exam.scope_level == 'topic' and exam.board_topic_id:
            queryset = queryset.filter(board_subtopic__topic_id=exam.board_topic_id, competitive_submodule__isnull=True)
        elif exam.scope_level == 'subject':
            subject_id = exam.board_subject_id
            if not subject_id and exam.board_topic_id:
                try:
                    top_obj = BoardTopic.objects.get(pk=exam.board_topic_id)
                    subject_id = top_obj.chapter.subject_id
                except BoardTopic.DoesNotExist:
                    subject_id = exam.board_topic_id
            if subject_id:
                queryset = queryset.filter(board_subtopic__topic__chapter__subject_id=subject_id, competitive_submodule__isnull=True)
    elif exam.assessment_flow == 'competitive':
        if exam.scope_level == 'subtopic' and exam.competitive_submodule_id:
            queryset = queryset.filter(competitive_submodule_id=exam.competitive_submodule_id, board_subtopic__isnull=True)
        elif exam.scope_level in ['topic', 'subject'] and exam.competitive_module_id:
            queryset = queryset.filter(competitive_submodule__module_id=exam.competitive_module_id, board_subtopic__isnull=True)
    return queryset

def assign_questions_to_exam(exam):
    pool = list(get_filtered_question_queryset(exam))
    if pool:
        selected = random.sample(pool, min(len(pool), exam.total_questions))
        exam.questions.set(selected)

@login_required
def ajax_load_topics(request):
    subject_id = request.GET.get('subject_id')
    topics = BoardTopic.objects.filter(chapter__subject_id=subject_id).values('id', 'title')
    return JsonResponse(list(topics), safe=False)

@login_required
def ajax_load_subtopics(request):
    topic_id = request.GET.get('topic_id')
    subtopics = BoardSubTopic.objects.filter(topic_id=topic_id).values('id', 'title')
    return JsonResponse(list(subtopics), safe=False)

@login_required
def create_exam_view(request):
    if request.method == 'POST':
        form = ExamCreationForm(request.POST, user=request.user)
        if form.is_valid():
            exam = form.save(commit=False)
            exam.creator = request.user
            
            teacher_profile = getattr(request.user, 'teacher_profile', getattr(request.user, 'profile', None))
            inst = getattr(teacher_profile, 'institution', None) if teacher_profile else None
            if not inst and hasattr(request.user, 'institution'):
                inst = request.user.institution
                
            exam.institution = inst
            exam.save()
            assign_questions_to_exam(exam)
            messages.success(request, "Institution assessment created successfully!")
            return redirect('accounts:dashboard_redirect')
    else:
        form = ExamCreationForm(user=request.user)
    return render(request, 'examinations/create_exam.html', {'form': form})

@login_required
def take_exam_view(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    student_profile = getattr(request.user, 'student_profile', getattr(request.user, 'profile', None))
    
    # Check if a retest parameter was passed to allow clearing prior attempts
    is_retest = request.GET.get('retest') == 'true'
    if is_retest and exam.exam_type != 'practice':
        ExamAttempt.objects.filter(student=request.user, exam=exam).delete()

    if exam.exam_type != 'practice':
        existing_attempt = ExamAttempt.objects.filter(student=request.user, exam=exam).first()
        if existing_attempt:
            return redirect('examinations:exam_result', attempt_id=existing_attempt.id)

    if exam.institution and student_profile:
        if getattr(student_profile, 'institution', None) != exam.institution:
            return render(request, 'examinations/exam_locked.html')

    if not student_can_access_exam(student_profile, exam):
        return render(request, 'examinations/exam_locked.html')

    # STRICT FLOW-BASED QUESTION ISOLATION
    if exam.assessment_flow == 'competitive':
        if exam.competitive_submodule_id:
            questions = Question.objects.filter(competitive_submodule_id=exam.competitive_submodule_id).exclude(board_subtopic__isnull=False)
        elif exam.competitive_module_id:
            questions = Question.objects.filter(competitive_submodule__module_id=exam.competitive_module_id).exclude(board_subtopic__isnull=False)
        else:
            questions = exam.questions.filter(competitive_submodule__isnull=False, board_subtopic__isnull=True)
    elif exam.assessment_flow == 'board':
        if exam.board_subtopic_id:
            questions = Question.objects.filter(board_subtopic_id=exam.board_subtopic_id).exclude(competitive_submodule__isnull=False)
        else:
            questions = exam.questions.filter(board_subtopic__isnull=False, competitive_submodule__isnull=True)
    else:
        questions = exam.questions.all()

    total_duration_seconds = questions.count() * 20
    
    if request.method == 'POST':
        if exam.exam_type != 'practice' and ExamAttempt.objects.filter(student=request.user, exam=exam).exists():
            messages.error(request, "You have already submitted this exam.")
            return redirect('accounts:dashboard_redirect')

        score = 0
        total_marks = questions.count()
        attempt = ExamAttempt.objects.create(
            student=request.user,
            exam=exam,
            total_marks=total_marks,
            is_practice=(exam.exam_type == 'practice')
        )
        
        for q in questions:
            selected_option = request.POST.get(f'question_{q.id}')
            is_correct = (selected_option == q.correct_option) if selected_option else False
            if is_correct:
                score += 1
            StudentAnswer.objects.create(
                attempt=attempt,
                question=q,
                selected_option=selected_option,
                is_correct=is_correct
            )
            
        percentage = (score / total_marks * 100) if total_marks > 0 else 0.0
        attempt.score = score
        attempt.percentage = percentage
        attempt.is_passed = percentage >= exam.passing_percentage
        attempt.save()
        
        return redirect('examinations:exam_result', attempt_id=attempt.id)
        
    return render(request, 'examinations/take_exam.html', {
        'exam': exam, 
        'questions': questions,
        'total_duration_seconds': total_duration_seconds
    })

@login_required
def exam_result_view(request, attempt_id):
    user = request.user
    is_teacher_or_staff = (
        user.is_superuser or 
        getattr(user, 'role', None) in ['superadmin', 'institution_admin', 'teacher', 'content_team'] or 
        hasattr(user, 'teacher_profile')
    )
    
    if is_teacher_or_staff:
        attempt = get_object_or_404(ExamAttempt, id=attempt_id)
    else:
        attempt = get_object_or_404(ExamAttempt, id=attempt_id, student=user)
        
    answers = attempt.answers.select_related('question').all()
    return render(request, 'examinations/exam_result.html', {
        'attempt': attempt,
        'answers': answers
    })

@login_required
def exam_remedial_videos_view(request, attempt_id):
    user = request.user
    is_teacher_or_staff = (
        user.is_superuser or 
        getattr(user, 'role', None) in ['superadmin', 'institution_admin', 'teacher', 'content_team'] or 
        hasattr(user, 'teacher_profile')
    )
    
    if is_teacher_or_staff:
        attempt = get_object_or_404(ExamAttempt, id=attempt_id)
    else:
        attempt = get_object_or_404(ExamAttempt, id=attempt_id, student=user)

    wrong_answers = attempt.answers.select_related('question').filter(
        is_correct=False, 
        question__youtube_url__isnull=False
    ).exclude(question__youtube_url='')
    
    return render(request, 'examinations/youtube_player.html', {
        'attempt': attempt,
        'wrong_answers': wrong_answers
    })

@login_required
def results_dashboard(request):
    user = request.user
    
    is_teacher_or_staff = (
        user.is_superuser or 
        getattr(user, 'role', None) in ['superadmin', 'institution_admin', 'teacher', 'content_team'] or 
        hasattr(user, 'teacher_profile')
    )
    
    class_id = request.GET.get('class_id')
    subject_id = request.GET.get('subject_id')
    
    board_classes = BoardClass.objects.filter(is_active=True)
    board_subjects = BoardSubject.objects.filter(is_active=True)
    if class_id:
        board_subjects = board_subjects.filter(board_class_id=class_id)
    
    if is_teacher_or_staff:
        teacher_profile = getattr(user, 'teacher_profile', getattr(user, 'profile', None))
        inst = getattr(teacher_profile, 'institution', None) if teacher_profile else None
        if not inst and hasattr(user, 'institution'):
            inst = user.institution
            
        if inst:
            available_exams = Exam.objects.filter(institution=inst).order_by('-id')
        else:
            available_exams = Exam.objects.filter(creator=user).order_by('-id')
            
        if subject_id:
            available_exams = available_exams.filter(board_subject_id=subject_id)
            
        attempts = ExamAttempt.objects.filter(exam__in=available_exams).order_by('-submitted_at')
        
        if class_id:
            student_ids = []
            for att in attempts:
                s_profile = getattr(att.student, 'student_profile', getattr(att.student, 'profile', None))
                if s_profile and getattr(s_profile, 'board_class_id', None) == int(class_id):
                    student_ids.append(att.student.id)
            attempts = attempts.filter(student_id__in=student_ids)
    else:
        attempts = ExamAttempt.objects.filter(student=user).order_by('-submitted_at')
        student_profile = getattr(user, 'student_profile', getattr(user, 'profile', None))
        inst = getattr(student_profile, 'institution', None) if student_profile else None
        if not inst and hasattr(user, 'institution'):
            inst = user.institution
            
        if inst:
            available_exams = Exam.objects.filter(institution=inst).order_by('-id')
        else:
            available_exams = Exam.objects.none()

    return render(request, 'examinations/results_dashboard.html', {
        'attempts': attempts, 
        'created_exams': available_exams,
        'is_teacher': is_teacher_or_staff,
        'board_classes': board_classes,
        'board_subjects': board_subjects,
        'selected_class': class_id,
        'selected_subject': subject_id,
    })

@login_required
def official_exams_view(request):
    student_profile = getattr(request.user, 'student_profile', getattr(request.user, 'profile', None))
    inst = getattr(student_profile, 'institution', None) if student_profile else None
    if not inst and hasattr(request.user, 'institution'):
        inst = request.user.institution
    
    exams_data = []
    if inst:
        exams = Exam.objects.filter(institution=inst).order_by('-id')
        for exam in exams:
            attempt = ExamAttempt.objects.filter(student=request.user, exam=exam).first()
            exams_data.append({
                'exam': exam,
                'has_attempted': attempt is not None,
                'latest_attempt_id': attempt.id if attempt else None
            })
    
    return render(request, 'examinations/official_exams.html', {'exams_data': exams_data})

@login_required
def teacher_exams_view(request):
    now = timezone.now()
    exams_data = []
    exams = Exam.objects.filter(creator=request.user).order_by('-id')
    
    for exam in exams:
        has_ended = exam.end_time and exam.end_time < now
        has_attempts = ExamAttempt.objects.filter(exam=exam).exists()
        is_completed = has_ended or has_attempts
        
        exams_data.append({
            'exam': exam,
            'is_completed': is_completed
        })
        
    return render(request, 'examinations/teacher_exams.html', {'exams_data': exams_data})

@login_required
def grant_retest_view(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id, creator=request.user)
    if request.method == 'POST':
        RetestPermission.objects.create(exam=exam, granted_by=request.user, is_for_entire_class=True)
        messages.success(request, "Retest granted for the entire class.")
        return redirect('accounts:dashboard_redirect')
    return render(request, 'examinations/grant_retest.html', {'exam': exam})

@login_required
def download_results_pdf(request):
    attempts = ExamAttempt.objects.filter(student=request.user)
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    p.drawString(50, height - 50, f"Exam Results Report - {request.user.username}")
    y = height - 90
    for att in attempts:
        p.drawString(50, y, f"Exam: {att.exam.title} | Score: {att.score}/{att.total_marks} ({att.percentage:.1f}%)")
        y -= 25
        if y < 50:
            p.showPage()
            y = height - 50
    p.save()
    buffer.seek(0)
    return HttpResponse(buffer, content_type='application/pdf')

@login_required
def download_teacher_results_pdf(request):
    user = request.user
    is_teacher_or_staff = (
        user.is_superuser or 
        getattr(user, 'role', None) in ['superadmin', 'institution_admin', 'teacher', 'content_team'] or 
        hasattr(user, 'teacher_profile')
    )
    if not is_teacher_or_staff:
        return HttpResponse("Unauthorized", status=403)
    
    class_id = request.GET.get('class_id')
    subject_id = request.GET.get('subject_id')
    
    teacher_profile = getattr(user, 'teacher_profile', getattr(user, 'profile', None))
    inst = getattr(teacher_profile, 'institution', None) if teacher_profile else None
    if not inst and hasattr(user, 'institution'):
        inst = user.institution
        
    if inst:
        available_exams = Exam.objects.filter(institution=inst)
    else:
        available_exams = Exam.objects.filter(creator=user)
        
    if subject_id:
        available_exams = available_exams.filter(board_subject_id=subject_id)
        
    attempts = ExamAttempt.objects.filter(exam__in=available_exams).order_by('exam__title', '-submitted_at')
    
    if class_id:
        filtered_attempts = []
        for att in attempts:
            s_profile = getattr(att.student, 'student_profile', getattr(att.student, 'profile', None))
            if s_profile and getattr(s_profile, 'board_class_id', None) == int(class_id):
                filtered_attempts.append(att)
        attempts = filtered_attempts
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elements = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'ReportTitle',
        parent=styles['Heading1'],
        fontSize=15,
        textColor=colors.HexColor('#1a365d'),
        spaceAfter=4
    )
    meta_style = ParagraphStyle(
        'ReportMeta',
        parent=styles['Normal'],
        fontSize=8.5,
        textColor=colors.HexColor('#4a5568'),
        spaceAfter=12
    )
    
    elements.append(Paragraph(f"Institution & Class Performance Report - {inst.name if inst else user.username}", title_style))
    elements.append(Paragraph(f"Filters -> Class ID: {class_id or 'All'} | Subject ID: {subject_id or 'All'} | Generated: {timezone.now().strftime('%Y-%m-%d %H:%M')}", meta_style))
    
    table_data = [
        ["Student Name", "Exam Title", "Score", "%", "Status", "Submitted At"]
    ]
    
    for att in attempts:
        student_name = att.student.get_full_name() or att.student.username
        status = "Passed" if att.is_passed else "Failed"
        sub_date = att.submitted_at.strftime('%Y-%m-%d %H:%M') if att.submitted_at else "N/A"
        table_data.append([
            student_name,
            att.exam.title,
            f"{att.score}/{att.total_marks}",
            f"{att.percentage:.1f}%",
            status,
            sub_date
        ])
        
    t = Table(table_data, colWidths=[120, 155, 55, 45, 55, 125])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2b6cb0')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('TOPPADDING', (0,0), (-1,0), 6),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f7fafc')]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e0')),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,1), (-1,-1), 8),
        ('BOTTOMPADDING', (0,1), (-1,-1), 5),
        ('TOPPADDING', (0,1), (-1,-1), 5),
    ]))
    
    elements.append(t)
    doc.build(elements)
    buffer.seek(0)
    return HttpResponse(buffer, content_type='application/pdf')

@login_required
def class_performance_analytics_api(request):
    user = request.user
    is_teacher_or_staff = (
        user.is_superuser or 
        getattr(user, 'role', None) in ['superadmin', 'institution_admin', 'teacher', 'content_team'] or 
        hasattr(user, 'teacher_profile')
    )
    if not is_teacher_or_staff:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    teacher_profile = getattr(user, 'teacher_profile', getattr(user, 'profile', None))
    inst = getattr(teacher_profile, 'institution', None) if teacher_profile else None
    if not inst and hasattr(user, 'institution'):
        inst = user.institution

    exams = Exam.objects.filter(institution=inst) if inst else Exam.objects.filter(creator=user)
    attempts = ExamAttempt.objects.filter(exam__in=exams)

    total_attempts = attempts.count()
    passed_attempts = attempts.filter(is_passed=True).count()
    failed_attempts = total_attempts - passed_attempts
    avg_percentage = attempts.aggregate(Avg('percentage'))['percentage__avg'] or 0.0

    exam_breakdown = list(
        attempts.values('exam__title').annotate(
            total=Count('id'),
            avg_score=Avg('score'),
            avg_percentage=Avg('percentage')
        ).order_by('-submitted_at')
    )

    data = {
        "summary": {
            "total_attempts": total_attempts,
            "passed_attempts": passed_attempts,
            "failed_attempts": failed_attempts,
            "pass_rate": (passed_attempts / total_attempts * 100) if total_attempts > 0 else 0.0,
            "average_percentage": round(avg_percentage, 2)
        },
        "exam_breakdown": exam_breakdown
    }
    return JsonResponse(data)

@login_required
def topic_weakness_analytics_api(request):
    user = request.user
    is_teacher_or_staff = (
        user.is_superuser or 
        getattr(user, 'role', None) in ['superadmin', 'institution_admin', 'teacher', 'content_team'] or 
        hasattr(user, 'teacher_profile')
    )
    if not is_teacher_or_staff:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    teacher_profile = getattr(user, 'teacher_profile', getattr(user, 'profile', None))
    inst = getattr(teacher_profile, 'institution', None) if teacher_profile else None
    if not inst and hasattr(user, 'institution'):
        inst = user.institution

    exams = Exam.objects.filter(institution=inst) if inst else Exam.objects.filter(creator=user)
    answers = StudentAnswer.objects.filter(attempt__exam__in=exams)

    topic_stats = {}
    for ans in answers.select_related('question__board_subtopic__topic'):
        q = ans.question
        if q.board_subtopic and q.board_subtopic.topic:
            topic_name = q.board_subtopic.topic.title
            if topic_name not in topic_stats:
                topic_stats[topic_name] = {"total": 0, "incorrect": 0}
            topic_stats[topic_name]["total"] += 1
            if not ans.is_correct:
                topic_stats[topic_name]["incorrect"] += 1

    formatted_stats = []
    for topic, stats in topic_stats.items():
        error_rate = (stats["incorrect"] / stats["total"] * 100) if stats["total"] > 0 else 0.0
        formatted_stats.append({
            "topic": topic,
            "total_answers": stats["total"],
            "incorrect_answers": stats["incorrect"],
            "error_rate": round(error_rate, 2)
        })

    formatted_stats.sort(key=lambda x: x["error_rate"], reverse=True)
    return JsonResponse({"topic_weaknesses": formatted_stats}, safe=False)

@login_required
def delete_exam_view(request, exam_id):
    """Allows creators or authorized staff to delete an exam assessment."""
    exam = get_object_or_404(Exam, pk=exam_id)
    user = request.user
    
    is_authorized = (
        user.is_superuser or 
        exam.creator == user or 
        user.role in ['superadmin', 'institution_admin']
    )
    
    if not is_authorized:
        messages.error(request, "You do not have permission to delete this test.")
        return redirect('accounts:dashboard_redirect')

    if request.method == 'POST':
        title = exam.title
        exam.delete()
        messages.success(request, f"Assessment '{title}' deleted successfully!")
        
    return redirect('accounts:dashboard_redirect')

@login_required
def student_practice_setup_view(request, subtopic_id=None):
    subtopic = None
    if subtopic_id:
        subtopic = get_object_or_404(BoardSubTopic, pk=subtopic_id)

    if request.method == 'POST':
        target_subtopic_id = request.POST.get('board_subtopic') or subtopic_id
        questions = Question.objects.filter(board_subtopic_id=target_subtopic_id)
        
        score = None
        total_questions = questions.count()
        user_answers = {}
        correct_count = 0

        for q in questions:
            selected_option = request.POST.get(f'question_{q.id}')
            user_answers[q.id] = selected_option
            if selected_option and str(selected_option).strip() == str(getattr(q, 'correct_option', '')).strip():
                correct_count += 1
        
        score = {
            'correct': correct_count,
            'total': total_questions,
            'percentage': (correct_count / total_questions * 100) if total_questions > 0 else 0
        }

        context = {
            'subtopic': subtopic,
            'questions': questions,
            'score': score,
            'user_answers': user_answers,
        }
        return render(request, 'examinations/practice_results.html', context)

    context = {
        'subtopic': subtopic,
    }
    return render(request, 'examinations/practice_setup.html', context)

@login_required
def start_subtopic_practice_view(request, subtopic_id):
    subtopic = get_object_or_404(BoardSubTopic, pk=subtopic_id)
    questions = Question.objects.filter(board_subtopic=subtopic)
    
    score = None
    user_answers = {}

    if request.method == 'POST':
        correct_count = 0
        total_questions = questions.count()
        for q in questions:
            selected_option = request.POST.get(f'question_{q.id}')
            user_answers[q.id] = selected_option
            if selected_option and str(selected_option).strip() == str(getattr(q, 'correct_option', '')).strip():
                correct_count += 1
        
        score = {
            'correct': correct_count,
            'total': total_questions,
            'percentage': (correct_count / total_questions * 100) if total_questions > 0 else 0
        }

    context = {
        'subtopic': subtopic,
        'questions': questions,
        'score': score,
        'user_answers': user_answers,
    }
    return render(request, 'examinations/practice_quiz.html', context)

@login_required
@role_required(['student', 'institution_admin', 'superadmin'])
def start_board_exam_for_topic(request, pk):
    subtopic = get_object_or_404(BoardSubTopic, pk=pk)
    exam = Exam.objects.filter(board_subtopic=subtopic).first()
    
    if not exam:
        exam = Exam.objects.create(
            title=f"Assessment: {subtopic.title}",
            assessment_flow='board',
            scope_level='subtopic',
            board_subtopic=subtopic,
            creator=request.user,
            total_questions=10,
            duration_minutes=30
        )
        matching_questions = Question.objects.filter(board_subtopic=subtopic, competitive_submodule__isnull=True).distinct()[:15]
        if matching_questions.exists():
            exam.questions.set(matching_questions)
            
    target_url = f"/examinations/take/{exam.id}/"
    if request.GET.get('retest') == 'true':
        target_url += "?retest=true"
    return redirect(target_url)

@login_required
@role_required(['student', 'institution_admin', 'superadmin'])
def start_competitive_exam_for_topic(request, pk):
    submodule = get_object_or_404(CompetitiveSubModule, pk=pk)
    exam = Exam.objects.filter(competitive_submodule=submodule).first()
    
    if not exam:
        exam = Exam.objects.create(
            title=f"Assessment: {submodule.title}",
            assessment_flow='competitive',
            scope_level='subtopic',
            competitive_submodule=submodule,
            creator=request.user,
            total_questions=10,
            duration_minutes=30
        )
        matching_questions = Question.objects.filter(competitive_submodule=submodule, board_subtopic__isnull=True).distinct()[:15]
        if matching_questions.exists():
            exam.questions.set(matching_questions)
            
    target_url = f"/examinations/take/{exam.id}/"
    if request.GET.get('retest') == 'true':
        target_url += "?retest=true"
    return redirect(target_url)

@login_required
def results_dashboard(request):
    user = request.user
    is_teacher_or_staff = (
        user.is_superuser or 
        getattr(user, 'role', None) in ['superadmin', 'institution_admin', 'teacher', 'content_team'] or 
        hasattr(user, 'teacher_profile')
    )
    
    if is_teacher_or_staff:
        # Teacher views code...
        pass
    else:
        # Independent or institutional student views their own attempts
        attempts = ExamAttempt.objects.filter(student=user).order_by('-submitted_at')

    return render(request, 'examinations/results_dashboard.html', {
        'attempts': attempts,
        'is_teacher': is_teacher_or_staff,
    })