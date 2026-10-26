"""Export the curated notebook for static hosting, without opening a database.

Run: python3 -m server.build_pages --base-path /source-culture/
Only the editorial JSON and explicitly selected frontend assets are published.
"""
import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from .project_images import render_project_image

ROOT = Path(__file__).resolve().parents[1]
ACTIVITIES = ['food and cooking', 'craft and making', 'games and play', 'remembering and recording', 'exchange and sharing', 'navigation and place', 'everyday coordination']
SOURCE_TYPES = ['academic article', 'book or chapter', 'thesis or dissertation', 'video', 'blog or essay', 'project documentation', 'podcast or audio', 'interview or oral account', 'archive or exhibition', 'other']
PROJECT_IMAGES = {'rice-grid': 'experiments-with-rice.JPG', 'prasa': 'prasa-example.png'}


def public_supabase_config(url, key):
    if not url and not key:
        return None
    if not url or not key:
        raise ValueError('Set both SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY to enable contributions.')
    parsed = urlparse(url)
    if parsed.scheme != 'https' or not re.fullmatch(r'[a-z0-9-]+\.supabase\.co', parsed.netloc) or parsed.path not in ('', '/') or parsed.query or parsed.fragment:
        raise ValueError('SUPABASE_URL must be your https://<project-ref>.supabase.co URL.')
    valid_key = bool(re.fullmatch(r'sb_publishable_[A-Za-z0-9_-]{20,}', key))
    if key.startswith('eyJ'):
        try:
            payload = key.split('.')[1]
            valid_key = json.loads(base64.urlsafe_b64decode(payload + '=' * (-len(payload) % 4))).get('role') == 'anon'
        except (ValueError, IndexError, UnicodeDecodeError):
            valid_key = False
    if not valid_key:
        raise ValueError('Only a publishable key or legacy anon key can be included in the website. Never use a secret or service_role key.')
    return {'url': url.rstrip('/'), 'publishableKey': key}


def build(output, base_path='/source-culture/', supabase_url=None, supabase_key=None):
    if not re.fullmatch(r'/(?:[\w-]+/)*', base_path):
        raise ValueError('Base path must be / or a path such as /source-culture/.')
    supabase = public_supabase_config(supabase_url, supabase_key)
    mode = 'supabase' if supabase else 'static'
    output = Path(output).resolve()
    # The output is disposable; never allow it to replace source or runtime data.
    if output == ROOT or output in ROOT.parents or (output.is_relative_to(ROOT) and output != ROOT / 'dist'):
        raise ValueError('Use dist/ or a directory outside the source checkout for output.')
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        if not (output / '.source-culture-export').is_file():
            raise ValueError('Refusing to replace a nonempty directory that is not a Pages export.')
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)
    (output / '.source-culture-export').touch()

    for directory in ['css', 'js', 'assets/fonts', 'assets/illustrations', 'assets/vendor']:
        shutil.copytree(ROOT / directory, output / directory)
    # Version the whole module graph together: changing only app.js leaves its
    # imports eligible for reuse from an older read-only deployment.
    digest = hashlib.sha256(json.dumps({'mode': mode, 'supabase': supabase}, sort_keys=True).encode())
    for resource in sorted([*ROOT.glob('js/**/*.js'), *ROOT.glob('css/**/*.css'), ROOT / 'index.html']):
        digest.update(resource.relative_to(ROOT).as_posix().encode() + b'\0' + resource.read_bytes())
    version = digest.hexdigest()[:16]
    for script in (output / 'js').rglob('*.js'):
        script.write_text(re.sub(
            r'''(['"])(\.{1,2}/[^'"\s]+\.js)(?:\?[^'"]*)?\1''',
            lambda match: f'{match[1]}{match[2]}?v={version}{match[1]}',
            script.read_text()))
    shutil.copy2(ROOT / 'favicon.svg', output / 'favicon.svg')
    (output / '.nojekyll').touch()

    editorial = json.loads((ROOT / 'data/editorial.json').read_text())
    data = {'config': {'mode': 'static', 'activities': ACTIVITIES, 'source_types': SOURCE_TYPES}, 'practices': [], 'sources': []}
    with tempfile.TemporaryDirectory(prefix='source-culture-images-') as cache:
        for collection, records in [('practices', editorial['entries']), ('sources', editorial['sources'])]:
            for record in records:
                entry = {**record['content'], 'id': record['id'], 'slug': record['slug'], 'kind': record['kind'],
                         'parent_id': None, 'demo': False, 'revision': 1, 'created_at': record.get('date'),
                         'updated_at': record.get('date'), 'media': [], 'citations': record.get('citations', [])}
                if not re.fullmatch(r'[\w-]+', entry['slug']):
                    raise ValueError('Editorial slugs must be a single URL segment.')
                if name := PROJECT_IMAGES.get(entry.get('placeholder')):
                    image = render_project_image(name, cache)
                    destination = Path('project-images') / (Path(name).stem + '.webp')
                    (output / destination).parent.mkdir(exist_ok=True)
                    shutil.copy2(image, output / destination)
                    entry['project_image'] = '/' + destination.as_posix()
                data[collection].append(entry)
    (output / 'data').mkdir()
    (output / 'data/public.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    if supabase:
        (output / 'data/supabase.json').write_text(json.dumps(supabase, indent=2) + '\n')

    page = (ROOT / 'index.html').read_text()
    page = page.replace('<meta name="app-base" content="/">',
                        f'<meta name="app-base" content="{base_path}">\n  <meta name="app-mode" content="{mode}">')
    page = re.sub(r'(\b(?:href|src)=")/(?!/)', lambda match: match[1] + base_path, page)
    page = re.sub(r'(\b(?:href|src)=")([^"?]+\.(?:js|css))(?:\?[^\"]*)?(\")',
                  lambda match: f'{match[1]}{match[2]}?v={version}{match[3]}', page)
    page = page.replace('Please enable JavaScript to explore this local demo.', 'Please enable JavaScript to explore this notebook.')
    if not supabase:
        page = page.replace('  <header class="site-header">',
                            '  <div class="demo-banner" id="site-notice">this site is a work in progress. contribution submissions are coming soon!</div>\n  <header class="site-header">')
    routes = ['', 'explore', 'sources', 'about', 'contribute', 'manage', 'admin']
    routes += [f'practices/{entry["slug"]}' for entry in data['practices']]
    routes += [f'sources/{entry["slug"]}' for entry in data['sources']]
    for route in routes:
        destination = output / route / 'index.html'
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(page)
    (output / '404.html').write_text(page)
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-path', default='/source-culture/')
    parser.add_argument('--output', type=Path, default=ROOT / 'dist')
    args = parser.parse_args()
    data = build(args.output, args.base_path, os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_PUBLISHABLE_KEY'))
    print(f'Built {len(data["practices"])} projects and {len(data["sources"])} sources in {args.output}')


if __name__ == '__main__':
    main()
