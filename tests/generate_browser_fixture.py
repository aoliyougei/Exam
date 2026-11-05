"""Generate pages only in the isolated test container."""
from pathlib import Path
from app import generate_exam_html

questions = []
for index in range(120):
    kind = ['single', 'multiple', 'judgment'][index % 3]
    question = {'type': kind, 'question': f'题库题目 {index}', 'score': 7}
    if kind != 'judgment':
        question['options'] = ['选项 A', '选项 B', '选项 C']
    question['answer'] = {'single': '1', 'multiple': ['0', '2'], 'judgment': 'true'}[kind]
    questions.append(question)
Path('/tmp/exam-browser.html').write_text(generate_exam_html({
    'title': '浏览器测试', 'duration': 30, 'total_score': 840, 'questions': questions,
}), encoding='utf-8')
