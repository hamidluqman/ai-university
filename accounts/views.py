from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.db import transaction, models
from .forms import (
    ContentTeamCreationForm,
    TeacherCreationForm,
    StudentCreationForm,
    InstitutionWithAdminCreationForm,
)
from datetime import timedelta, date
from .models import User, TeacherProfile, StudentProfile
from .decorators import role_required
from institutions.models import Institution
from subscriptions.models import SubscriptionPlan, Subscription
from question_bank.models import Question, BoardClass, BoardSubject
from examinations.models import Exam, ExamAttempt
from django.db.models import Avg, Count

def is_admin_or_superadmin(user):
    return user.is_superuser or user.role in ['superadmin', 'institution_admin']


def get_user_institution(user):
    """Helper to extract institution for InstitutionAdmin profiles."""
    if user.role == 'institution_admin' and hasattr(user, 'institution_admin_profile'):
        return user.institution_admin_profile.institution
    return None


def get_institution_subscription(institution):
    """Safely retrieves the active subscription for an institution regardless of relationship type."""
    if not institution:
        return None
    if hasattr(institution, 'subscription') and not hasattr(institution.subscription, 'model'):
        return institution.subscription
    if hasattr(institution, 'subscriptions'):
        return institution.subscriptions.order_by('-id').first()
    if hasattr(institution, 'subscription_set'):
        return institution.subscription_set.order_by('-id').first()
    return Subscription.objects.filter(institution=institution).order_by('-id').first()


@login_required
def dashboard_redirect(request):
    user = request.user
    
    if user.is_superuser or getattr(user, 'role', None) == "superadmin":
        context = {
            'institutions_count': Institution.objects.count(),
            'independent_students_count': StudentProfile.objects.count(),
            'active_subscriptions_count': Subscription.objects.filter(is_active=True).count(),
            'pending_payments': Subscription.objects.filter(payment_status__iexact='pending'),
        }
        return render(request, "dashboard/superadmin.html", context)
        
    # Check Teacher subscription status
    if getattr(user, 'role', None) == "teacher" or hasattr(user, 'teacher_profile'):
        teacher_profile = getattr(user, 'teacher_profile', None)
        inst = teacher_profile.institution if teacher_profile else None
        if inst:
            sub = get_institution_subscription(inst)
            if sub and not sub.is_active:
                return render(request, "dashboard/pending_approval.html", {'message': 'Your institution subscription is pending superadmin approval. Staff access will be enabled once verified.'})
        return teacher_dashboard(request)
        
    if getattr(user, 'role', None) == "institution_admin" or hasattr(user, 'institution_admin_profile'):
        inst = get_user_institution(user)
        sub = get_institution_subscription(inst)
        if sub and not sub.is_active:
            return render(request, "dashboard/pending_approval.html", {'message': 'Your institution subscription is pending superadmin approval.'})
        return institution_dashboard_view(request)
        
    if getattr(user, 'role', None) == "content_team":
        return content_team_dashboard(request)
        
    if hasattr(user, 'student_profile'):
        student_profile = user.student_profile
        if student_profile.student_type == 'institutional':
            inst = student_profile.institution
            sub = get_institution_subscription(inst)
            if sub and not sub.is_active:
                return render(request, "dashboard/pending_approval.html", {'message': 'Your institution subscription is pending approval.'})
            return institutional_student_dashboard(request)
        else:
            sub = Subscription.objects.filter(user=user).order_by('-id').first()
            if not sub or not sub.is_active or sub.payment_status.lower() != 'approved':
                return render(request, "dashboard/pending_approval.html", {'message': 'Your subscription is pending superadmin approval.'})
            return independent_student_dashboard(request)

    return teacher_dashboard(request)


@login_required
@role_required(['teacher', 'institution_admin', 'superadmin'])
def teacher_dashboard(request):
    user = request.user
    teacher_profile = getattr(user, 'teacher_profile', None)
    institution = teacher_profile.institution if teacher_profile else None
    
    assigned_classes = []
    assigned_subjects = []
    teacher_tests = []

    if teacher_profile:
        if hasattr(teacher_profile, 'assigned_classes'):
            assigned_classes = list(teacher_profile.assigned_classes.all())
        elif hasattr(teacher_profile, 'classes'):
            assigned_classes = list(teacher_profile.classes.all())

        if hasattr(teacher_profile, 'assigned_subjects'):
            assigned_subjects = list(teacher_profile.assigned_subjects.all())
        elif hasattr(teacher_profile, 'subjects'):
            assigned_subjects = list(teacher_profile.subjects.all())

        try:
            teacher_tests = Exam.objects.filter(creator=user)
        except Exception:
            teacher_tests = []

    context = {
        'teacher_profile': teacher_profile,
        'institution': institution,
        'assigned_classes': assigned_classes,
        'assigned_subjects': assigned_subjects,
        'teacher_tests': teacher_tests,
    }
    return render(request, "dashboard/teacher.html", context)


@login_required
@role_required(['student', 'institution_admin', 'superadmin'])
def institutional_student_dashboard(request):
    user = request.user
    student_profile = getattr(user, 'student_profile', None)
    
    if not student_profile or student_profile.student_type != 'institutional':
        messages.error(request, "Access restricted to institutional students.")
        return redirect('accounts:dashboard_redirect')

    if request.method == 'POST':
        phone = request.POST.get('phone_number')
        if phone:
            if hasattr(user, 'phone'):
                user.phone = phone
            elif hasattr(user, 'profile'):
                user.profile.phone_number = phone
                user.profile.save()

        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        if new_password:
            if new_password == confirm_password:
                user.set_password(new_password)
                messages.success(request, "Password updated successfully!")
            else:
                messages.error(request, "New passwords do not match.")

        user.save()
        messages.success(request, "Profile updated successfully!")
        return redirect('accounts:dashboard_redirect')

    institution = student_profile.institution
    assigned_classes = student_profile.assigned_classes.all()
    assigned_subjects = student_profile.assigned_subjects.all()

    courses = []
    if hasattr(student_profile, 'assigned_courses'):
        courses = student_profile.assigned_courses.all()
    elif assigned_subjects:
        courses = assigned_subjects

    assigned_exams = Exam.objects.filter(
        models.Q(institution=institution),
        models.Q(board_subject__in=assigned_subjects) | models.Q(board_subject__board_class__in=assigned_classes)
    ).distinct().order_by('-id')

    now = timezone.now()
    exams_data = []
    for exam in assigned_exams:
        attempt = ExamAttempt.objects.filter(student=user, exam=exam).first()
        
        start_time = getattr(exam, 'start_time', None)
        end_time = getattr(exam, 'end_time', None)
        
        is_scheduled = start_time and now < start_time
        is_expired = end_time and now > end_time

        exams_data.append({
            'exam': exam,
            'has_attempted': attempt is not None,
            'latest_attempt_id': attempt.id if attempt else None,
            'is_scheduled': is_scheduled,
            'is_expired': is_expired,
            'start_time': start_time,
        })

    attempts = ExamAttempt.objects.filter(student=user).select_related('exam', 'exam__board_subject').order_by('-submitted_at')

    subject_stats_map = {}
    weak_subjects = set()

    for att in attempts:
        subject = att.exam.board_subject
        subj_name = subject.name if subject else "General"
        
        if subj_name not in subject_stats_map:
            subject_stats_map[subj_name] = {'total_score': 0, 'total_max': 0, 'count': 0, 'percentages': []}
        
        subject_stats_map[subj_name]['count'] += 1
        subject_stats_map[subj_name]['percentages'].append(float(att.percentage))

    subject_stats = []
    for subj_name, data in subject_stats_map.items():
        avg_pct = sum(data['percentages']) / len(data['percentages']) if data['percentages'] else 0.0
        subject_stats.append({
            'subject_name': subj_name,
            'total_attempts': data['count'],
            'avg_percentage': avg_pct
        })
        if avg_pct < 50.0:
            weak_subjects.add(subj_name)

    weak_topics_hierarchy = {}
    try:
        from examinations.models import StudentAnswer
        wrong_answers = StudentAnswer.objects.filter(attempt__student=user, is_correct=False).select_related(
            'question', 'question__board_subtopic', 'question__board_subtopic__topic', 
            'question__board_subtopic__topic__chapter', 'question__board_subtopic__topic__chapter__subject'
        )
        for wa in wrong_answers:
            q = wa.question
            if q and hasattr(q, 'board_subtopic') and q.board_subtopic:
                subtopic = q.board_subtopic
                topic = getattr(subtopic, 'topic', None)
                chapter = getattr(topic, 'chapter', None)
                subject = getattr(chapter, 'subject', None)
                
                subj_name = subject.name if subject else (q.board_subject.name if hasattr(q, 'board_subject') and q.board_subject else "General")
                chap_title = f"Ch {chapter.chapter_number}: {chapter.title}" if chapter and hasattr(chapter, 'chapter_number') else (chapter.title if chapter else "General Chapter")
                topic_title = subtopic.title
                
                if subj_name not in weak_topics_hierarchy:
                    weak_topics_hierarchy[subj_name] = {}
                if chap_title not in weak_topics_hierarchy[subj_name]:
                    weak_topics_hierarchy[subj_name][chap_title] = set()
                weak_topics_hierarchy[subj_name][chap_title].add(topic_title)
    except Exception:
        pass

    formatted_weak_topics = {}
    for subj, chapters in weak_topics_hierarchy.items():
        formatted_weak_topics[subj] = {chap: list(tops) for chap, tops in chapters.items()}

    context = {
        'student_profile': student_profile,
        'institution': institution,
        'assigned_classes': assigned_classes,
        'assigned_subjects': assigned_subjects,
        'courses': courses,
        'exams_data': exams_data,
        'attempts': attempts,
        'subject_stats': subject_stats,
        'weak_subjects': list(weak_subjects),
        'weak_topics_hierarchy': formatted_weak_topics,
        'phone_number': getattr(user, 'phone', '') or getattr(getattr(user, 'profile', None), 'profile_number', ''),
    }
    return render(request, "dashboard/institutional_student.html", context)

@login_required
@role_required(['student', 'institution_admin', 'superadmin'])
def student_courses_view(request):
    user = request.user
    student_profile = getattr(user, 'student_profile', None)
    
    if not student_profile or student_profile.student_type != 'institutional':
        messages.error(request, "Access restricted to institutional students.")
        return redirect('accounts:dashboard_redirect')

    institution = student_profile.institution
    assigned_subjects = student_profile.assigned_subjects.all()

    courses = []
    if hasattr(student_profile, 'assigned_courses'):
        courses = student_profile.assigned_courses.all()
    elif assigned_subjects:
        courses = assigned_subjects

    context = {
        'student_profile': student_profile,
        'institution': institution,
        'courses': courses,
    }
    return render(request, "dashboard/student_courses.html", context)

@login_required
@role_required(['student', 'institution_admin', 'superadmin'])
def student_assessments_view(request):
    user = request.user
    student_profile = getattr(user, 'student_profile', None)
    
    if not student_profile or student_profile.student_type != 'institutional':
        messages.error(request, "Access restricted to institutional students.")
        return redirect('accounts:dashboard_redirect')

    institution = student_profile.institution
    assigned_classes = student_profile.assigned_classes.all()
    assigned_subjects = student_profile.assigned_subjects.all()

    assigned_exams = Exam.objects.filter(
        models.Q(institution=institution),
        models.Q(board_subject__in=assigned_subjects) | models.Q(board_subject__board_class__in=assigned_classes)
    ).distinct().order_by('-id')

    now = timezone.now()
    exams_data = []
    for exam in assigned_exams:
        attempt = ExamAttempt.objects.filter(student=user, exam=exam).first()
        
        start_time = getattr(exam, 'start_time', None)
        end_time = getattr(exam, 'end_time', None)
        
        is_scheduled = start_time and now < start_time
        is_expired = end_time and now > end_time

        exams_data.append({
            'exam': exam,
            'has_attempted': attempt is not None,
            'latest_attempt_id': attempt.id if attempt else None,
            'is_scheduled': is_scheduled,
            'is_expired': is_expired,
            'start_time': start_time,
        })

    context = {
        'student_profile': student_profile,
        'institution': institution,
        'exams_data': exams_data,
    }
    return render(request, "dashboard/student_assessments.html", context)

@login_required
@role_required(['student', 'institution_admin', 'superadmin'])
def student_results_view(request):
    user = request.user
    student_profile = getattr(user, 'student_profile', None)
    
    if not student_profile or student_profile.student_type != 'institutional':
        messages.error(request, "Access restricted to institutional students.")
        return redirect('accounts:dashboard_redirect')

    institution = student_profile.institution
    attempts = ExamAttempt.objects.filter(student=user).select_related('exam', 'exam__board_subject').order_by('-submitted_at')

    subject_stats_map = {}
    weak_subjects = set()

    for att in attempts:
        subject = att.exam.board_subject
        subj_name = subject.name if subject else "General"
        
        if subj_name not in subject_stats_map:
            subject_stats_map[subj_name] = {'total_score': 0, 'total_max': 0, 'count': 0, 'percentages': []}
        
        subject_stats_map[subj_name]['count'] += 1
        subject_stats_map[subj_name]['percentages'].append(float(att.percentage))

    subject_stats = []
    for subj_name, data in subject_stats_map.items():
        avg_pct = sum(data['percentages']) / len(data['percentages']) if data['percentages'] else 0.0
        subject_stats.append({
            'subject_name': subj_name,
            'total_attempts': data['count'],
            'avg_percentage': avg_pct
        })
        if avg_pct < 50.0:
            weak_subjects.add(subj_name)

    context = {
        'student_profile': student_profile,
        'institution': institution,
        'attempts': attempts,
        'subject_stats': subject_stats,
        'weak_subjects': list(weak_subjects),
    }
    return render(request, "dashboard/student_results.html", context)

@login_required
@role_required(['student', 'institution_admin', 'superadmin'])
def student_weak_topics_view(request):
    user = request.user
    student_profile = getattr(user, 'student_profile', None)
    
    if hasattr(user, 'role') and user.role not in ['student', 'institution_admin', 'superadmin']:
        messages.error(request, "Access restricted.")
        return redirect('accounts:dashboard_redirect')

    institution = student_profile.institution if student_profile else None
    attempts = ExamAttempt.objects.filter(student=user).select_related('exam', 'exam__board_subject')

    subject_stats_map = {}
    weak_subjects = set()

    for att in attempts:
        subject = att.exam.board_subject
        subj_name = subject.name if subject else "General"
        
        if subj_name not in subject_stats_map:
            subject_stats_map[subj_name] = {'percentages': []}
        subject_stats_map[subj_name]['percentages'].append(float(att.percentage))

    for subj_name, data in subject_stats_map.items():
        avg_pct = sum(data['percentages']) / len(data['percentages']) if data['percentages'] else 0.0
        if avg_pct < 50.0:
            weak_subjects.add(subj_name)

    weak_topics_hierarchy = {}
    try:
        from examinations.models import StudentAnswer
        wrong_answers = StudentAnswer.objects.filter(attempt__student=user, is_correct=False).select_related(
            'question', 'question__board_subtopic', 'question__board_subtopic__topic', 
            'question__board_subtopic__topic__chapter', 'question__board_subtopic__topic__chapter__subject'
        )
        for wa in wrong_answers:
            q = wa.question
            if q and hasattr(q, 'board_subtopic') and q.board_subtopic:
                subtopic = q.board_subtopic
                topic = getattr(subtopic, 'topic', None)
                chapter = getattr(topic, 'chapter', None)
                subject = getattr(chapter, 'subject', None)
                
                subj_name = subject.name if subject else (q.board_subject.name if hasattr(q, 'board_subject') and q.board_subject else "General")
                chap_title = f"Ch {chapter.chapter_number}: {chapter.title}" if chapter and hasattr(chapter, 'chapter_number') else (chapter.title if chapter else "General Chapter")
                topic_title = subtopic.title
                
                if subj_name not in weak_topics_hierarchy:
                    weak_topics_hierarchy[subj_name] = {}
                if chap_title not in weak_topics_hierarchy[subj_name]:
                    weak_topics_hierarchy[subj_name][chap_title] = set()
                weak_topics_hierarchy[subj_name][chap_title].add(topic_title)
    except Exception:
        pass

    formatted_weak_topics = {}
    for subj, chapters in weak_topics_hierarchy.items():
        formatted_weak_topics[subj] = {chap: list(tops) for chap, tops in chapters.items()}

    context = {
        'student_profile': student_profile,
        'institution': institution,
        'weak_subjects': list(weak_subjects),
        'weak_topics_hierarchy': formatted_weak_topics,
    }
    return render(request, "dashboard/student_weak_topics.html", context)


@login_required
@role_required(['teacher', 'institution_admin', 'superadmin'])
def class_roster_view(request, class_id):
    """
    Displays the roster of students for a specific class assigned to the teacher,
    checking direct class assignments and subject relationships.
    """
    user = request.user
    teacher_profile = getattr(user, 'teacher_profile', None)
    institution = teacher_profile.institution if teacher_profile else None
    
    board_class = get_object_or_404(BoardClass, pk=class_id)
    
    if user.role == 'teacher' and teacher_profile:
        if not teacher_profile.assigned_classes.filter(pk=board_class.pk).exists():
            messages.error(request, "You are not assigned to this class.")
            return redirect('accounts:dashboard_redirect')
            
    class_subjects = BoardSubject.objects.filter(board_class=board_class)
    
    students = StudentProfile.objects.filter(
        models.Q(assigned_classes=board_class) | 
        models.Q(assigned_subjects__in=class_subjects)
    ).distinct()

    if institution and user.role != 'superadmin':
        students = students.filter(institution=institution)
        
    subject_id = request.GET.get('subject_id')
    selected_subject = None
    if subject_id:
        selected_subject = get_object_or_404(BoardSubject, pk=subject_id)
        students = students.filter(assigned_subjects=selected_subject)

    context = {
        'board_class': board_class,
        'students': students.select_related('user'),
        'institution': institution,
        'assigned_subjects': teacher_profile.assigned_subjects.all() if teacher_profile else [],
        'selected_subject': selected_subject,
    }
    return render(request, 'dashboard/class_roster.html', context)


@login_required
@role_required(['teacher', 'institution_admin', 'superadmin'])
def exam_results_view(request, exam_id):
    """
    Displays assessment results for a specific exam, querying eligible students 
    based on the exam's board subject scope and institution, automatically marking 
    unattempted students as Absent.
    """
    exam = get_object_or_404(Exam, pk=exam_id)
    user = request.user
    
    if user.role == 'teacher' and exam.creator != user:
        teacher_profile = getattr(user, 'teacher_profile', None)
        if teacher_profile and exam.institution and teacher_profile.institution != exam.institution:
            messages.error(request, "You do not have permission to view these results.")
            return redirect('accounts:dashboard_redirect')

    students_query = StudentProfile.objects.select_related('user')
    
    if exam.institution:
        students_query = students_query.filter(institution=exam.institution)
        
    if exam.assessment_flow == 'board' and exam.board_subject:
        board_class = getattr(exam.board_subject, 'board_class', None)
        if board_class:
            students_query = students_query.filter(
                models.Q(assigned_subjects=exam.board_subject) | 
                models.Q(assigned_classes=board_class)
            ).distinct()
        else:
            students_query = students_query.filter(assigned_subjects=exam.board_subject)
    elif exam.assessment_flow == 'competitive' and exam.competitive_module:
        students_query = students_query.filter(competitive_exams=exam.competitive_module.exam)

    eligible_students = students_query.all()

    attempts = ExamAttempt.objects.filter(exam=exam).select_related('student')
    attempt_map = {attempt.student_id: attempt for attempt in attempts}

    report_rows = []
    for student_profile in eligible_students:
        student_user = student_profile.user
        attempt = attempt_map.get(student_user.id)
        
        if attempt:
            status = "Submitted"
            score_display = f"{attempt.score} / {attempt.total_marks} ({attempt.percentage}%)"
            is_passed = attempt.is_passed
            submitted_at = attempt.submitted_at
        else:
            status = "Absent"
            score_display = "-"
            is_passed = False
            submitted_at = None

        report_rows.append({
            'student': student_user,
            'profile': student_profile,
            'attempt': attempt,
            'status': status,
            'score_display': score_display,
            'is_passed': is_passed,
            'submitted_at': submitted_at,
        })

    context = {
        'exam': exam,
        'report_rows': report_rows,
        'total_students': len(report_rows),
        'submitted_count': len(attempt_map),
        'absent_count': len(report_rows) - len(attempt_map),
    }
    return render(request, 'dashboard/exam_results.html', context)


@login_required
@role_required(['institution_admin', 'superadmin'])
def user_management_hub(request):
    """
    Central hub listing institutions, teachers, students, and content team members.
    Applies multi-tenant scoping if logged in as an InstitutionAdmin.
    """
    inst = get_user_institution(request.user)
    is_institution_admin = bool(inst)
    
    if inst:
        teachers = TeacherProfile.objects.select_related('user', 'institution').filter(institution=inst)
        students = StudentProfile.objects.select_related('user', 'institution').filter(institution=inst)
        institutions = Institution.objects.filter(id=inst.id)
    else:
        teachers = TeacherProfile.objects.select_related('user', 'institution').all()
        students = StudentProfile.objects.select_related('user', 'institution').all()
        institutions = Institution.objects.all()

    content_team_members = User.objects.filter(role='content_team')

    context = {
        'institutions': institutions,
        'teachers': teachers,
        'students': students,
        'content_team_members': content_team_members,
        'is_institution_admin': is_institution_admin,
    }
    return render(request, 'accounts/user_hub.html', context)


@login_required
@role_required(['institution_admin', 'superadmin'])
def create_institution_view(request):
    """
    Creates a new institution record, its primary admin account, and securely
    links the selected or default institution subscription plan.
    """
    if request.method == 'POST':
        form = InstitutionWithAdminCreationForm(request.POST, request.FILES)
        raw_plan_id = request.POST.get('subscription_plan') or request.POST.get('plan')
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    target_institution, admin_user = form.save()

                    plan_id = None
                    if raw_plan_id:
                        try:
                            plan_id = int(raw_plan_id)
                        except (ValueError, TypeError):
                            plan_id = None

                    plan = None
                    if plan_id:
                        plan = SubscriptionPlan.objects.filter(
                            pk=plan_id, 
                            plan_type__in=['institution', 'institutional', 'INSTITUTION', 'INSTITUTIONAL', 'ORGANIZATION']
                        ).first()
                    
                    if not plan:
                        plan = SubscriptionPlan.objects.filter(
                            plan_type__in=['institution', 'institutional', 'INSTITUTION', 'INSTITUTIONAL', 'ORGANIZATION'], 
                            is_active=True
                        ).first()
                    
                    if not plan:
                        plan = SubscriptionPlan.objects.create(
                            name="Default Institution Plan",
                            plan_type='institution',
                            price=0.00,
                            duration_days=30,
                            is_active=True
                        )

                    if not plan or not plan.pk:
                        raise ValueError("Failed to resolve or create a valid SubscriptionPlan for this institution.")

                    Subscription.objects.filter(institution=target_institution).delete()
                    
                    Subscription.objects.create(
                        user=None,
                        institution=target_institution,
                        plan=plan,
                        payment_status='pending',
                        is_active=False
                    )

                messages.success(request, f"Institution '{target_institution.name}' and subscription plan linked successfully!")
                return redirect('accounts:user_management_hub')
            except Exception as e:
                messages.error(request, f"Subscription Link Error: {str(e)}")
        else:
            messages.error(request, "Please correct the form errors below.")
    else:
        form = InstitutionWithAdminCreationForm()
        
    institution_plans = SubscriptionPlan.objects.filter(
        plan_type__in=['institution', 'institutional', 'INSTITUTION', 'INSTITUTIONAL', 'ORGANIZATION'], 
        is_active=True
    )
    return render(request, 'accounts/create_form.html', {
        'form': form, 
        'title': 'Add New Institution & Admin Account',
        'subscription_plans': institution_plans
    })


@login_required
@role_required(['institution_admin', 'superadmin'])
def create_teacher_view(request):
    """
    Creates a new teacher account with assigned classes, subjects, full name, and credentials.
    """
    inst = get_user_institution(request.user)
    if request.method == 'POST':
        form = TeacherCreationForm(request.POST, institution=inst)
        if form.is_valid():
            form.save()
            messages.success(request, "Teacher account created successfully!")
            return redirect('accounts:user_management_hub')
    else:
        form = TeacherCreationForm(institution=inst)
    return render(request, 'accounts/create_form.html', {'form': form, 'title': 'Register New Teacher'})


@login_required
@role_required(['institution_admin', 'superadmin'])
def create_student_view(request):
    """
    Creates institutional or independent student accounts with multi-selection for
    Board Classes, Subjects, and Competitive Exams, including personal subscriptions for independent students.
    """
    inst = get_user_institution(request.user)
    if request.method == 'POST':
        form = StudentCreationForm(request.POST, institution=inst)
        plan_id = request.POST.get('subscription_plan') or request.POST.get('plan')
        
        if form.is_valid():
            student_user = form.save()
            
            if not getattr(student_user, 'student_profile', None) or not student_user.student_profile.institution:
                if plan_id:
                    plan = SubscriptionPlan.objects.filter(pk=plan_id, plan_type='INDEPENDENT_STUDENT').first()
                    if plan:
                        sub, created = Subscription.objects.get_or_create(
                            user=student_user,
                            defaults={
                                'institution': None,
                                'plan': plan,
                                'payment_status': 'pending',
                                'is_active': False
                            }
                        )
                        if not created and sub.payment_status != 'pending':
                            sub.plan = plan
                            sub.payment_status = 'pending'
                            sub.is_active = False
                            sub.save()

            messages.success(request, "Student account created successfully!")
            return redirect('accounts:user_management_hub')
    else:
        form = StudentCreationForm(institution=inst)
        
    independent_plans = SubscriptionPlan.objects.filter(plan_type='INDEPENDENT_STUDENT', is_active=True)
    return render(request, 'accounts/create_student_form.html', {
        'form': form, 
        'title': 'Register New Student',
        'subscription_plans': independent_plans
    })


@login_required
@role_required(['institution_admin', 'superadmin'])
def create_content_team_view(request):
    """
    Creates a new Content Team account with explicit login credentials.
    """
    if request.method == 'POST':
        form = ContentTeamCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Content Team account created successfully!")
            return redirect('accounts:user_management_hub')
    else:
        form = ContentTeamCreationForm()
    return render(request, 'accounts/create_form.html', {'form': form, 'title': 'Register Content Team Member'})


@login_required
@role_required(['institution_admin', 'superadmin'])
def delete_institution_view(request, institution_id):
    """Deletes an institution record."""
    institution = get_object_or_404(Institution, pk=institution_id)
    user_inst = get_user_institution(request.user)
    if user_inst and user_inst.pk != institution.pk and not request.user.is_superuser:
        messages.error(request, "You do not have permission to delete this institution.")
        return redirect('accounts:user_management_hub')

    if request.method == 'POST':
        name = institution.name
        institution.delete()
        messages.success(request, f"Institution '{name}' deleted successfully!")
    return redirect('accounts:user_management_hub')


@login_required
@role_required(['institution_admin', 'superadmin'])
def delete_teacher_view(request, teacher_id):
    """Deletes a teacher profile and user account."""
    teacher = get_object_or_404(TeacherProfile, pk=teacher_id)
    inst = get_user_institution(request.user)
    if inst and teacher.institution != inst and not request.user.is_superuser:
        messages.error(request, "You do not have permission to delete this teacher.")
        return redirect('accounts:user_management_hub')

    if request.method == 'POST':
        username = teacher.user.username if teacher.user else "Teacher"
        if teacher.user:
            teacher.user.delete()
        else:
            teacher.delete()
        messages.success(request, f"Teacher '{username}' deleted successfully!")
    return redirect('accounts:user_management_hub')


@login_required
@role_required(['institution_admin', 'superadmin'])
def delete_student_view(request, student_id):
    """Deletes a student profile and user account."""
    student = get_object_or_404(StudentProfile, pk=student_id)
    inst = get_user_institution(request.user)
    if inst and student.institution != inst and not request.user.is_superuser:
        messages.error(request, "You do not have permission to delete this student.")
        return redirect('accounts:user_management_hub')

    if request.method == 'POST':
        username = student.user.username if student.user else "Student"
        if student.user:
            student.user.delete()
        else:
            student.delete()
        messages.success(request, f"Student '{username}' deleted successfully!")
    return redirect('accounts:user_management_hub')


@login_required
@role_required(['superadmin'])
def superadmin_profile_view(request):
    """
    Allows the superadmin to view and update their profile details, 
    including full name, username, email, password, phone number, and profile picture.
    """
    user = request.user
    
    phone_number = getattr(user, 'phone', '')
    if not phone_number and hasattr(user, 'profile'):
        phone_number = getattr(user.profile, 'phone_number', '')

    if request.method == 'POST':
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.username = request.POST.get('username', user.username)
        user.email = request.POST.get('email', user.email)
        
        phone = request.POST.get('phone_number')
        if phone:
            if hasattr(user, 'phone'):
                user.phone = phone
            elif hasattr(user, 'profile'):
                user.profile.phone_number = phone
                user.profile.save()

        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        if new_password:
            if new_password == confirm_password:
                user.set_password(new_password)
                messages.success(request, "Password updated successfully!")
            else:
                messages.error(request, "New passwords do not match.")

        if 'profile_picture' in request.FILES:
            if hasattr(user, 'profile'):
                user.profile.picture = request.FILES['profile_picture']
                user.profile.save()
            elif hasattr(user, 'student_profile'):
                user.student_profile.picture = request.FILES['profile_picture']
                user.student_profile.save()
            
        user.save()
        messages.success(request, "Profile settings updated successfully!")
        return redirect('accounts:superadmin_profile')
        
    return render(request, 'accounts/superadmin_profile.html', {
        'user': user,
        'phone_number': phone_number
    })


@login_required
@role_required(['superadmin'])
def delete_content_team_view(request, user_id):
    """Deletes a content team user account."""
    member = get_object_or_404(User, pk=user_id, role='content_team')
    if request.method == 'POST':
        username = member.username
        member.delete()
        messages.success(request, f"Content team member '{username}' deleted successfully!")
    return redirect('accounts:user_management_hub')


@login_required
@role_required(['content_team', 'superadmin'])
def content_team_dashboard(request):
    """
    Dashboard for Content Team members with complete dynamic hierarchy filtering for questions.
    """
    from question_bank.models import (
        Question, BoardClass, BoardSubject, BoardChapter, BoardTopic, BoardSubTopic,
        CompetitiveExam, CompetitiveModule, CompetitiveSubModule
    )

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

    total_questions = Question.objects.count()
    recent_questions = questions.order_by('-id')[:25]

    context = {
        'total_questions': total_questions,
        'recent_questions': recent_questions,
        'board_classes': BoardClass.objects.filter(is_active=True),
        'board_subjects': BoardSubject.objects.filter(is_active=True),
        'board_chapters': BoardChapter.objects.all(),
        'board_topics': BoardTopic.objects.all(),
        'board_subtopics': BoardSubTopic.objects.all(),
        'competitive_exams': CompetitiveExam.objects.filter(is_active=True),
        'competitive_modules': CompetitiveModule.objects.all(),
        'competitive_submodules': CompetitiveSubModule.objects.all(),
    }
    return render(request, "dashboard/content_team.html", context)


@login_required
@role_required(['teacher'])
def teacher_profile_view(request):
    """
    Allows teachers to view locked details (Name, ID, Username) 
    and update editable details (Phone, Email, Password).
    """
    user = request.user
    teacher_profile = getattr(user, 'teacher_profile', None)
    
    phone_number = getattr(user, 'phone', '')
    if not phone_number and hasattr(user, 'profile'):
        phone_number = getattr(user.profile, 'phone_number', '')

    if request.method == 'POST':
        user.email = request.POST.get('email', user.email)
        
        phone = request.POST.get('phone_number')
        if phone:
            if hasattr(user, 'phone'):
                user.phone = phone
            elif hasattr(user, 'profile'):
                user.profile.phone_number = phone
                user.profile.save()

        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        if new_password:
            if new_password == confirm_password:
                user.set_password(new_password)
                messages.success(request, "Password updated successfully!")
            else:
                messages.error(request, "New passwords do not match.")

        user.save()
        messages.success(request, "Profile settings updated successfully!")
        return redirect('accounts:teacher_profile')
        
    return render(request, 'dashboard/teacher_profile.html', {
        'user': user,
        'teacher_profile': teacher_profile,
        'phone_number': phone_number
    })


@login_required
@role_required(['institution_admin', 'superadmin'])
def institution_dashboard_view(request):
    user = request.user
    
    # Resolve the specific institution for the logged-in institution admin or teacher
    institution = None
    if hasattr(user, 'institution_admin_profile') and user.institution_admin_profile:
        institution = getattr(user.institution_admin_profile, 'institution', None)
    elif hasattr(user, 'institution') and isinstance(user.institution, Institution):
        institution = user.institution
    
    # If standard institution admin lookup fails, try helper
    if not institution:
        institution = get_user_institution(user)
        
    # Fallback only if no institution is bound and user is superadmin viewing generally
    if not isinstance(institution, Institution) and user.is_superuser:
        institution = Institution.objects.first()

    # Scope all queries strictly to this specific institution
    if institution:
        teachers = TeacherProfile.objects.filter(institution=institution)
        students = StudentProfile.objects.filter(institution=institution)
        exams = Exam.objects.filter(institution=institution).order_by('-id')
    else:
        teachers = TeacherProfile.objects.none()
        students = StudentProfile.objects.none()
        exams = Exam.objects.none()

    classes = BoardClass.objects.all()

    class_progress_data = []
    for cls in classes:
        cls_exams = exams[:3]
        exam_scores = []
        for ex in cls_exams:
            attempts = ExamAttempt.objects.filter(exam=ex)
            avg_pct = attempts.aggregate(Avg('percentage'))['percentage__avg'] or 0.0
            exam_scores.append({
                'exam_title': ex.title,
                'average_percentage': round(avg_pct, 1)
            })
        if exam_scores:
            class_progress_data.append({
                'class_name': cls.name,
                'exam_scores': exam_scores
            })

    context = {
        'institution': institution,
        'teachers_count': teachers.count(),
        'students_count': students.count(),
        'exams_count': exams.count(),
        'teachers': teachers,
        'students': students[:10],
        'classes': classes,
        'exams': exams,
        'class_progress_data': class_progress_data,
    }
    return render(request, "dashboard/institution.html", context)


@login_required
@role_required(['institution_admin', 'superadmin'])
def delete_exam_view(request, exam_id):
    """Deletes an institutional exam record."""
    exam = get_object_or_404(Exam, pk=exam_id)
    if request.method == 'POST':
        title = exam.title
        exam.delete()
        messages.success(request, f"Exam '{title}' deleted successfully!")
    return redirect('accounts:dashboard_redirect')

@login_required
@role_required(['student', 'institution_admin', 'superadmin'])
def independent_student_dashboard(request):
    user = request.user
    student_profile = getattr(user, 'student_profile', None)
    
    if student_profile and student_profile.student_type == 'institutional':
        return redirect('accounts:dashboard_redirect')

    if request.method == 'POST':
        # Handle plan request submission
        plan_id = request.POST.get('request_plan_id')
        if plan_id:
            plan = get_object_or_404(SubscriptionPlan, pk=plan_id)
            sub, created = Subscription.objects.get_or_create(
                user=user,
                defaults={
                    'institution': None,
                    'plan': plan,
                    'payment_status': 'pending',
                    'is_active': False
                }
            )
            if not created:
                sub.plan = plan
                sub.payment_status = 'pending'
                sub.is_active = False
                sub.save()
            messages.success(request, f"Request for '{plan.name}' submitted successfully! Awaiting superadmin approval.")
            return redirect('accounts:dashboard_redirect')

        # Profile update handling...
        phone = request.POST.get('phone_number')
        if phone:
            if hasattr(user, 'phone'):
                user.phone = phone
            elif hasattr(user, 'profile'):
                user.profile.phone_number = phone
                user.profile.save()

        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        if new_password:
            if new_password == confirm_password:
                user.set_password(new_password)
                messages.success(request, "Password updated successfully!")
            else:
                messages.error(request, "New passwords do not match.")

        user.save()
        messages.success(request, "Profile updated successfully!")
        return redirect('accounts:dashboard_redirect')

    # Fetch active or pending subscription dynamically reflecting superadmin updates
    active_subscription = Subscription.objects.filter(user=user, is_active=True, payment_status__iexact='approved').order_by('-id').first()
    if not active_subscription:
        active_subscription = Subscription.objects.filter(user=user, is_active=True).order_by('-id').first()

    pending_subscription = Subscription.objects.filter(user=user, is_active=False, payment_status__iexact='pending').order_by('-id').first()
    
    available_plans = SubscriptionPlan.objects.filter(plan_type__in=['INDEPENDENT_STUDENT', 'independent_student'], is_active=True)
    attempts = ExamAttempt.objects.filter(student=user).select_related('exam', 'exam__board_subject').order_by('-submitted_at')

    subject_stats_map = {}
    for att in attempts:
        subject = att.exam.board_subject
        subj_name = subject.name if subject else "General"
        if subj_name not in subject_stats_map:
            subject_stats_map[subj_name] = {'count': 0, 'percentages': []}
        subject_stats_map[subj_name]['count'] += 1
        subject_stats_map[subj_name]['percentages'].append(float(att.percentage))

    subject_stats = []
    for subj_name, data in subject_stats_map.items():
        avg_pct = sum(data['percentages']) / len(data['percentages']) if data['percentages'] else 0.0
        subject_stats.append({
            'subject_name': subj_name,
            'total_attempts': data['count'],
            'avg_percentage': avg_pct
        })

    context = {
        'student_profile': student_profile,
        'active_subscription': active_subscription,
        'pending_subscription': pending_subscription,
        'available_plans': available_plans,
        'attempts': attempts,
        'subject_stats': subject_stats,
        'phone_number': getattr(user, 'phone', '') or getattr(getattr(user, 'profile', None), 'profile_number', ''),
    }
    return render(request, "dashboard/independent_student.html", context)

@login_required
@role_required(['student', 'institution_admin', 'superadmin'])
def independent_student_profile_view(request):
    user = request.user
    student_profile = getattr(user, 'student_profile', None)
    
    if student_profile and student_profile.student_type == 'institutional':
        return redirect('accounts:dashboard_redirect')

    phone_number = getattr(user, 'phone', '')
    if not phone_number and hasattr(user, 'profile'):
        phone_number = getattr(user.profile, 'phone_number', '')

    if request.method == 'POST':
        phone = request.POST.get('phone_number')
        if phone:
            if hasattr(user, 'phone'):
                user.phone = phone
            elif hasattr(user, 'profile'):
                user.profile.phone_number = phone
                user.profile.save()

        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        if new_password:
            if new_password == confirm_password:
                user.set_password(new_password)
                messages.success(request, "Password updated successfully!")
            else:
                messages.error(request, "New passwords do not match.")

        user.save()
        messages.success(request, "Profile settings updated successfully!")
        return redirect('accounts:independent_student_profile')

    context = {
        'user': user,
        'student_profile': student_profile,
        'phone_number': phone_number,
    }
    return render(request, "dashboard/independent_student_profile.html", context)

@login_required
@role_required(['student', 'institution_admin', 'superadmin'])
def start_exam_for_topic(request, pk):
    """
    Resolves or auto-creates an Exam instance linked to a Board Subtopic or Competitive SubModule PK,
    matching exact model foreign keys, then routes directly to take_exam.
    """
    exam = Exam.objects.filter(models.Q(board_subtopic_id=pk) | models.Q(competitive_submodule_id=pk)).first()
    
    if not exam:
        from question_bank.models import BoardSubTopic, CompetitiveSubModule
        subtopic = BoardSubTopic.objects.filter(pk=pk).first()
        submodule = CompetitiveSubModule.objects.filter(pk=pk).first()
        
        if subtopic:
            exam = Exam.objects.create(
                title=f"Assessment: {subtopic.title}",
                assessment_flow='board',
                scope_level='subtopic',
                board_subtopic=subtopic,
                creator=request.user
            )
        elif submodule:
            exam = Exam.objects.create(
                title=f"Assessment: {submodule.title}",
                assessment_flow='competitive',
                scope_level='subtopic',
                competitive_submodule=submodule,
                creator=request.user
            )
        else:
            messages.error(request, "Invalid topic or module reference.")
            return redirect('accounts:dashboard_redirect')
            
    return redirect('examinations:take_exam', exam_id=exam.id)


@login_required
@role_required(['student', 'institution_admin', 'superadmin'])
def independent_student_courses_view(request):
    user = request.user
    student_profile = getattr(user, 'student_profile', None)
    
    if student_profile and student_profile.student_type == 'institutional':
        return redirect('accounts:dashboard_redirect')

    # Fetch attempt exam IDs made by this independent student
    user_attempts_qs = ExamAttempt.objects.filter(student=user, exam__isnull=False).select_related('exam')
    
    # Explicit mapping for board subtopic IDs vs competitive submodule IDs
    board_attempted_subtopics = set()
    competitive_attempted_submodules = set()
    
    for attempt in user_attempts_qs:
        if attempt.exam:
            if attempt.exam.board_subtopic_id:
                board_attempted_subtopics.add(int(attempt.exam.board_subtopic_id))
            if attempt.exam.competitive_submodule_id:
                competitive_attempted_submodules.add(int(attempt.exam.competitive_submodule_id))

    courses = []
    if student_profile:
        if hasattr(student_profile, 'assigned_courses') and student_profile.assigned_courses.exists():
            courses = student_profile.assigned_courses.all()
        elif hasattr(student_profile, 'assigned_subjects') and student_profile.assigned_subjects.exists():
            subject_ids = student_profile.assigned_subjects.values_list('id', flat=True)
            courses = BoardSubject.objects.filter(id__in=subject_ids, is_active=True)

    competitive_hierarchy = {}
    try:
        from question_bank.models import CompetitiveExam
        registered_exams = []
        if student_profile and hasattr(student_profile, 'competitive_exams'):
            registered_exams = student_profile.competitive_exams.all()
            
        if registered_exams:
            exams = CompetitiveExam.objects.prefetch_related('modules', 'modules__submodules').filter(
                id__in=[e.id for e in registered_exams], 
                is_active=True
            )
            for exam in exams:
                exam_name = exam.title
                competitive_hierarchy[exam_name] = {}
                for mod in exam.modules.all():
                    mod_name = mod.title
                    submods = list(mod.submodules.all()) if hasattr(mod, 'submodules') else []
                    competitive_hierarchy[exam_name][mod_name] = submods
    except Exception:
        competitive_hierarchy = {}

    context = {
        'student_profile': student_profile,
        'courses': courses,
        'competitive_hierarchy': competitive_hierarchy,
        'user_attempts': board_attempted_subtopics,
        'competitive_attempts': competitive_attempted_submodules,
    }
    return render(request, "dashboard/independent_student_courses.html", context)


@login_required
@role_required(['superadmin'])
def manage_subscription_requests(request):
    if request.method == 'POST':
        sub_id = request.POST.get('subscription_id')
        action = request.POST.get('action') # 'approve', 'reject', or 'delete'
        subscription = get_object_or_404(Subscription, pk=sub_id)
        
        if action == 'approve':
            subscription.payment_status = 'approved'
            subscription.is_active = True
            if subscription.plan and subscription.plan.duration_days:
                subscription.end_date = timezone.now().date() + timedelta(days=subscription.plan.duration_days)
            subscription.save()
            messages.success(request, f"Subscription for {subscription.user.username} approved successfully.")
        elif action == 'reject':
            subscription.payment_status = 'rejected'
            subscription.is_active = False
            subscription.save()
            messages.warning(request, f"Subscription request for {subscription.user.username} was rejected.")
        elif action == 'delete':
            subscription.delete()
            messages.success(request, "Subscription record deleted successfully.")
            
        return redirect('accounts:manage_subscription_requests')

    # Explicitly separate pending requests from all other records
    pending_subscriptions = Subscription.objects.filter(payment_status__iexact='pending').select_related('user', 'plan').order_by('-id')
    all_subscriptions = Subscription.objects.all().select_related('user', 'plan').order_by('-id')

    context = {
        'pending_subscriptions': pending_subscriptions,
        'all_subscriptions': all_subscriptions,
    }
    return render(request, "dashboard/manage_subscriptions.html", context)