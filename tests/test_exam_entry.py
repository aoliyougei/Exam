import os
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlsplit

import app as module


class ExamEntryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd = os.getcwd()
        os.chdir(self.tmp.name)
        Path('static/exams').mkdir(parents=True)
        Path('static/qrcodes').mkdir(parents=True)
        self.static_folder = module.app.static_folder
        module.app.static_folder = str(Path('static').resolve())
        self.client = module.app.test_client()
        self.headers = {'X-API-Key': module.API_KEY}
        self.payload = {
            'title': '试卷标题', 'exam_name': '测试考试', 'duration': 30,
            'questions': [{'type': 'single', 'question': '测试题',
                           'options': ['A', 'B'], 'answer': '0', 'score': 10}],
        }

    def tearDown(self):
        module.app.static_folder = self.static_folder
        os.chdir(self.cwd)
        self.tmp.cleanup()

    def create(self, payload=None, client=None):
        return (client or self.client).post('/api/create_exam',
            json=self.payload if payload is None else payload, headers=self.headers)

    def test_named_exam_and_direct_links(self):
        with patch.object(module, 'generate_qrcode', wraps=module.generate_qrcode) as qr:
            response = self.create()
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['exam_name'], '测试考试')
        self.assertEqual(data['total_score'], 10)
        self.assertEqual(data['question_count'], 1)
        qr.assert_called_once_with(data['exam_url'], data['exam_id'])
        path = urlsplit(data['exam_url']).path
        direct = self.client.get(path)
        self.assertEqual(direct.status_code, 200)
        self.assertIn('试卷标题', direct.get_data(as_text=True))
        with self.client.get(urlsplit(data['qr_url']).path) as qr_response:
            self.assertEqual(qr_response.status_code, 200)
        entered = self.client.post('/enter', data={'exam_name': ' 测试考试 '})
        self.assertEqual(entered.status_code, 302)
        self.assertEqual(entered.location, path)
        self.assertEqual(self.client.post('/enter', data={'exam_name': '测试考试'},
                                         follow_redirects=True).data, direct.data)

    def test_trim_and_duplicate_preserves_original(self):
        first = self.create(dict(self.payload, exam_name=' 测试考试 ')).get_json()
        files = {str(p): p.read_bytes() for p in Path('static').rglob('*') if p.is_file()}
        second = self.create()
        self.assertEqual(second.status_code, 409)
        self.assertEqual(first['exam_name'], '测试考试')
        self.assertEqual(files, {str(p): p.read_bytes() for p in Path('static').rglob('*') if p.is_file()})

    def test_invalid_name(self):
        for name in ['', '   ', None, 123, [], {}, 'x' * 121]:
            with self.subTest(name=name):
                self.assertEqual(self.create(dict(self.payload, exam_name=name)).status_code, 400)
        self.assertFalse(list(Path('static/exams').iterdir()))

    def test_legacy_client(self):
        payload = dict(self.payload)
        del payload['exam_name']
        response = self.create(payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get(urlsplit(response.json['exam_url']).path).status_code, 200)

    def test_unauthorized_name_not_reserved(self):
        response = self.client.post('/api/create_exam', json=self.payload,
                                    headers={'X-API-Key': 'invalid'})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.create().status_code, 200)

    def test_unknown_invalid_and_missing_file(self):
        self.assertEqual(self.client.post('/enter', data={'exam_name': '未知'}).status_code, 404)
        for name in ['', ' ', 'x' * 121]:
            self.assertEqual(self.client.post('/enter', data={'exam_name': name}).status_code, 400)
        data = self.create().json
        Path('static/exams', data['exam_id'] + '.html').unlink()
        self.assertEqual(self.client.post('/enter', data={'exam_name': '测试考试'}).status_code, 404)

    def test_persisted_exact_names_and_escaping(self):
        name = "<script>alert('x')</script> ' OR 1=1 --"
        self.assertEqual(self.create(dict(self.payload, exam_name=name)).status_code, 200)
        client = module.app.test_client()
        self.assertEqual(client.post('/enter', data={'exam_name': name}).status_code, 302)
        self.assertEqual(client.post('/enter', data={'exam_name': "' OR 1=1 --"}).status_code, 404)
        body = client.post('/enter', data={'exam_name': '<script>missing</script>'}).get_data(as_text=True)
        self.assertNotIn('<script>missing</script>', body)
        self.assertEqual(self.create(dict(self.payload, exam_name='Case')).status_code, 200)
        self.assertEqual(client.post('/enter', data={'exam_name': 'case'}).status_code, 404)
        self.assertTrue(Path('storage/exams.sqlite3').is_file())
        self.assertEqual(client.get('/static/../storage/exams.sqlite3').status_code, 404)

    def test_concurrent_duplicate(self):
        def create(_):
            with module.app.test_client() as client:
                return self.create(client=client).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses = list(pool.map(create, range(2)))
        self.assertEqual(sorted(statuses), [200, 409])
        self.assertEqual(len(list(Path('static/exams').glob('*.html'))), 1)

    def test_generation_failure_rolls_back(self):
        with patch.object(module, 'generate_qrcode', side_effect=OSError('test failure')):
            with self.assertLogs(module.app.logger, level='ERROR'):
                self.assertEqual(self.create().status_code, 500)
        self.assertFalse(list(Path('static/exams').iterdir()))
        self.assertFalse(list(Path('static/qrcodes').iterdir()))
        self.assertEqual(self.create().status_code, 200)

    def test_home_and_admin(self):
        home = self.client.get('/').get_data(as_text=True)
        self.assertIn('name="exam_name"', home)
        self.assertIn('action="/enter"', home)
        self.assertIn('进入考试', home)
        self.assertIn('for="examName"', home)
        self.assertNotIn('id="apiKey"', home)
        self.assertIn('linear-gradient(135deg, #667eea 0%, #764ba2 100%)', home)
        self.assertIn('background: #4CAF50', home)
        self.assertIn('class="entry-card"', home)
        self.assertIn('class="entry-content"', home)
        self.assertNotIn('href="/admin"', home)
        self.assertNotIn('考试管理', home)
        self.assertIn('max-width: 560px', home)
        self.assertIn('aria-describedby="entryHelp"', home)
        self.assertIn(':focus-visible', home)
        self.assertIn('@media (max-width: 768px)', home)
        admin = self.client.get('/admin')
        self.assertEqual(admin.status_code, 200)
        self.assertIn('id="apiKey"', admin.get_data(as_text=True))
        self.assertIn('id="examName"', admin.get_data(as_text=True))
        self.assertIn('exam_name', admin.get_data(as_text=True))

    def test_database_failure_is_not_reported_as_not_found(self):
        with patch.object(module, 'exam_registry', side_effect=sqlite3.OperationalError('offline')):
            with self.assertLogs(module.app.logger, level='ERROR'):
                self.assertEqual(self.client.post('/enter', data={'exam_name': '考试'}).status_code, 503)

    def test_filename_collision_preserves_existing_files(self):
        data = self.create().json
        original = {str(p): p.read_bytes() for p in Path('static').rglob('*') if p.is_file()}
        with patch.object(module.uuid, 'uuid4', return_value=data['exam_id'] + '-collision'):
            with self.assertLogs(module.app.logger, level='ERROR'):
                self.assertEqual(self.create(dict(self.payload, exam_name='另一场')).status_code, 500)
        self.assertEqual(original, {str(p): p.read_bytes() for p in Path('static').rglob('*') if p.is_file()})
        self.assertEqual(self.create(dict(self.payload, exam_name='另一场')).status_code, 200)

    def test_lookup_name_and_credentials_not_embedded(self):
        payload = dict(self.payload, exam_name='</script><script>alert(1)</script>',
                       api_key='body-secret-not-public')
        response = self.create(payload)
        self.assertEqual(response.status_code, 200)
        html = self.client.get(urlsplit(response.json['exam_url']).path).get_data(as_text=True)
        self.assertNotIn(payload['exam_name'], html)
        self.assertNotIn(payload['api_key'], html)

    def test_invalid_json_object(self):
        for payload in [[], 'text', None]:
            self.assertEqual(self.client.post('/api/create_exam', json=payload,
                                             headers=self.headers).status_code, 400)


if __name__ == '__main__':
    unittest.main()
