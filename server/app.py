"""Small local reference API. All public responses are explicit allowlists.

Python's HTTP server is for local development. See README before production use.
"""
import argparse
import base64
import hashlib
import html
import io
import json
import mimetypes
import os
import re
import secrets
import smtplib
import sqlite3
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from email.message import EmailMessage
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlparse, urlencode, urlunparse

if __package__:
    from .project_images import render_project_image
else:
    from project_images import render_project_image

ROOT = Path(__file__).resolve().parent.parent
ACTIVITIES = ['food and cooking', 'craft and making', 'games and play', 'remembering and recording', 'exchange and sharing', 'navigation and place', 'everyday coordination']
SOURCE_TYPES = ['academic article', 'book or chapter', 'thesis or dissertation', 'video', 'blog or essay', 'project documentation', 'podcast or audio', 'interview or oral account', 'archive or exhibition', 'other']
RELATIONSHIPS = ['documents this practice', 'supports this specific claim', 'informs this interpretation', 'offers a related example', 'further reading or viewing']
EMAIL = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def uid():
    return secrets.token_hex(12)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def canonical_url(value):
    if not value:
        return ''
    url = urlparse(value)
    query = [(k, v) for k, v in parse_qsl(url.query) if not k.startswith('utm_')]
    return urlunparse((url.scheme.lower(), url.netloc.lower(), url.path.rstrip('/'), '', urlencode(query), ''))


class APIError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message


class Store:
    def __init__(self, directory, demo=True, editors=(), base_url='http://127.0.0.1:8000', *, include_fixtures=False):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.uploads = self.directory / 'uploads'
        self.uploads.mkdir(exist_ok=True)
        self.demo, self.editors, self.base_url = demo, set(editors), base_url.rstrip('/')
        self.db_path = self.directory / 'collection.sqlite3'
        with self.connect() as db:
            db.executescript((ROOT / 'server/migrations/001_initial.sql').read_text())
        if demo:
            if include_fixtures:
                self.seed()
            else:
                self.withdraw_fixtures()
            self.seed_editorial()

    def connect(self):
        db = sqlite3.connect(self.db_path, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('PRAGMA journal_mode=WAL')
        return db

    def identity(self, db, email):
        email = str(email).strip().lower()
        if not EMAIL.fullmatch(email) or len(email) > 254:
            raise APIError(422, 'Enter a valid private email address.')
        row = db.execute('SELECT * FROM contributors WHERE email=?', (email,)).fetchone()
        if row:
            return row['id']
        ident = uid()
        db.execute('INSERT INTO contributors VALUES (?,?,0,?)', (ident, email, now()))
        return ident

    def mail_link(self, email):
        if not self.demo and not os.getenv('SMTP_HOST'):
            raise APIError(503, 'Email delivery is not configured. Your input has been preserved.')
        token = secrets.token_urlsafe(32)
        with self.connect() as db:
            owner = self.identity(db, email)
            db.execute('INSERT INTO login_tokens VALUES (?,?,?)', (digest(token), owner, time.time() + 900))
        link = self.base_url + '/manage#token=' + token
        if self.demo:
            # Private local development outbox. Never served over HTTP or returned by the API.
            with (self.directory / 'mail.jsonl').open('a') as out:
                out.write(json.dumps({'to': email, 'link': link, 'created_at': now()}) + '\n')
            os.chmod(self.directory / 'mail.jsonl', 0o600)
        else:
            msg = EmailMessage()
            msg['Subject'], msg['From'], msg['To'] = 'Your Source Culture sign-in link', os.environ['SMTP_FROM'], email
            msg.set_content('Sign in within 15 minutes. This link works once:\n' + link)
            try:
                with smtplib.SMTP(os.environ['SMTP_HOST'], int(os.getenv('SMTP_PORT', '587')), timeout=15) as smtp:
                    smtp.starttls()
                    if os.getenv('SMTP_USER'):
                        smtp.login(os.environ['SMTP_USER'], os.environ['SMTP_PASSWORD'])
                    smtp.send_message(msg)
            except (OSError, smtplib.SMTPException) as exc:
                raise APIError(503, 'Email could not be delivered. Please try again.') from exc

    def verify(self, token):
        session, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(24)
        with self.connect() as db:
            # Acquire a write lock before reading: a link cannot establish two sessions.
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM login_tokens WHERE digest=? AND expires>?', (digest(token), time.time())).fetchone()
            if not row:
                raise APIError(401, 'This link has expired or was already used. Request a new link.')
            db.execute('DELETE FROM login_tokens WHERE digest=?', (digest(token),))
            db.execute('UPDATE contributors SET verified=1 WHERE id=?', (row['contributor_id'],))
            db.execute('INSERT INTO sessions VALUES (?,?,?,?)', (digest(session), row['contributor_id'], csrf, time.time() + 28800))
        return session

    def session(self, token):
        with self.connect() as db:
            row = db.execute('SELECT contributors.*, sessions.csrf FROM sessions JOIN contributors ON contributors.id=sessions.contributor_id WHERE sessions.digest=? AND sessions.expires>?', (digest(token), time.time())).fetchone()
        if not row:
            return None
        return {**dict(row), 'editor': row['email'] in self.editors}

    def visible(self, db, row):
        if not row or row['status'] != 'published' or (row['demo'] and not self.demo):
            return False
        if row['parent_id']:
            parent = db.execute('SELECT * FROM entities WHERE id=?', (row['parent_id'],)).fetchone()
            return bool(parent and parent['status'] == 'published' and (self.demo or not parent['demo']))
        return True

    def public(self, db, row):
        rev = db.execute('SELECT * FROM revisions WHERE id=?', (row['published_revision_id'],)).fetchone()
        content = json.loads(rev['content'])
        # References are resolved through live citation/source visibility checks below.
        # In particular, withdrawing a source must not leak its old metadata here.
        content.pop('references', None)
        if row['demo'] and row['id'].startswith('demo-'):
            content['fictional'] = True
        # Stored content has already been validated and contains only public fields.
        return {**content, 'id': row['id'], 'slug': row['slug'], 'kind': row['kind'], 'parent_id': row['parent_id'], 'demo': bool(row['demo']), 'created_at': row['created_at'], 'updated_at': rev['created_at'], 'revision': rev['number'], 'media': [self.public_media(m) for m in db.execute('SELECT * FROM media WHERE revision_id=?', (rev['id'],))], 'citations': [dict(c) for c in db.execute('SELECT citations.* FROM citations JOIN entities ON entities.id=citations.source_id WHERE revision_id=? AND entities.status="published" AND (entities.demo=0 OR ?=1)', (rev['id'], int(self.demo)))]}

    @staticmethod
    def public_media(row):
        return {'id': row['id'], 'url': '/media/' + row['id'], 'alt': row['alt'], 'caption': row['caption'], 'credit': row['credit'], 'licence': row['licence']}

    def collection(self, kind):
        with self.connect() as db:
            rows = db.execute('SELECT * FROM entities ORDER BY updated_at DESC').fetchall()
            return [self.public(db, r) for r in rows if (r['kind'] in ('practice', 'variation') if kind == 'practice' else r['kind'] == kind) and self.visible(db, r)]

    def detail(self, slug, kind):
        with self.connect() as db:
            row = db.execute('SELECT * FROM entities WHERE (slug=? OR id=?) AND kind IN (?,?)', (slug, slug, kind, 'variation' if kind == 'practice' else kind)).fetchone()
            if not row:
                alias = db.execute('SELECT entities.* FROM aliases JOIN entities ON entities.id=aliases.entity_id WHERE aliases.slug=?', (slug,)).fetchone()
                if alias and self.visible(db, alias):
                    return {'redirect': alias['slug']}
            if not self.visible(db, row):
                raise APIError(404, 'This entry is unavailable. It may have been withdrawn or is not published.')
            return self.public(db, row)

    def validate(self, payload, kind):
        if not isinstance(payload, dict):
            raise APIError(422, 'A contribution must be an object.')
        def field(name, required=False, limit=12000):
            value = payload.get(name, '')
            if not isinstance(value, str) or len(value) > limit:
                raise APIError(422, f'{name.replace("_", " ")} is too long or has an invalid format.')
            value = value.strip()
            if required and not value:
                raise APIError(422, f'Please complete {name.replace("_", " ")}.')
            return value
        content = {name: field(name, name in ('title',), 400 if name == 'title' else 12000) for name in ['title', 'summary', 'original_name', 'language', 'context', 'place', 'community', 'relationship', 'account', 'materials', 'steps', 'judgement', 'similar', 'changes', 'prompt', 'display_name', 'reuse']}
        content['display_name'] = content['display_name'] or 'anonymous contributor'
        content['reuse'] = content['reuse'] or 'credit; no additional reuse licence'
        content['entry_type'] = field('entry_type', limit=80) or 'practice'
        if content['entry_type'] not in ('project', 'practice', 'experiment'):
            raise APIError(422, 'Choose project, practice, or experiment.')
        tags = payload.get('tags', [])
        if not isinstance(tags, list) or len(tags) > 12 or any(not isinstance(t, str) or len(t) > 80 for t in tags):
            raise APIError(422, 'Use at most 12 short activity or suggested tags.')
        content['tags'] = tags
        if payload.get('publication_permission') is not True or payload.get('rights_confirmation') is not True:
            raise APIError(422, 'Publication permission and confirmation that you may share this material are required.')
        if kind in ('practice', 'variation'):
            for name in ('summary', 'relationship', 'account'):
                if not content[name]:
                    raise APIError(422, f'Please complete {name.replace("_", " ")}.')
            if content['relationship'] not in ('personal experience', 'learned from someone', 'observation', 'source-based research'):
                raise APIError(422, 'Choose how you know this practice.')
            if kind == 'variation' and (not content['similar'] or not content['changes']):
                raise APIError(422, 'Describe what is similar and what changes in your variation.')
        refs = payload.get('references', [])
        if not isinstance(refs, list) or len(refs) > 20:
            raise APIError(422, 'Use at most 20 sources.')
        content['references'] = [self.validate_source(s) for s in refs]
        for reference in content['references']:
            block_field = {'story': 'context', 'account': 'account', 'judgement': 'judgement'}.get(reference['block_id'])
            if block_field and not content.get(block_field):
                raise APIError(422, 'The citation points to an empty passage. Add that passage or choose further reading without a passage.')
        if content['relationship'] == 'source-based research' and not refs:
            raise APIError(422, 'A source-based account needs at least one identified source. Print and oral sources do not need a URL.')
        if kind == 'source':
            content['source'] = self.validate_source(payload.get('source', {}))
            content['title'] = content['source']['title']
            if not content['source']['annotation']:
                raise APIError(422, 'Explain why this source is relevant.')
        if kind == 'correction' and not content['account']:
            raise APIError(422, 'Please describe the correction.')
        # Computational readings are editorial interpretations and cannot be silently generated.
        return content

    def validate_source(self, source):
        if not isinstance(source, dict):
            raise APIError(422, 'Check the source details.')
        keys = ['source_id', 'type', 'title', 'creators', 'date', 'language', 'url', 'access_date', 'annotation', 'doi', 'venue', 'volume', 'pages', 'publisher', 'edition', 'chapter', 'isbn', 'platform', 'duration', 'locator', 'interviewer', 'recording', 'translation', 'custom_type', 'relation', 'block_id']
        result = {}
        for key in keys:
            value = source.get(key, '')
            if not isinstance(value, str) or len(value) > 4000:
                raise APIError(422, 'A source field is invalid or too long.')
            result[key] = value.strip()
        if result['type'] not in SOURCE_TYPES or not result['title']:
            raise APIError(422, 'Every source needs a type and a title or descriptive label.')
        if result['url']:
            url = urlparse(result['url'])
            if url.scheme not in ('http', 'https') or not url.hostname or url.username or url.password:
                raise APIError(422, 'Source links must be ordinary HTTP or HTTPS URLs.')
        if result['type'] == 'interview or oral account' and source.get('oral_permission') is not True:
            raise APIError(422, 'Confirm permission to share an attributed oral account, or use an anonymised descriptive reference you may share.')
        result['oral_permission'] = source.get('oral_permission') is True
        result['relation'] = result['relation'] or 'further reading or viewing'
        if result['relation'] not in RELATIONSHIPS:
            raise APIError(422, 'Choose how this source relates to the practice.')
        if result['block_id'] not in ('', 'story', 'account', 'judgement'):
            raise APIError(422, 'Choose a valid passage for the citation.')
        return result

    def attach_image(self, db, rev_id, owner, image):
        from PIL import Image, ImageOps, UnidentifiedImageError
        if not isinstance(image, dict) or not image.get('alt', '').strip() or image.get('permission') is not True:
            raise APIError(422, 'Images need an accessible description and your permission to publish them.')
        try:
            raw = base64.b64decode(image.get('data', ''), validate=True)
            if len(raw) > 5 * 1024 * 1024:
                raise APIError(422, 'Each image must be smaller than 5 MB.')
            with Image.open(io.BytesIO(raw)) as im:
                if im.format not in ('JPEG', 'PNG', 'WEBP') or im.width * im.height > 24000000:
                    raise APIError(422, 'Use a JPEG, PNG, or WebP image of at most 24 megapixels.')
                im.load()
                clean = ImageOps.exif_transpose(im).convert('RGB')
                clean.thumbnail((1800, 1800))
                ident = uid()
                key = ident + '.webp'
                # Fresh image has no EXIF, GPS, or inherited text metadata.
                clean.save(self.uploads / key, 'WEBP', quality=84, exif=b'')
        except (ValueError, OSError, UnidentifiedImageError, Image.DecompressionBombError) as exc:
            raise APIError(422, 'That file is not a supported image. Use JPEG, PNG, or WebP.') from exc
        db.execute('INSERT INTO media VALUES (?,?,?,?,?,?,?,?,?)', (ident, rev_id, owner, key, str(image['alt'])[:2000], str(image.get('caption', ''))[:2000], str(image.get('credit', ''))[:400], 1, str(image.get('licence', 'no additional reuse licence'))[:200]))

    def insert_entity(self, db, owner, kind, content, parent=None, target=None, demo=False):
        ident, rev_id, timestamp = uid(), uid(), now()
        slug = re.sub(r'[^a-z0-9]+', '-', content['title'].lower()).strip('-')[:70] or 'practice'
        slug += '-' + ident[:6]
        db.execute('INSERT INTO entities VALUES (?,?,?,?,?,?,?,NULL,?,?,?)', (ident, kind, slug, owner, parent, target, 'submitted', int(demo), timestamp, timestamp))
        db.execute('INSERT INTO revisions VALUES (?,?,1,?,?,?)', (rev_id, ident, json.dumps(content, ensure_ascii=False), 'submitted', timestamp))
        return ident, rev_id

    def save_revision(self, db, rev_id, owner, content, payload, demo=False):
        db.execute('INSERT INTO permissions VALUES (?,?,?,?,?,?,?)', (uid(), rev_id, owner, '2026-10-v1', 1, content['reuse'], now()))
        images = payload.get('images', [])
        if not isinstance(images, list) or len(images) > 4:
            raise APIError(422, 'Attach at most four images.')
        for image in images:
            self.attach_image(db, rev_id, owner, image)
        kept = payload.get('keep_media', [])
        if not isinstance(kept, list) or len(kept) + len(images) > 4:
            raise APIError(422, 'Keep at most four images per contribution.')
        for media_id in kept:
            m = db.execute('SELECT * FROM media WHERE id=? AND owner_id=?', (media_id, owner)).fetchone()
            if not m:
                raise APIError(403, 'You cannot attach that image.')
            db.execute('INSERT INTO media VALUES (?,?,?,?,?,?,?,?,?)', (uid(), rev_id, owner, m['storage_key'], m['alt'], m['caption'], m['credit'], m['permission'], m['licence']))
        for source in content.get('references', []):
            # Each suggestion has a separate review state. A citation never makes a source public.
            source_id = None
            changed_reference = False
            if source.get('source_id'):
                existing = db.execute('SELECT * FROM entities WHERE id=? AND kind="source"', (source['source_id'],)).fetchone()
                if not existing or existing['status'] == 'withdrawn' or (existing['demo'] and not self.demo) or not (self.visible(db, existing) or existing['owner_id'] == owner):
                    raise APIError(422, 'A linked source is unavailable. Remove it or ask an editor to clarify the reference.')
                existing_rev = db.execute('SELECT content FROM revisions WHERE entity_id=? ORDER BY number DESC LIMIT 1', (existing['id'],)).fetchone() if existing['owner_id'] == owner else db.execute('SELECT content FROM revisions WHERE id=?', (existing['published_revision_id'],)).fetchone()
                metadata = json.loads(existing_rev['content'])['source']
                bibliographic = ('type', 'title', 'creators', 'date', 'url', 'doi', 'venue', 'volume', 'pages', 'publisher', 'edition', 'chapter', 'isbn', 'platform', 'duration', 'interviewer', 'recording', 'translation', 'custom_type')
                changed_reference = any(source.get(k, '') != metadata.get(k, '') for k in bibliographic)
                if not changed_reference:
                    source_id = existing['id']
            if not source_id and not changed_reference and (source['url'] or source['doi']):
                for existing in db.execute('SELECT entities.id, revisions.content FROM entities JOIN revisions ON revisions.id=entities.published_revision_id WHERE entities.kind="source" AND entities.status="published" AND (entities.demo=0 OR ?=1)', (int(self.demo),)):
                    metadata = json.loads(existing['content'])['source']
                    same_doi = source['doi'] and source['doi'].lower().removeprefix('https://doi.org/') == metadata.get('doi', '').lower().removeprefix('https://doi.org/')
                    same_url = source['url'] and canonical_url(source['url']) == canonical_url(metadata.get('url', ''))
                    if (same_doi or same_url) and all(source.get(k, '') == metadata.get(k, '') for k in ('edition', 'title', 'creators', 'date')):
                        source_id = existing['id']
                        break
            if not source_id:
                source_content = {'title': source['title'], 'source': source, 'display_name': content['display_name'], 'tags': content['tags'], 'reuse': content['reuse']}
                source_id, source_rev = self.insert_entity(db, owner, 'source', source_content, demo=demo)
                db.execute('INSERT INTO permissions VALUES (?,?,?,?,?,?,?)', (uid(), source_rev, owner, '2026-10-v1', 1, content['reuse'], now()))
            db.execute('INSERT INTO citations VALUES (?,?,?,?,?,?,?)', (uid(), rev_id, source['block_id'] or None, source_id, source['relation'], source['locator'], source['annotation']))

    def submit(self, payload, user=None, entity_id=None):
        kind = payload.get('kind', 'practice')
        if kind not in ('practice', 'variation', 'source', 'correction'):
            raise APIError(422, 'Choose a contribution type.')
        content = self.validate(payload, kind)
        with self.connect() as db:
            if entity_id:
                row = db.execute('SELECT * FROM entities WHERE id=?', (entity_id,)).fetchone()
                if not user or not row or row['owner_id'] != user['id']:
                    raise APIError(403, 'You can only revise your own contribution.')
                if row['status'] == 'withdrawn' or row['kind'] != kind:
                    raise APIError(409, 'This contribution cannot be revised.')
                rev_id = uid()
                number = db.execute('SELECT MAX(number) FROM revisions WHERE entity_id=?', (entity_id,)).fetchone()[0] + 1
                db.execute('INSERT INTO revisions VALUES (?,?,?,?,?,?)', (rev_id, entity_id, number, json.dumps(content, ensure_ascii=False), 'submitted', now()))
                db.execute('UPDATE entities SET updated_at=? WHERE id=?', (now(), entity_id))
                owner = user['id']
            else:
                owner = user['id'] if user else self.identity(db, payload.get('email', ''))
                parent, target = payload.get('parent_id') or None, payload.get('target_id') or None
                if kind == 'variation' and not parent:
                    raise APIError(422, 'A variation needs a published parent practice.')
                for linked in (parent, target):
                    if linked:
                        row = db.execute('SELECT * FROM entities WHERE id=?', (linked,)).fetchone()
                        if not self.visible(db, row):
                            raise APIError(422, 'The entry you are responding to is unavailable.')
                if parent:
                    if db.execute('SELECT kind FROM entities WHERE id=?', (parent,)).fetchone()[0] not in ('practice', 'variation'):
                        raise APIError(422, 'A variation must refer to a practice.')
                entity_id, rev_id = self.insert_entity(db, owner, kind, content, parent, target, demo=self.demo)
            self.save_revision(db, rev_id, owner, content, payload, demo=self.demo)
            if user:
                self.confirm_revision(db, rev_id, owner)
        return {'id': entity_id, 'message': 'Saved to the review queue. It is not public.', 'email_delivery': 'not requested'}

    def confirm_revision(self, db, rev_id, owner):
        db.execute('INSERT OR IGNORE INTO confirmations VALUES (?,?,?)', (rev_id, owner, now()))
        for row in db.execute('SELECT entities.id FROM citations JOIN entities ON entities.id=citations.source_id WHERE citations.revision_id=? AND entities.owner_id=?', (rev_id, owner)):
            source_rev = db.execute('SELECT id FROM revisions WHERE entity_id=? ORDER BY number DESC LIMIT 1', (row['id'],)).fetchone()
            db.execute('INSERT OR IGNORE INTO confirmations VALUES (?,?,?)', (source_rev['id'], owner, now()))

    def confirm(self, user, entity_id, payload):
        if not user:
            raise APIError(401, 'Sign in first.')
        if payload.get('publication_permission') is not True or payload.get('rights_confirmation') is not True:
            raise APIError(422, 'Confirm that this is your account and you approve its recorded sharing permissions.')
        with self.connect() as db:
            row = db.execute('SELECT * FROM entities WHERE id=? AND owner_id=?', (entity_id, user['id'])).fetchone()
            if not row or row['status'] == 'withdrawn':
                raise APIError(403, 'You can only confirm your own active contribution.')
            revision = db.execute('SELECT id FROM revisions WHERE entity_id=? ORDER BY number DESC LIMIT 1', (entity_id,)).fetchone()
            self.confirm_revision(db, revision['id'], user['id'])
        return {'message': 'Your account and sharing permissions are confirmed. An editor can now review it for publication.'}

    def private(self, user, entity_id=None, admin=False):
        if not user or (admin and not user['editor']):
            raise APIError(403, 'Sign in with an authorised account to continue.')
        with self.connect() as db:
            rows = db.execute('SELECT * FROM entities ORDER BY updated_at DESC').fetchall()
            result = []
            for row in rows:
                if entity_id and row['id'] != entity_id:
                    continue
                if not admin and row['owner_id'] != user['id']:
                    continue
                if row['demo'] and not self.demo:
                    continue
                rev = db.execute('SELECT * FROM revisions WHERE entity_id=? ORDER BY number DESC LIMIT 1', (row['id'],)).fetchone()
                person = db.execute('SELECT * FROM contributors WHERE id=?', (row['owner_id'],)).fetchone()
                published = db.execute('SELECT content FROM revisions WHERE id=?', (row['published_revision_id'],)).fetchone()
                content = json.loads(rev['content'])
                if row['kind'] in ('practice', 'variation'):
                    content['references'] = []
                    for citation in db.execute('SELECT * FROM citations WHERE revision_id=? ORDER BY rowid', (rev['id'],)):
                        source_entity = db.execute('SELECT * FROM entities WHERE id=?', (citation['source_id'],)).fetchone()
                        if source_entity['owner_id'] == user['id'] or user['editor']:
                            source_rev = db.execute('SELECT content FROM revisions WHERE entity_id=? ORDER BY number DESC LIMIT 1', (citation['source_id'],)).fetchone()
                        else:
                            source_rev = db.execute('SELECT content FROM revisions WHERE id=?', (source_entity['published_revision_id'],)).fetchone()
                        if source_rev:
                            source = json.loads(source_rev['content'])['source']
                            content['references'].append({**source, 'source_id': citation['source_id'], 'relation': citation['relationship'], 'locator': citation['locator'] or '', 'annotation': citation['annotation'] or '', 'block_id': citation['block_id'] or ''})
                permission = db.execute('SELECT publication, reuse, consent_version, created_at FROM permissions WHERE revision_id=?', (rev['id'],)).fetchone()
                confirmed = db.execute('SELECT 1 FROM confirmations WHERE revision_id=?', (rev['id'],)).fetchone()
                result.append({**dict(row), 'content': content, 'revision_id': rev['id'], 'number': rev['number'], 'revision_state': rev['state'], 'permission': dict(permission) if permission else None, 'confirmed': bool(confirmed), 'email': person['email'], 'email_verified': bool(person['verified']), 'published_content': json.loads(published[0]) if published else None, 'media': [self.public_media(m) for m in db.execute('SELECT * FROM media WHERE revision_id=?', (rev['id'],))], 'feedback': [dict(r) for r in db.execute('SELECT action, feedback, created_at FROM reviews WHERE entity_id=? ORDER BY created_at DESC, rowid DESC', (row['id'],))], 'messages': [dict(m) for m in db.execute('SELECT body, created_at, author_id FROM messages WHERE entity_id=? ORDER BY created_at, rowid', (row['id'],))]})
        if entity_id and not result:
            raise APIError(404, 'Contribution not found in your account.')
        return result[0] if entity_id else result

    def withdraw(self, user, entity_id):
        if not user:
            raise APIError(401, 'Sign in first.')
        with self.connect() as db:
            result = db.execute('UPDATE entities SET status="withdrawn", updated_at=? WHERE id=? AND owner_id=?', (now(), entity_id, user['id']))
            if not result.rowcount:
                raise APIError(403, 'You can only withdraw your own contribution.')
        return {'message': 'Withdrawn. The contribution and its media are no longer public.'}

    def message(self, user, entity_id, body):
        if not user:
            raise APIError(401, 'Sign in first.')
        body = str(body).strip()
        if not body or len(body) > 12000:
            raise APIError(422, 'Write a private response of at most 12,000 characters.')
        with self.connect() as db:
            row = db.execute('SELECT * FROM entities WHERE id=?', (entity_id,)).fetchone()
            if not row or not (user['editor'] or row['owner_id'] == user['id']):
                raise APIError(403, 'You cannot respond to this contribution.')
            db.execute('INSERT INTO messages VALUES (?,?,?,?,?)', (uid(), entity_id, user['id'], body, now()))
        return {'message': 'Your private response has been saved for editorial review.'}

    def link_sources(self, db, source_id, links):
        if not isinstance(links, list) or len(links) > 50:
            raise APIError(422, 'Use at most 50 source connections.')
        for connection in links:
            practice = db.execute('SELECT * FROM entities WHERE id=?', (connection.get('practice_id'),)).fetchone()
            if not self.visible(db, practice) or practice['kind'] not in ('practice', 'variation'):
                raise APIError(422, 'Source connections need published practices.')
            if connection.get('relationship') not in RELATIONSHIPS or not str(connection.get('annotation', '')).strip():
                raise APIError(422, 'Explain how the source relates to each practice.')
            block = connection.get('block_id') or None
            if block not in (None, 'story', 'account', 'judgement'):
                raise APIError(422, 'Choose a stable passage identifier.')
            if block:
                published = json.loads(db.execute('SELECT content FROM revisions WHERE id=?', (practice['published_revision_id'],)).fetchone()[0])
                if not published.get({'story': 'context', 'account': 'account', 'judgement': 'judgement'}[block]):
                    raise APIError(422, 'That practice has no text in the selected passage. Choose another passage or further reading.')
            db.execute('INSERT INTO citations VALUES (?,?,?,?,?,?,?)', (uid(), practice['published_revision_id'], block, source_id, connection['relationship'], str(connection.get('locator', ''))[:1000], str(connection['annotation'])[:4000]))

    def connect_source(self, user, entity_id, payload):
        if not user or not user['editor']:
            raise APIError(403, 'Only editors can connect a reviewed source.')
        with self.connect() as db:
            row = db.execute('SELECT * FROM entities WHERE id=?', (entity_id,)).fetchone()
            if not self.visible(db, row) or row['kind'] != 'source':
                raise APIError(404, 'The source is unavailable.')
            if not payload.get('links'):
                raise APIError(422, 'Add at least one source connection.')
            self.link_sources(db, entity_id, payload['links'])
            db.execute('INSERT INTO reviews VALUES (?,?,?,?,?,?,?)', (uid(), entity_id, row['published_revision_id'], user['id'], 'connections', 'Editor added annotated source connections.', now()))
        return {'message': 'Source connections saved.'}

    def review(self, user, entity_id, payload):
        if not user or not user['editor']:
            raise APIError(403, 'Only explicitly authorised editors can review contributions.')
        action, feedback = payload.get('action'), str(payload.get('feedback', '')).strip()[:12000]
        if action not in ('published', 'needs changes', 'declined') or (action != 'published' and not feedback):
            raise APIError(422, 'Choose a review decision and explain requested changes or a decline.')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM entities WHERE id=?', (entity_id,)).fetchone()
            if not row or row['status'] == 'withdrawn' or (row['demo'] and not self.demo):
                raise APIError(404, 'This contribution is unavailable.')
            rev = db.execute('SELECT * FROM revisions WHERE entity_id=? ORDER BY number DESC LIMIT 1', (entity_id,)).fetchone()
            if payload.get('revision_id') != rev['id'] or rev['state'] not in ('submitted', 'needs changes'):
                raise APIError(409, 'The contribution changed or was already reviewed. Refresh before reviewing.')
            owner = db.execute('SELECT verified FROM contributors WHERE id=?', (row['owner_id'],)).fetchone()
            if action == 'published' and (not owner[0] or row['kind'] == 'correction'):
                raise APIError(422, 'Verify the contributor email before publishing. Corrections must be applied through an approved contributor revision.')
            if action == 'published' and not db.execute('SELECT 1 FROM confirmations WHERE revision_id=? AND owner_id=?', (rev['id'], row['owner_id'])).fetchone():
                raise APIError(422, 'The verified contributor must confirm this specific account and its sharing permissions in their private notebook before publication.')
            if action == 'published':
                pending_source = db.execute('SELECT 1 FROM citations JOIN entities ON entities.id=citations.source_id WHERE revision_id=? AND entities.status!="published"', (rev['id'],)).fetchone()
                if pending_source:
                    raise APIError(422, 'Review and publish the linked source suggestions before publishing this practice.')
                links = payload.get('links', [])
                if not isinstance(links, list) or len(links) > 50:
                    raise APIError(422, 'Use at most 50 source connections per review.')
                if row['kind'] == 'source':
                    if row['target_id'] and not links:
                        raise APIError(422, 'Explain the suggested source connection before publishing. Choose its practice, relationship, and passage.')
                    self.link_sources(db, entity_id, links)
                db.execute('UPDATE entities SET published_revision_id=?, status="published", updated_at=? WHERE id=?', (rev['id'], now(), entity_id))
            elif not row['published_revision_id']:
                db.execute('UPDATE entities SET status=?,updated_at=? WHERE id=?', (action, now(), entity_id))
            db.execute('UPDATE revisions SET state=? WHERE id=?', (action, rev['id']))
            db.execute('INSERT INTO reviews VALUES (?,?,?,?,?,?,?)', (uid(), entity_id, rev['id'], user['id'], action, feedback, now()))
        return {'message': 'Review recorded: ' + action + '.'}

    def withdraw_fixtures(self):
        """Retire only the known fictional records from older local previews."""
        seed = json.loads((ROOT / 'data/demo.json').read_text())
        identifiers = [entry['id'] for entry in seed['sources'] + seed['practices']]
        if not identifiers:
            return
        with self.connect() as db:
            db.execute(
                'UPDATE entities SET status="withdrawn" WHERE demo=1 AND status!="withdrawn" AND id IN ('
                + ','.join('?' for _ in identifiers) + ')', identifiers)

    def seed(self):
        seed = json.loads((ROOT / 'data/demo.json').read_text())
        with self.connect() as db:
            if db.execute('SELECT 1 FROM entities WHERE demo=1').fetchone():
                return
            owner = self.identity(db, 'fictional-seed@example.test')
            db.execute('UPDATE contributors SET verified=1 WHERE id=?', (owner,))
            for entry in seed['sources'] + seed['practices']:
                rev_id = 'revision-' + entry['id']
                content = entry['content']
                db.execute('INSERT INTO entities VALUES (?,?,?,?,?,?,?,NULL,1,?,?)', (entry['id'], entry.get('kind', 'practice'), entry['slug'], owner, entry.get('parent_id'), None, 'published', entry['date'], entry['date']))
                db.execute('INSERT INTO revisions VALUES (?,?,1,?,?,?)', (rev_id, entry['id'], json.dumps(content, ensure_ascii=False), 'published', entry['date']))
                db.execute('UPDATE entities SET published_revision_id=? WHERE id=?', (rev_id, entry['id']))
                for c in entry.get('citations', []):
                    db.execute('INSERT INTO citations VALUES (?,?,?,?,?,?,?)', (uid(), rev_id, c['block_id'], c['source_id'], c['relationship'], c['locator'], c['annotation']))

    def seed_editorial(self):
        """Local-only editorial metadata supplied by the user, not a consent claim.

        The reserved owner is an internal record identity, never the named author.
        Existing records, revisions, and withdrawals are deliberately left alone.
        """
        editorial = json.loads((ROOT / 'data/editorial.json').read_text())
        with self.connect() as db:
            owner = self.identity(db, 'editorial-preview@example.invalid')
            for entry in editorial['sources'] + editorial['entries']:
                if db.execute('SELECT 1 FROM entities WHERE id=?', (entry['id'],)).fetchone():
                    continue
                revision_id, timestamp = 'revision-' + entry['id'], now()
                db.execute('INSERT INTO entities VALUES (?,?,?,?,NULL,NULL,?,NULL,1,?,?)', (entry['id'], entry['kind'], entry['slug'], owner, 'published', timestamp, timestamp))
                db.execute('INSERT INTO revisions VALUES (?,?,1,?,?,?)', (revision_id, entry['id'], json.dumps(entry['content'], ensure_ascii=False), 'published', timestamp))
                db.execute('UPDATE entities SET published_revision_id=? WHERE id=?', (revision_id, entry['id']))
                for citation in entry.get('citations', []):
                    db.execute('INSERT INTO citations VALUES (?,?,?,?,?,?,?)', (uid(), revision_id, citation['block_id'], citation['source_id'], citation['relationship'], citation['locator'], citation['annotation']))


class Handler(BaseHTTPRequestHandler):
    server_version = 'SourceCulture/0.1'
    rates = defaultdict(deque)

    def log_message(self, fmt, *args):
        # Do not log tokens, query strings, private email, or request bodies.
        print(self.command, urlparse(self.path).path, flush=True)

    @property
    def store(self):
        return self.server.store

    def headers_common(self, private=True, revalidate=False):
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Cache-Control', 'no-store' if private else 'no-cache' if revalidate else 'public, max-age=3600')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-src https://www.youtube-nocookie.com; base-uri 'self'; form-action 'self'; frame-ancestors 'none'; object-src 'none'")

    def respond(self, data, status=200, cookie=None):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.headers_common()
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        if cookie:
            self.send_header('Set-Cookie', cookie)
        self.end_headers()
        self.wfile.write(body)

    def user(self):
        try:
            cookies = SimpleCookie(self.headers.get('Cookie', ''))
            return self.store.session(cookies['sc_session'].value) if 'sc_session' in cookies else None
        except Exception:
            return None

    def do_GET(self):
        try:
            self.get()
        except APIError as exc:
            self.respond({'error': exc.message}, exc.status)

    def get(self):
        path = unquote(urlparse(self.path).path)
        if path.startswith('/api/'):
            if path == '/api/config':
                return self.respond({'mode': 'demo' if self.store.demo else 'production', 'activities': ACTIVITIES, 'source_types': SOURCE_TYPES, 'relationships': RELATIONSHIPS})
            if path == '/api/session':
                user = self.user()
                return self.respond({'user': {'email': user['email'], 'editor': user['editor']} if user else None, 'csrf': user['csrf'] if user else None})
            if path == '/api/practices':
                return self.respond(self.store.collection('practice'))
            if path == '/api/sources':
                return self.respond(self.store.collection('source'))
            for prefix, kind in [('/api/practices/', 'practice'), ('/api/sources/', 'source')]:
                if path.startswith(prefix):
                    return self.respond(self.store.detail(path[len(prefix):], kind))
            if path == '/api/mine':
                return self.respond(self.store.private(self.user()))
            if path == '/api/admin':
                return self.respond(self.store.private(self.user(), admin=True))
            if path.startswith('/api/submissions/'):
                return self.respond(self.store.private(self.user(), path.split('/')[-1]))
            raise APIError(404, 'API route not found.')
        if path.startswith('/media/'):
            with self.store.connect() as db:
                row = db.execute('SELECT media.*, entities.id AS entity_id FROM media JOIN revisions ON revisions.id=media.revision_id JOIN entities ON entities.id=revisions.entity_id WHERE media.id=?', (path.split('/')[-1],)).fetchone()
                user = self.user()
                entity = db.execute('SELECT * FROM entities WHERE id=?', (row['entity_id'],)).fetchone() if row else None
                allowed = row and self.store.visible(db, entity) and entity['published_revision_id'] == row['revision_id']
                if not row or not (allowed or (user and (user['id'] == row['owner_id'] or user['editor']))):
                    raise APIError(404, 'Image unavailable.')
                return self.file(self.store.uploads / row['storage_key'], private=True)
        if path.startswith('/project-images/'):
            try:
                image = render_project_image(path[len('/project-images/'):], self.store.directory / 'project-images')
            except FileNotFoundError:
                raise APIError(404, 'Project image not found.')
            except (OSError, ValueError, KeyError) as exc:
                print('Project image processing failed:', type(exc).__name__, flush=True)
                raise APIError(500, 'Project image could not be processed.')
            return self.file(image, private=False, revalidate=True)
        # Explicit static allowlist keeps databases, outbox, design inputs, and secrets private.
        if path in ('/favicon.svg', '/css/tokens.css', '/css/base.css', '/css/layout.css', '/css/components.css', '/css/notebook.css', '/assets/projects/prasa-example.png') or path.startswith(('/js/', '/assets/fonts/', '/assets/illustrations/', '/assets/vendor/')):
            target = (ROOT / path.lstrip('/')).resolve()
            if ROOT not in target.parents or not target.is_file() or target.suffix not in ('.js', '.css', '.svg', '.otf', '.woff2', '.png'):
                raise APIError(404, 'File not found.')
            return self.file(target, private=False)
        if path in ('/', '/explore', '/sources', '/about', '/contribute', '/manage', '/admin') or re.fullmatch(r'/(practices|sources)/[^/]+', path):
            body = (ROOT / 'index.html').read_text()
            if path in ('/manage', '/admin', '/contribute'):
                body = body.replace('<head>', '<head><meta name="robots" content="noindex, nofollow">')
            if path.startswith(('/practices/', '/sources/')):
                try:
                    entry = self.store.detail(path.split('/')[-1], 'practice' if path.startswith('/practices/') else 'source')
                    if 'redirect' in entry:
                        self.send_response(301)
                        self.send_header('Location', '/' + path.split('/')[1] + '/' + entry['redirect'])
                        self.end_headers()
                        return
                    title = html.escape(entry['title'] + ' — Source Culture', quote=True)
                    description = html.escape(entry.get('summary') or entry.get('source', {}).get('annotation', ''), quote=True)
                    body = body.replace('<title>source culture — everyday ways of knowing</title>', '<title>' + title + '</title>')
                    body = body.replace('content="Source Culture"', 'content="' + title + '"')
                    body = body.replace('content="Source Culture — a growing collection of everyday instructions, patterns, and ways of knowing."', 'content="' + description + '"')
                    body = body.replace('content="A growing collection of everyday instructions, patterns, and ways of knowing."', 'content="' + description + '"')
                    canonical = html.escape(self.store.base_url + path, quote=True)
                    body = body.replace('</head>', f'<link rel="canonical" href="{canonical}"><meta property="og:url" content="{canonical}"></head>')
                except APIError as exc:
                    self.send_response(exc.status)
                    self.headers_common()
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(body.encode())
                    return
            self.send_response(200)
            self.headers_common()
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(body.encode())
            return
        raise APIError(404, 'Page not found.')

    def file(self, path, private=False, revalidate=False):
        body = path.read_bytes()
        self.send_response(200)
        local_code = self.store.demo and path.suffix in ('.js', '.css')
        self.headers_common(private, revalidate=revalidate or local_code)
        self.send_header('Content-Type', mimetypes.guess_type(path)[0] or 'application/octet-stream')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        try:
            self.post()
        except APIError as exc:
            self.respond({'error': exc.message}, exc.status)
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError, TypeError):
            self.respond({'error': 'The request could not be read. Your input has been preserved.'}, 400)
        except Exception as exc:
            print('Request failed:', type(exc).__name__, flush=True)
            self.respond({'error': 'The server could not complete the request. Your input has been preserved.'}, 500)

    def post(self):
        path = urlparse(self.path).path
        if self.headers.get('Origin') != self.store.base_url:
            raise APIError(403, 'This request must come from this website.')
        if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
            raise APIError(415, 'Use a JSON request.')
        length = int(self.headers.get('Content-Length', '0'))
        if length < 1 or length > 29 * 1024 * 1024:
            raise APIError(413, 'This request is too large.')
        key = (self.client_address[0], 'auth' if '/auth/' in path else 'write')
        queue = self.rates[key]
        while queue and queue[0] < time.time() - 600:
            queue.popleft()
        if len(queue) >= (12 if key[1] == 'auth' else 40):
            raise APIError(429, 'Too many requests. Please wait a few minutes and try again.')
        queue.append(time.time())
        payload = json.loads(self.rfile.read(length))
        if not isinstance(payload, dict):
            raise APIError(400, 'Expected a request object.')
        user = self.user()
        if user and self.headers.get('X-CSRF-Token') != user['csrf']:
            raise APIError(403, 'Your session changed. Refresh this page and try again.')
        if path == '/api/auth/request':
            email = str(payload.get('email', '')).strip().lower()
            self.store.mail_link(email)
            return self.respond({'message': 'Sign-in requested. In local demo mode, open the private development outbox in the terminal.' if self.store.demo else 'Check your inbox for a single-use link. It expires in 15 minutes.'})
        if path == '/api/auth/verify':
            token = self.store.verify(str(payload.get('token', '')))
            return self.respond({'message': 'Signed in.'}, cookie='sc_session=' + token + '; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800' + ('' if self.store.demo else '; Secure'))
        if path == '/api/auth/logout':
            cookies = SimpleCookie(self.headers.get('Cookie', ''))
            if 'sc_session' in cookies:
                with self.store.connect() as db:
                    db.execute('DELETE FROM sessions WHERE digest=?', (digest(cookies['sc_session'].value),))
            return self.respond({'message': 'Signed out.'}, cookie='sc_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0')
        if path == '/api/submissions':
            return self.respond(self.store.submit(payload, user), 201)
        if re.fullmatch('/api/submissions/[^/]+/revisions', path):
            return self.respond(self.store.submit(payload, user, path.split('/')[3]), 201)
        if re.fullmatch('/api/submissions/[^/]+/withdraw', path):
            return self.respond(self.store.withdraw(user, path.split('/')[3]))
        if re.fullmatch('/api/submissions/[^/]+/messages', path):
            return self.respond(self.store.message(user, path.split('/')[3], payload.get('body', '')))
        if re.fullmatch('/api/submissions/[^/]+/confirm', path):
            return self.respond(self.store.confirm(user, path.split('/')[3], payload))
        if re.fullmatch('/api/admin/[^/]+/review', path):
            return self.respond(self.store.review(user, path.split('/')[3], payload))
        if re.fullmatch('/api/admin/[^/]+/connections', path):
            return self.respond(self.store.connect_source(user, path.split('/')[3], payload))
        raise APIError(404, 'API route not found.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--outbox', action='store_true', help='Read private local demo email links; never available over HTTP.')
    args = parser.parse_args()
    directory = Path(os.getenv('DATA_DIR', ROOT / '.runtime'))
    if args.outbox:
        outbox = directory / 'mail.jsonl'
        print(outbox.read_text() if outbox.exists() else 'No local sign-in links yet.')
        return
    demo = os.getenv('APP_MODE', 'demo') == 'demo'
    host, port = os.getenv('HOST', '127.0.0.1'), int(os.getenv('PORT', '8000'))
    base_url = os.getenv('BASE_URL', f'http://{host}:{port}')
    if demo and host not in ('localhost', '127.0.0.1', '::1'):
        raise SystemExit('Demo mode must bind to loopback. Do not expose the development outbox or demo server.')
    if not demo and not base_url.startswith('https://'):
        raise SystemExit('Production requires an HTTPS BASE_URL.')
    editors = [e.strip().lower() for e in os.getenv('EDITOR_EMAILS', '').split(',') if e.strip()]
    store = Store(directory, demo, editors, base_url)
    server = ThreadingHTTPServer((host, port), Handler)
    server.store = store
    print(f'Source Culture — {"LOCAL DEMO" if demo else "PRODUCTION DATA MODE"}\nLocal: {base_url}\nSign-in outbox: python3 server/app.py --outbox', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()


if __name__ == '__main__':
    main()
