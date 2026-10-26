"""Exercise actual Postgres transactions in a disposable local database.

Start a temporary Postgres server, then run this file. This never connects to a
hosted Supabase project. SUPABASE_TEST_SOCKET must name a local Unix socket dir.
"""
import json
import os
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SupabaseDatabaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        socket = os.environ.get('SUPABASE_TEST_SOCKET', '/tmp/source-culture-supabase-pg')
        if not socket.startswith('/'):
            raise RuntimeError('Use an absolute local Unix socket directory, never a remote host.')
        cls.command = [shutil.which('psql') or 'psql', '-X', '-h', socket, '-p', os.environ.get('SUPABASE_TEST_PORT', '55483'), '-v', 'ON_ERROR_STOP=1', '-At']
        cls.database = 'source_culture_test_' + str(os.getpid())
        cls.psql('create database ' + cls.database, database='postgres')
        cls.psql("""do $$ begin
          if not exists(select 1 from pg_roles where rolname='anon') then create role anon nologin; end if;
          if not exists(select 1 from pg_roles where rolname='authenticated') then create role authenticated nologin; end if;
          if not exists(select 1 from pg_roles where rolname='service_role') then create role service_role nologin; end if;
        end $$;
        create schema storage;
        create table storage.buckets(id text primary key,name text,public boolean,file_size_limit bigint,allowed_mime_types text[]);
        """)
        for migration in sorted((ROOT / 'supabase/migrations').glob('*.sql')):
            cls.psql(migration.read_text())

    @classmethod
    def tearDownClass(cls):
        cls.psql('drop database ' + cls.database, database='postgres')

    @classmethod
    def psql(cls, sql, database=None, fail=False):
        result = subprocess.run(cls.command + ['-d', database or cls.database], input=sql, text=True, capture_output=True)
        if fail:
            if result.returncode == 0:
                raise AssertionError('Expected database access to be rejected.')
            return result.stderr
        if result.returncode:
            raise AssertionError(result.stderr)
        return result.stdout.strip()

    def rpc(self, path, payload=None, email=None, editor=False, fail=False):
        quote = lambda value: "'" + str(value).replace("'", "''") + "'"
        query = 'select public.source_culture_api(' + ','.join([
            quote(path), quote('POST' if payload is not None else 'GET'), quote(json.dumps(payload or {})) + '::jsonb',
            'null' if email is None else quote(email), 'true' if editor else 'false']) + ');'
        output = self.psql(query, fail=fail)
        return output if fail else json.loads(output)

    def submit(self, email, *, signed=False, references=None, media=None, revision=None, kind='practice', **content):
        c = {'title': 'Rice ' + str(os.urandom(4).hex()), 'summary': 'A small practice', 'account': 'A firsthand account',
             'relationship': 'personal experience', 'display_name': 'Contributor', 'tags': [],
             'reuse': 'credit; no additional reuse licence', 'references': references or [], **content}
        payload = {'kind': kind, 'email': email, 'content': c, 'media': media or [], 'keep_media': [], 'parent_id': None, 'target_id': None}
        return self.rpc('/submissions/' + revision + '/revisions' if revision else '/submissions', payload, email if signed else None)['id']

    def publish(self, ident, *, fail=False):
        items = self.rpc('/admin', email='editor@example.test', editor=True)
        item = next(row for row in items if row['id'] == ident)
        return self.rpc('/admin/' + ident + '/review', {'action': 'published', 'revision_id': item['revision_id'], 'links': []},
                        'editor@example.test', True, fail=fail)

    def test_browser_roles_cannot_read_tables_or_impersonate_rpc_identity(self):
        for role in ['anon', 'authenticated']:
            for query in ['select * from source_culture.contributors', "select public.source_culture_api('/admin','GET','{}','editor@example.test',true)"]:
                self.assertIn('permission denied', self.psql('set role ' + role + ';' + query, fail=True))
        self.assertEqual(self.psql("set role service_role; select jsonb_typeof(public.source_culture_api('/practices'));"), 'SET\narray')
        self.assertEqual(self.psql("select public from storage.buckets where id='source-culture-media'"), 'f')

    def test_anonymous_submission_requires_confirmation_even_for_known_verified_email(self):
        owner = 'known@example.test'
        self.rpc('/session', email=owner)
        ident = self.submit(owner)
        self.assertIn('confirm this specific account', self.publish(ident, fail=True))
        self.rpc('/submissions/' + ident + '/confirm', {'publication_permission': True, 'rights_confirmation': True}, owner)
        self.publish(ident)
        public = self.rpc('/practices/' + ident)
        self.assertEqual(public['id'], ident)
        for private in ['email', 'owner_id', 'permission', 'confirmed', 'references', 'feedback', 'messages']:
            self.assertNotIn(private, public)
        self.assertIn('own contribution', self.rpc('/submissions/' + ident + '/withdraw', {}, 'other@example.test', fail=True))

    def test_pending_revision_stale_review_and_withdrawn_media(self):
        owner = 'images@example.test'
        image = {'id': 'image-' + os.urandom(4).hex(), 'storage_key': 'private.webp', 'alt': 'Rice', 'caption': '', 'credit': '', 'licence': 'no additional reuse licence'}
        ident = self.submit(owner, signed=True, media=[image], title='Original title')
        self.publish(ident)
        self.assertEqual(self.rpc('/media/' + image['id']), {'storage_key': 'private.webp'})
        self.assertEqual(self.psql("select public.source_culture_unused_media(array['private.webp','orphan.webp'])"), '{orphan.webp}')
        self.assertIn('Image unavailable', self.rpc('/media/missing', fail=True))
        self.submit(owner, signed=True, revision=ident, title='Proposed title')
        old = self.rpc('/submissions/' + ident, email=owner)
        self.submit(owner, signed=True, revision=ident, title='Newest title')
        self.assertEqual(self.rpc('/practices/' + ident)['title'], 'Original title')
        self.assertIn('changed or was already reviewed', self.rpc('/admin/' + ident + '/review', {'action': 'published', 'revision_id': old['revision_id']}, 'editor@example.test', True, fail=True))
        self.publish(ident)
        self.assertEqual(self.rpc('/practices/' + ident)['title'], 'Newest title')
        self.assertIn('Image unavailable', self.rpc('/media/' + image['id'], fail=True))
        self.assertEqual(self.rpc('/media/' + image['id'], email=owner), {'storage_key': 'private.webp'})
        self.rpc('/submissions/' + ident + '/withdraw', {}, owner)
        self.assertIn('unavailable', self.rpc('/practices/' + ident, fail=True))
        self.assertIn('unavailable', self.publish(ident, fail=True))

    def test_sources_are_separately_reviewed_and_withdrawals_hide_citations(self):
        owner = 'references@example.test'
        ref = {'type': 'book or chapter', 'title': 'A print reference', 'creators': 'Author', 'date': '', 'url': '', 'doi': '',
               'source_id': '', 'relation': 'documents this practice', 'locator': 'page 3', 'annotation': 'Documents this account', 'block_id': 'account'}
        ident = self.submit(owner, signed=True, references=[ref])
        self.assertIn('linked source suggestions', self.publish(ident, fail=True))
        source = next(item for item in self.rpc('/mine', email=owner) if item['kind'] == 'source')
        self.publish(source['id'])
        self.publish(ident)
        self.assertEqual(len(self.rpc('/practices/' + ident)['citations']), 1)
        self.submit(owner, signed=True, revision=source['id'], kind='source', title='Private metadata', source={**ref, 'title': 'Private metadata'})
        self.assertEqual(self.rpc('/sources/' + source['id'])['title'], 'A print reference')
        self.rpc('/submissions/' + source['id'] + '/withdraw', {}, owner)
        self.assertEqual(self.rpc('/practices/' + ident)['citations'], [])

    def test_bad_references_roll_back_entities_permissions_and_images(self):
        before = self.psql('select count(*) from source_culture.entities')
        payload = {'kind': 'practice', 'email': 'rollback@example.test', 'content': {'title': 'Should roll back', 'reuse': 'credit',
                   'references': [{'source_id': 'missing', 'title': 'Missing'}]}, 'media': [], 'keep_media': []}
        self.assertIn('linked source is unavailable', self.rpc('/submissions', payload, fail=True))
        self.assertEqual(self.psql('select count(*) from source_culture.entities'), before)

    def test_rate_limits_are_shared_across_function_instances(self):
        self.assertEqual(self.psql("select public.source_culture_rate_limit('test',1,600);"), 't')
        self.assertEqual(self.psql("select public.source_culture_rate_limit('test',1,600);"), 'f')

    def test_withdrawal_hides_all_descendant_variations_and_their_images(self):
        owner = 'variations@example.test'
        parent = self.submit(owner, signed=True)
        self.publish(parent)
        descendants = []
        for level in range(2):
            payload = {'kind': 'variation', 'email': owner, 'content': {'title': 'Variation ' + str(level), 'reuse': 'credit', 'references': []},
                       'parent_id': parent, 'target_id': None, 'media': [], 'keep_media': []}
            parent = self.rpc('/submissions', payload, owner)['id']
            descendants.append(parent)
            self.publish(parent)
        first = self.rpc('/practices/' + descendants[0])['parent_id']
        self.rpc('/submissions/' + first + '/withdraw', {}, owner)
        for ident in descendants:
            self.assertIn('unavailable', self.rpc('/practices/' + ident, fail=True))

    def test_editorial_import_is_idempotent_and_preserves_withdrawals(self):
        self.assertEqual(self.rpc('/practices/editorial-rice')['title'], 'experiments with rice')
        self.psql("update source_culture.entities set status='withdrawn' where id='editorial-rice'")
        self.psql((ROOT / 'supabase/migrations/202610260002_editorial.sql').read_text())
        self.assertIn('unavailable', self.rpc('/practices/editorial-rice', fail=True))


if __name__ == '__main__':
    unittest.main(verbosity=2)
