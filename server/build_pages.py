"""Export the curated notebook for static hosting, without opening a database.

Run: python3 -m server.build_pages --base-path /source-culture/
Only the editorial JSON and explicitly selected frontend assets are published.
"""
import argparse
import json
import re
import shutil
import tempfile
from pathlib import Path

from .project_images import render_project_image

ROOT = Path(__file__).resolve().parents[1]
ACTIVITIES = ['food and cooking', 'craft and making', 'games and play', 'remembering and recording', 'exchange and sharing', 'navigation and place', 'everyday coordination']
SOURCE_TYPES = ['academic article', 'book or chapter', 'thesis or dissertation', 'video', 'blog or essay', 'project documentation', 'podcast or audio', 'interview or oral account', 'archive or exhibition', 'other']
PROJECT_IMAGES = {'rice-grid': 'experiments-with-rice.JPG', 'prasa': 'prasa-example.png'}


def build(output, base_path='/source-culture/'):
    if not re.fullmatch(r'/(?:[\w-]+/)*', base_path):
        raise ValueError('Base path must be / or a path such as /source-culture/.')
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

    page = (ROOT / 'index.html').read_text()
    page = page.replace('<meta name="app-base" content="/">',
                        f'<meta name="app-base" content="{base_path}">\n  <meta name="app-mode" content="static">')
    page = re.sub(r'(\b(?:href|src)=")/(?!/)', lambda match: match[1] + base_path, page)
    page = page.replace('Please enable JavaScript to explore this local demo.', 'Please enable JavaScript to explore this notebook.')
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
    data = build(args.output, args.base_path)
    print(f'Built {len(data["practices"])} projects and {len(data["sources"])} sources in {args.output}')


if __name__ == '__main__':
    main()
