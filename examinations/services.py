from .models import Exam

def student_can_access_exam(student_profile, exam):
    """
    Enforce strict access rules:
    - Independent students can access non-practice exams without institution constraints.
    - Institution students can ONLY access exams belonging to their own institution.
    """
    if not student_profile or not exam:
        return False

    institution = getattr(student_profile, 'institution', None)
    
    if institution:
        if not exam.institution_id:
            return False
        return exam.institution_id == institution.id
    else:
        if exam.exam_type == 'practice':
            return False
        return exam.institution is None


def get_available_exams(student_profile):
    """
    Return filtered queryset complying with institutional and independent boundaries.
    """
    if not student_profile:
        return Exam.objects.none()

    institution = getattr(student_profile, 'institution', None)
    
    if institution:
        return Exam.objects.filter(institution=institution).order_by('-id')
    else:
        return Exam.objects.filter(institution__isnull=True).exclude(exam_type='practice').order_by('-id')