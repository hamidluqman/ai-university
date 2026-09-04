import pandas as pd
from .models import Question, BoardSubTopic, CompetitiveSubModule


def process_question_excel_import(excel_file, assessment_flow, scope_id):
    """
    Parses an Excel spreadsheet and creates questions in bulk.
    
    Expected Excel Headers:
    question_text, option_a, option_b, option_c, option_d, correct_option, explanation, youtube_url
    """
    df = pd.read_excel(excel_file)
    created_count = 0

    subtopic = None
    submodule = None

    if assessment_flow == 'board':
        subtopic = BoardSubTopic.objects.get(id=scope_id)
    else:
        submodule = CompetitiveSubModule.objects.get(id=scope_id)

    for _, row in df.iterrows():
        question_text = str(row.get('question_text', '')).strip()
        option_a = str(row.get('option_a', '')).strip()
        option_b = str(row.get('option_b', '')).strip()
        option_c = str(row.get('option_c', '')).strip()
        option_d = str(row.get('option_d', '')).strip()
        correct_option = str(row.get('correct_option', '')).strip().upper()
        explanation = str(row.get('explanation', '')).strip()
        youtube_url = str(row.get('youtube_url', '')).strip()

        if correct_option in ['A', 'B', 'C', 'D']:
            Question.objects.create(
                assessment_flow=assessment_flow,
                board_subtopic=subtopic,
                competitive_submodule=submodule,
                question_text=question_text,
                option_a=option_a,
                option_b=option_b,
                option_c=option_c,
                option_d=option_d,
                correct_option=correct_option,
                explanation=explanation if explanation != 'nan' else '',
                youtube_url=youtube_url if youtube_url != 'nan' else ''
            )
            created_count += 1

    return created_count