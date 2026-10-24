import base64
import io
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from PIL import Image
from server.app import APIError, Handler, Store, ThreadingHTTPServer


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(self.tmp.name, demo=True, editors=['editor@example.test'])
        self.owner = self.login('owner@example.test')
        self.other = self.login('other@example.test')
        self.editor = self.login('editor@example.test')

    def tearDown(self):
        self.tmp.cleanup()

    def login(self, email):
        self.store.mail_link(email)
        link = json.loads((Path(self.tmp.name) / 'mail.jsonl').read_text().splitlines()[-1])['link']
        return self.store.session(self.store.verify(link.split('token=')[1]))

    def payload(self, **extra):
        return {'kind': 'practice', 'title': 'A personal account', 'summary': 'A small everyday example.', 'relationship': 'personal experience', 'context': 'My own account.', 'account': 'Observe, adjust, try again.', 'display_name': 'A pseudonym', 'publication_permission': True, 'rights_confirmation': True, 'email': 'owner@example.test', **extra}

    def publish(self, ident):
        item = self.store.private(self.editor, ident, admin=True)
        return self.store.review(self.editor, ident, {'action': 'published', 'revision_id': item['revision_id']})

    def assertAPIError(self, status, fn, *args):
        with self.assertRaises(APIError) as raised:
            fn(*args)
        self.assertEqual(raised.exception.status, status)

    def test_submission_persists_and_pending_is_private(self):
        ident = self.store.submit(self.payload(), self.owner)['id']
        self.assertNotIn(ident, [p['id'] for p in self.store.collection('practice')])
        self.assertAPIError(403, self.store.private, None)
        self.assertAPIError(404, self.store.private, self.other, ident)
        reopened = Store(self.tmp.name, demo=True)
        self.assertEqual(reopened.private(self.owner, ident)['content']['title'], 'A personal account')
        self.publish(ident)
        public = self.store.detail(ident, 'practice')
        serialized = json.dumps(public)
        self.assertNotIn('owner@example.test', serialized)
        self.assertNotIn('csrf', serialized)
        self.assertNotIn('feedback', serialized)

    def test_revisions_do_not_replace_published_until_reviewed(self):
        ident = self.store.submit(self.payload(), self.owner)['id']
        self.publish(ident)
        self.store.submit(self.payload(title='A changed account'), self.owner, ident)
        self.assertEqual(self.store.detail(ident, 'practice')['title'], 'A personal account')
        self.assertAPIError(403, self.store.submit, self.payload(title='Not yours'), self.other, ident)
        self.assertAPIError(403, self.store.review, self.other, ident, {'action': 'published'})
        revision = self.store.private(self.owner, ident)
        self.store.review(self.editor, ident, {'action': 'needs changes', 'feedback': 'Please clarify your context.', 'revision_id': revision['revision_id']})
        self.assertEqual(self.store.detail(ident, 'practice')['title'], 'A personal account')
        self.assertIn('clarify', self.store.private(self.owner, ident)['feedback'][0]['feedback'])
        self.store.submit(self.payload(title='An approved revision'), self.owner, ident)
        self.publish(ident)
        self.assertEqual(self.store.detail(ident, 'practice')['title'], 'An approved revision')
        self.assertEqual(self.store.detail(ident, 'practice')['revision'], 3)

    def test_variation_never_overwrites_parent_and_withdrawal_hides_it(self):
        before = self.store.detail('rice-water', 'practice')
        ident = self.store.submit(self.payload(kind='variation', parent_id=before['id'], similar='Same goal.', changes='A different cup.'), self.owner)['id']
        self.publish(ident)
        self.assertEqual(self.store.detail('rice-water', 'practice'), before)
        self.assertEqual(self.store.detail(ident, 'practice')['parent_id'], before['id'])
        self.assertAPIError(403, self.store.withdraw, self.other, ident)
        self.store.withdraw(self.owner, ident)
        self.assertAPIError(404, self.store.detail, ident, 'practice')
        self.assertAPIError(409, self.store.submit, self.payload(kind='variation', similar='same', changes='other'), self.owner, ident)

    def test_email_links_single_use_expire_and_unverified_cannot_publish(self):
        ident = self.store.submit(self.payload(email='unverified@example.test'))['id']
        self.assertAPIError(422, self.publish, ident)
        self.store.mail_link('new@example.test')
        token = json.loads((Path(self.tmp.name) / 'mail.jsonl').read_text().splitlines()[-1])['link'].split('token=')[1]
        self.store.verify(token)
        self.assertAPIError(401, self.store.verify, token)
        self.store.mail_link('expiring@example.test')
        token = json.loads((Path(self.tmp.name) / 'mail.jsonl').read_text().splitlines()[-1])['link'].split('token=')[1]
        with self.store.connect() as db:
            db.execute('UPDATE login_tokens SET expires=0')
        self.assertAPIError(401, self.store.verify, token)

    def test_sources_print_oral_video_metadata_and_stable_citations(self):
        self.assertAPIError(422, self.store.submit, self.payload(relationship='source-based research'), self.owner)
        refs = [
            {'type': 'academic article', 'title': 'TEST FIXTURE — paper', 'creators': 'test author', 'venue': 'test venue', 'doi': '', 'relation': 'supports this specific claim', 'block_id': 'account', 'locator': 'p. 12'},
            {'type': 'video', 'title': 'TEST FIXTURE — video', 'url': 'https://www.youtube.com/watch?v=TESTFIXTURE&t=90', 'locator': '01:30', 'relation': 'documents this practice', 'block_id': 'account'},
            {'type': 'blog or essay', 'title': 'TEST FIXTURE — blog', 'url': 'https://example.test/post', 'relation': 'further reading or viewing'},
            {'type': 'interview or oral account', 'title': 'TEST FIXTURE — oral', 'creators': 'anonymous speaker', 'oral_permission': True},
        ]
        ident = self.store.submit(self.payload(relationship='source-based research', references=refs), self.owner)['id']
        self.assertAPIError(422, self.publish, ident)
        suggested = [x for x in self.store.private(self.owner) if x['kind'] == 'source']
        self.assertEqual(len(suggested), 4)
        for source in suggested:
            self.publish(source['id'])
        self.publish(ident)
        public = self.store.detail(ident, 'practice')
        self.assertEqual(len(public['citations']), 4)
        self.assertIn('account', [c['block_id'] for c in public['citations']])
        self.store.withdraw(self.owner, suggested[0]['id'])
        self.assertEqual(len(self.store.detail(ident, 'practice')['citations']), 3)
        self.assertNotIn('references', self.store.detail(ident, 'practice'))

    def test_invalid_urls_and_oral_permissions_rejected(self):
        for reference in [ {'type': 'blog or essay', 'title': 'x', 'url': 'javascript:alert(1)'}, {'type': 'interview or oral account', 'title': 'x', 'creators': 'someone'} ]:
            self.assertAPIError(422, self.store.submit, self.payload(references=[reference]), self.owner)

    def test_image_type_metadata_and_visibility_boundary(self):
        image = Image.new('RGB', (20, 20), 'red')
        out = io.BytesIO(); image.save(out, 'JPEG', exif=b'')
        payload = self.payload(images=[{'data': base64.b64encode(out.getvalue()).decode(), 'alt': 'A red square.', 'caption': 'A test image.', 'permission': True}])
        ident = self.store.submit(payload, self.owner)['id']
        media = self.store.private(self.owner, ident)['media']
        self.assertEqual(len(media), 1)
        with self.store.connect() as db:
            row = db.execute('SELECT * FROM media WHERE id=?', (media[0]['id'],)).fetchone()
        with Image.open(self.store.uploads / row['storage_key']) as clean:
            self.assertEqual(clean.format, 'WEBP')
            self.assertFalse(clean.getexif())
        self.assertAPIError(422, self.store.submit, self.payload(images=[{'data': base64.b64encode(b'<svg onload="bad"/>').decode(), 'alt': 'bad', 'permission': True}]), self.owner)

    def test_demo_never_appears_in_production_data_mode(self):
        local_id = self.store.submit(self.payload(), self.owner)['id']
        self.publish(local_id)
        prod = Store(self.tmp.name, demo=False)
        self.assertEqual(prod.collection('practice'), [])
        self.assertEqual(prod.collection('source'), [])
        self.assertAPIError(404, prod.detail, 'rice-water', 'practice')
        self.assertAPIError(404, prod.detail, local_id, 'practice')

    def test_editorial_preview_is_idempotent_and_does_not_revive_withdrawals(self):
        self.assertEqual(self.store.detail('experiments-with-rice', 'practice')['display_name'], 'Aditi Neti')
        self.assertFalse(self.store.detail('prasa', 'practice').get('fictional', False))
        editorial = self.login('editorial-preview@example.invalid')
        self.store.withdraw(editorial, 'editorial-prasa')
        reopened = Store(self.tmp.name, demo=True)
        self.assertAPIError(404, reopened.detail, 'prasa', 'practice')
        self.assertEqual(len([entry for entry in reopened.collection('practice') if entry['id'] == 'editorial-rice']), 1)

    def test_entry_type_is_preserved_without_granting_editorial_status(self):
        ident = self.store.submit(self.payload(entry_type='experiment', editorial=True), self.owner)['id']
        content = self.store.private(self.owner, ident)['content']
        self.assertEqual(content['entry_type'], 'experiment')
        self.assertNotIn('editorial', content)
        self.assertAPIError(422, self.store.submit, self.payload(entry_type='unsupported'), self.owner)

    def test_source_only_can_connect_to_multiple_practices(self):
        ident = self.store.submit(self.payload(kind='source', source={'type': 'book or chapter', 'title': 'TEST FIXTURE print source', 'annotation': 'A test annotation.', 'creators': ''}), self.owner)['id']
        self.publish(ident)
        links = [{'practice_id': p, 'relationship': 'further reading or viewing', 'annotation': 'A test connection.', 'locator': 'p. 2'} for p in ('demo-rice-water', 'demo-knitting-repeat')]
        self.assertAPIError(403, self.store.connect_source, self.other, ident, {'links': links})
        self.store.connect_source(self.editor, ident, {'links': links})
        for practice in ('rice-water', 'knitting-repeat'):
            self.assertIn(ident, [c['source_id'] for c in self.store.detail(practice, 'practice')['citations']])

    def test_editorial_messages_stay_private(self):
        ident = self.store.submit(self.payload(), self.owner)['id']
        self.assertAPIError(403, self.store.message, self.other, ident, 'not yours')
        self.store.message(self.owner, ident, 'PRIVATE editorial response')
        self.assertEqual(self.store.private(self.owner, ident)['messages'][0]['body'], 'PRIVATE editorial response')
        self.publish(ident)
        self.assertNotIn('PRIVATE', json.dumps(self.store.detail(ident, 'practice')))

    def test_citation_links_are_preserved_without_duplicating_print_sources(self):
        ident = self.store.submit(self.payload(references=[{'type': 'book or chapter', 'title': 'TEST FIXTURE — print', 'annotation': 'test', 'block_id': 'account'}]), self.owner)['id']
        source_id = next(x['id'] for x in self.store.private(self.owner) if x['kind'] == 'source')
        self.publish(source_id); self.publish(ident)
        existing = self.store.private(self.owner, ident)['content']
        self.store.submit({**existing, 'kind': 'practice', 'title': 'A revised account', 'publication_permission': True, 'rights_confirmation': True}, self.owner, ident)
        self.assertEqual(len([x for x in self.store.private(self.owner) if x['kind'] == 'source']), 1)
        self.publish(ident)
        self.assertEqual(self.store.detail(ident, 'practice')['citations'][0]['source_id'], source_id)

    def test_known_email_cannot_be_impersonated_by_anonymous_submission(self):
        ident = self.store.submit(self.payload(email='owner@example.test'))['id']
        # This email was verified earlier, but this particular submission was not.
        self.assertAPIError(422, self.publish, ident)
        self.assertAPIError(403, self.store.confirm, self.other, ident, {'publication_permission': True, 'rights_confirmation': True})
        self.store.confirm(self.owner, ident, {'publication_permission': True, 'rights_confirmation': True})
        self.publish(ident)
        self.assertEqual(self.store.detail(ident, 'practice')['id'], ident)

    def test_reference_editing_does_not_expose_another_sources_pending_revision(self):
        source_id = self.store.submit(self.payload(kind='source', source={'type': 'book or chapter', 'title': 'PUBLIC test source', 'annotation': 'Public test annotation.'}), self.other)['id']
        self.publish(source_id)
        ident = self.store.submit(self.payload(), self.owner)['id']
        self.publish(ident)
        self.store.connect_source(self.editor, source_id, {'links': [{'practice_id': ident, 'relationship': 'further reading or viewing', 'annotation': 'A test connection.'}]})
        self.store.submit(self.payload(kind='source', source={'type': 'book or chapter', 'title': 'PRIVATE source revision', 'annotation': 'PRIVATE source annotation.'}), self.other, source_id)
        own_account = json.dumps(self.store.private(self.owner, ident))
        self.assertNotIn('PRIVATE source', own_account)
        self.assertIn('PUBLIC test source', own_account)


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.base = 'http://127.0.0.1:' + str(cls.server.server_port)
        cls.store = Store(cls.tmp.name, base_url=cls.base)
        cls.server.store = cls.store
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.tmp.cleanup()

    def request(self, path, data=None, origin=None, cookie=None, csrf=None):
        headers = {'Content-Type': 'application/json'}
        if origin: headers['Origin'] = origin
        if cookie: headers['Cookie'] = cookie
        if csrf: headers['X-CSRF-Token'] = csrf
        request = urllib.request.Request(self.base + path, data=json.dumps(data).encode() if data is not None else None, headers=headers)
        try: return urllib.request.urlopen(request)
        except urllib.error.HTTPError as exc: return exc

    def test_private_files_and_routes_are_protected(self):
        for path in ['/js/app.js', '/css/notebook.css']:
            code = self.request(path)
            self.assertEqual(code.headers['Cache-Control'], 'no-cache')
            code.read()
        image = self.request('/assets/projects/prasa-example.png')
        self.assertEqual(image.status, 200)
        self.assertEqual(image.headers.get_content_type(), 'image/png')
        self.assertEqual(image.read()[:8], b'\x89PNG\r\n\x1a\n')
        for name in ['prasa-example.png', 'experiments-with-rice.JPG']:
            treated = self.request('/project-images/' + name)
            self.assertEqual(treated.status, 200)
            self.assertEqual(treated.headers.get_content_type(), 'image/webp')
            self.assertEqual(treated.headers['Cache-Control'], 'no-cache')
            self.assertEqual(treated.read()[:4], b'RIFF')
        for path in ['/project-images/../server/app.py', '/project-images/%2e%2e%2f.env', '/project-images/missing.jpg']:
            self.assertEqual(self.request(path).status, 404)
        for path in ['/data/demo.json', '/.runtime/mail.jsonl', '/.env', '/server/app.py', '/palette/image.png', '/references/image.png', '/api/mine', '/api/admin']:
            self.assertIn(self.request(path).status, (403, 404))
        for path in ['/', '/explore', '/practices/rice-water', '/sources/illustrative-rice-scenario', '/about', '/manage', '/admin']:
            response = self.request(path)
            self.assertEqual(response.status, 200)
            self.assertIn('Content-Security-Policy', response.headers)
        self.assertEqual(self.request('/practices/nonexistent').status, 404)
        self.assertIn(b'measuring with a fingertip', self.request('/practices/rice-water').read())

    def test_cross_origin_and_missing_csrf_rejected(self):
        self.assertEqual(self.request('/api/auth/request', {'email': 'test@example.test'}, 'https://other.test').status, 403)
        self.store.mail_link('session@example.test')
        token = json.loads((Path(self.tmp.name) / 'mail.jsonl').read_text().splitlines()[-1])['link'].split('token=')[1]
        response = self.request('/api/auth/verify', {'token': token}, self.base)
        cookie = response.headers['Set-Cookie'].split(';')[0]
        self.assertIn('HttpOnly', response.headers['Set-Cookie'])
        self.assertEqual(self.request('/api/auth/logout', {}, self.base, cookie).status, 403)
        session = json.load(self.request('/api/session', cookie=cookie))
        self.assertEqual(self.request('/api/auth/logout', {}, self.base, cookie, session['csrf']).status, 200)

    def test_unpublished_image_http_authorization(self):
        # Check the actual media route rather than only service-level metadata.
        self.store.mail_link('image-owner@example.test')
        token = json.loads((Path(self.tmp.name) / 'mail.jsonl').read_text().splitlines()[-1])['link'].split('token=')[1]
        session_token = self.store.verify(token)
        owner = self.store.session(session_token)
        out = io.BytesIO(); Image.new('RGB', (10, 10)).save(out, 'PNG')
        payload = {'kind': 'practice', 'title': 'Image test', 'summary': 'test', 'account': 'test', 'relationship': 'personal experience', 'publication_permission': True, 'rights_confirmation': True, 'images': [{'data': base64.b64encode(out.getvalue()).decode(), 'alt': 'test square', 'permission': True}]}
        ident = self.store.submit(payload, owner)['id']
        url = self.store.private(owner, ident)['media'][0]['url']
        self.assertEqual(self.request(url).status, 404)
        self.assertEqual(self.request(url, cookie='sc_session=' + session_token).status, 200)
        self.store.withdraw(owner, ident)
        self.assertEqual(self.request(url).status, 404)


if __name__ == '__main__':
    unittest.main()
