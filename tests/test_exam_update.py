from pathlib import Path
from unittest.mock import patch

import unittest
import test_exam_entry
import app as module


class ExamUpdateTests(unittest.TestCase):
    setUp = test_exam_entry.ExamEntryTests.setUp
    tearDown = test_exam_entry.ExamEntryTests.tearDown
    create = test_exam_entry.ExamEntryTests.create

    def update(self, exam_id, payload=None, headers=None):
        return self.client.put('/api/exams/' + exam_id,
            json=payload if payload is not None else {
                'title': '新版试卷', 'duration': 40,
                'questions': [{'type': 'judgment', 'question': '新题', 'answer': 'false', 'score': 20}]},
            headers=self.headers if headers is None else headers)

    def test_update_preserves_identity_qr_and_entry(self):
        old = self.create().json
        qr = Path(old['qr_path']).read_bytes()
        response = self.update(old['exam_id'])
        self.assertEqual(response.status_code, 200)
        data = response.json
        for key in ['exam_id', 'exam_name', 'exam_url', 'qr_url', 'qr_path']:
            self.assertEqual(data[key], old[key])
        self.assertEqual(data['total_score'], 20)
        self.assertEqual(Path(old['qr_path']).read_bytes(), qr)
        body = self.client.post('/enter', data={'exam_name': old['exam_name']}, follow_redirects=True).get_data(as_text=True)
        self.assertIn('新版试卷', body)
        self.assertIn('新题', body)
        self.assertNotIn('测试题', body)

    def test_conflict_returns_target(self):
        old = self.create().json
        duplicate = self.create()
        self.assertEqual(duplicate.status_code, 409)
        self.assertEqual(duplicate.json['exam_id'], old['exam_id'])
        self.assertEqual(duplicate.json['exam_name'], old['exam_name'])

    def test_failure_and_validation_preserve_old_exam(self):
        old = self.create().json
        path = Path('static/exams', old['exam_id'] + '.html')
        original = path.read_bytes()
        self.assertEqual(self.update(old['exam_id'], headers={'X-API-Key':'bad'}).status_code, 401)
        for payload in [{}, {'title':'x','questions':[]}, {'title':'x','questions':[{}]},
                        dict(self.payload, exam_name='改名'),
                        {'title':'x','questions':[{'type':'judgment','question':'x','answer':True,'score':1}]}]:
            self.assertEqual(self.update(old['exam_id'], payload).status_code, 400)
        with patch.object(module.os, 'replace', side_effect=OSError('disk failure')):
            with self.assertLogs(module.app.logger, level='ERROR'):
                self.assertEqual(self.update(old['exam_id']).status_code, 500)
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(len(list(Path('static/exams').iterdir())), 1)

    def test_legacy_and_unknown(self):
        payload = dict(self.payload)
        del payload['exam_name']
        old = self.create(payload).json
        self.assertEqual(self.update(old['exam_id']).status_code, 200)
        for exam_id in ['deadbeef', 'invalid-id']:
            self.assertEqual(self.update(exam_id).status_code, 404)
