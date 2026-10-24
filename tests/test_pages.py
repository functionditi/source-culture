import json
import re
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urljoin, urlparse

from PIL import Image
from server.build_pages import build


class PagesExportTests(unittest.TestCase):
    def test_export_serves_assets_and_deep_links_under_a_project_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'site'
            data = build(output, '/source-culture/')
            for route in ['', 'explore', 'sources', 'about', 'contribute', 'manage', 'admin',
                          *['practices/' + entry['slug'] for entry in data['practices']],
                          *['sources/' + entry['slug'] for entry in data['sources']]]:
                page = (output / route / 'index.html').read_text()
                self.assertIn('<meta name="app-mode" content="static">', page)
                self.assertIn('<meta name="app-base" content="/source-culture/">', page)
                for resource in re.findall(r'(?:src|href)="(/[^"?#]+)', page):
                    self.assertTrue(resource.startswith('/source-culture/'), resource)
                    path = output / resource.removeprefix('/source-culture/')
                    self.assertTrue(path.is_file() or (path / 'index.html').is_file(), resource)
            for font in re.findall(r'url\("([^"\n]+)"\)', (output / 'css/tokens.css').read_text()):
                path = urlparse(urljoin('https://example.test/source-culture/css/tokens.css', font)).path
                self.assertTrue((output / path.removeprefix('/source-culture/')).is_file(), font)
            self.assertTrue((output / '404.html').is_file())
            for entry in data['practices']:
                with Image.open(output / entry['project_image'].lstrip('/')) as image:
                    self.assertEqual(image.format, 'WEBP')
                    self.assertLessEqual(max(image.size), 1800)
            # Repeat builds must work without retaining outdated pages or files.
            (output / 'stale.txt').touch()
            build(output, '/source-culture/')
            self.assertFalse((output / 'stale.txt').exists())

    def test_snapshot_contains_only_curated_content_and_no_runtime_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'site'
            data = build(output, '/')
            self.assertEqual(len(data['practices']), 2)
            self.assertEqual(len(data['sources']), 4)
            self.assertEqual(data['config']['mode'], 'static')
            self.assertTrue(all(entry['editorial'] and not entry['demo'] for entry in data['practices'] + data['sources']))
            payload = (output / 'data/public.json').read_text()
            self.assertNotRegex(payload, r'demo-|fictional|@example|csrf|storage_key|feedback|permissions')
            self.assertEqual(json.loads(payload), data)
            files = [path.relative_to(output).as_posix() for path in output.rglob('*') if path.is_file()]
            self.assertFalse(any(path.startswith(('.runtime/', 'server/', 'tests/', '.git/', 'references/', 'palette/', 'assets/projects/')) for path in files))
            self.assertEqual(list((output / 'data').iterdir()), [output / 'data/public.json'])
            self.assertIn('content="/"', (output / 'index.html').read_text())

    def test_export_refuses_invalid_base_paths_and_unrelated_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            important = output / 'keep.txt'
            important.write_text('preserve this')
            for base in ['source-culture', '/source-culture', '/../', '/"unsafe/']:
                with self.assertRaises(ValueError):
                    build(output, base)
            with self.assertRaises(ValueError):
                build(output, '/')
            self.assertEqual(important.read_text(), 'preserve this')


if __name__ == '__main__':
    unittest.main()
