import unittest
from app import generate_exam_html


class ScoreExportTests(unittest.TestCase):
    def test_generated_page_includes_local_image_export_and_wrong_details(self):
        page = generate_exam_html({'title': '测试', 'duration': 60, 'total_score': 1,
            'questions': [{'type': 'single', 'question': '题目', 'options': ['甲', '乙'], 'answer': '0', 'score': 1}]})
        self.assertIn('id="saveScoreBtn"', page)
        self.assertIn('function getWrongQuestionDetails()', page)
        self.assertIn('function saveScoreImage()', page)
        self.assertIn('id="wrongQuestionDetails"', page)
        self.assertIn("canvas.toBlob", page)
        self.assertNotIn('html2canvas', page)
