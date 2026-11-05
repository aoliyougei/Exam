import sqlite3
import unittest
from pathlib import Path

import app as module
import test_exam_entry


class ExamQueryTests(unittest.TestCase):
    setUp = test_exam_entry.ExamEntryTests.setUp
    tearDown = test_exam_entry.ExamEntryTests.tearDown
    create = test_exam_entry.ExamEntryTests.create

    def test_queries_require_auth(self):
        for path in ['/api/exams', '/api/exams/deadbeef']:
            self.assertEqual(self.client.get(path).status_code, 401)
        self.assertEqual(self.client.get('/api/exams', headers=self.headers).json['exams'], [])

    def test_create_list_detail_and_update(self):
        created = self.create().json
        listed = self.client.get('/api/exams', headers=self.headers).json['exams']
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0]['exam_id'], created['exam_id'])
        self.assertEqual(listed[0]['title'], self.payload['title'])
        self.assertNotIn('questions', listed[0])
        path = '/api/exams/' + created['exam_id']
        detail = self.client.get(path, headers=self.headers).json['exam']
        self.assertEqual(detail['exam_name'], self.payload['exam_name'])
        self.assertEqual(detail['questions'], self.payload['questions'])
        replacement = dict(self.payload)
        del replacement['exam_name']
        replacement['title'] = '修订标题'
        self.assertEqual(self.client.put(path, json=replacement, headers=self.headers).status_code, 200)
        self.assertEqual(self.client.get(path, headers=self.headers).json['exam']['title'], '修订标题')
        self.assertEqual(self.client.get('/api/exams', headers=self.headers).json['exams'][0]['title'], '修订标题')

    def test_legacy_and_missing_files(self):
        Path('static/exams/12345678.html').write_text('legacy', encoding='utf-8')
        listed = self.client.get('/api/exams', headers=self.headers).json['exams']
        self.assertEqual(listed[0]['exam_id'], '12345678')
        self.assertFalse(listed[0]['data_available'])
        detail = self.client.get('/api/exams/12345678', headers=self.headers)
        self.assertEqual(detail.status_code, 200)
        self.assertIsNone(detail.json['exam']['questions'])
        for exam_id in ['deadbeef', 'invalid']:
            self.assertEqual(self.client.get('/api/exams/' + exam_id, headers=self.headers).status_code, 404)
        created = self.create().json
        Path('static/exams/' + created['exam_id'] + '.html').unlink()
        items = self.client.get('/api/exams', headers=self.headers).json['exams']
        missing = next(item for item in items if item['exam_id'] == created['exam_id'])
        self.assertFalse(missing['file_exists'])
        self.assertTrue(missing['data_available'])

    def test_old_schema_migration_and_secret_exclusion(self):
        Path('storage').mkdir()
        with sqlite3.connect('storage/exams.sqlite3') as connection:
            connection.execute('CREATE TABLE exams (name TEXT PRIMARY KEY, filename TEXT NOT NULL)')
            connection.execute('INSERT INTO exams VALUES (?, ?)', ('旧考试', 'abcdef12.html'))
        items = self.client.get('/api/exams', headers=self.headers).json['exams']
        self.assertEqual(items[0]['exam_name'], '旧考试')
        self.assertFalse(items[0]['file_exists'])
        created = self.create(dict(self.payload, api_key='do-not-save')).json
        response = self.client.get('/api/exams/' + created['exam_id'], headers=self.headers)
        self.assertNotIn('do-not-save', response.get_data(as_text=True))
        self.assertIn('no-store', response.headers['Cache-Control'])
