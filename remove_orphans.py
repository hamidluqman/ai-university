import os

# Exact list of unlinked templates identified from your scan
UNLINKED_TEMPLATES = [
    "accounts/templates/accounts/login.html",
    "courses/templates/courses/course_list.html",
    "courses/templates/courses/student_progress.html",
    "question_bank/templates/admin/question_bank/import_questions.html",
    "question_bank/templates/admin/question_bank/question/change_list.html",
    "templates/Examinations/exam_result.html",
    "templates/Examinations/official_exams.html",
    "templates/Examinations/results_dashboard.html",
    "templates/Examinations/take_exam.html",
    "templates/Examinations/teacher_exams.html",
    "templates/Examinations/youtube_player.html",
    "templates/admin/accounts/user/change_list.html",
    "templates/admin/dropdown_filter.html",
    "templates/admin/question_bank/question/change_list.html",
    "templates/pricing.html",
    "templates/registration/login.html",
    "templates/subscriptions/pending_payment.html"
]

def delete_unlinked_files():
    deleted_count = 0
    for path in UNLINKED_TEMPLATES:
        if os.path.exists(path):
            try:
                os.remove(path)
                print(f"[DELETED] {path}")
                deleted_count += 1
            except Exception as e:
                print(f"[ERROR] Could not delete {path}: {e}")
        else:
            print(f"[NOT FOUND] {path}")

    print(f"\nCleanup complete. Successfully removed {deleted_count} unlinked template files.")

if __name__ == "__main__":
    delete_unlinked_files()