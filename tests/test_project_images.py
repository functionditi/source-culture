import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from server.project_images import STYLE_FILE, render_project_image


class ProjectImageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.source = self.root / 'projects'
        self.source.mkdir()
        self.cache = self.root / 'cache'
        self.settings = self.root / 'style.json'
        self.style = json.loads(STYLE_FILE.read_text())
        self.style.update(noise=0, autocontrast=0, quality=100)
        self.write_style()

    def tearDown(self):
        self.temporary.cleanup()

    def write_style(self):
        self.settings.write_text(json.dumps(self.style))

    def render(self, name):
        return render_project_image(name, self.cache, self.source, self.settings)

    def test_orientation_duotone_and_original_preservation(self):
        source = self.source / 'Photo.JPG'
        image = Image.new('RGB', (80, 40), 'black')
        image.paste('white', (40, 0, 80, 40))
        exif = Image.Exif()
        exif[274] = 6
        exif[315] = 'private source metadata'
        image.save(source, quality=100, exif=exif)
        original = source.read_bytes()
        with Image.open(self.render(source.name)) as result:
            self.assertEqual(result.size, (40, 80))
            for actual, expected in zip(result.getpixel((20, 20)), (73, 81, 44)):
                self.assertLessEqual(abs(actual - expected), 3)
            self.assertTrue(all(value >= 252 for value in result.getpixel((20, 60))))
            self.assertNotIn('exif', result.info)
        self.assertEqual(source.read_bytes(), original)

    def test_cache_and_grain_are_repeatable(self):
        Image.new('RGB', (64, 64), (100, 100, 100)).save(self.source / 'flat.png')
        flat = self.render('flat.png')
        with Image.open(flat) as result:
            self.assertTrue(all(low == high for low, high in result.getextrema()))
        self.style['noise'] = 8
        self.write_style()
        textured = self.render('flat.png')
        contents, timestamp = textured.read_bytes(), textured.stat().st_mtime_ns
        with Image.open(textured) as result:
            self.assertTrue(all(high - low >= 8 for low, high in result.getextrema()))
        self.assertEqual(self.render('flat.png').stat().st_mtime_ns, timestamp)
        textured.unlink()
        self.assertEqual(self.render('flat.png').read_bytes(), contents)

    def test_source_and_style_changes_generate_new_copies(self):
        original = self.source / 'example.png'
        Image.new('RGB', (64, 64), 'black').save(original)
        first = self.render(original.name)
        Image.new('RGB', (64, 64), 'white').save(original)
        second = self.render(original.name)
        self.style['shadow'] = '#000000'
        self.write_style()
        third = self.render(original.name)
        self.assertEqual(len({first, second, third}), 3)
        self.assertTrue(all(path.exists() for path in [first, second, third]))

    def test_transparency_uses_white_and_size_is_limited(self):
        Image.new('RGBA', (200, 100), (255, 0, 0, 0)).save(self.source / 'transparent.png')
        self.style['max_edge'] = 100
        self.write_style()
        with Image.open(self.render('transparent.png')) as result:
            self.assertEqual(result.size, (100, 50))
            self.assertEqual(result.getpixel((50, 25)), (255, 255, 255))

    def test_only_project_images_can_be_processed(self):
        secret = self.root / 'secret.png'
        Image.new('RGB', (64, 64), 'black').save(secret)
        (self.source / 'linked.png').symlink_to(secret)
        (self.source / 'notes.txt').write_text('not an image')
        for name in ['../secret.png', 'sub/image.png', '..\\secret.png', '.hidden.png', 'linked.png', 'notes.txt', 'missing.jpg']:
            with self.subTest(name=name), self.assertRaises(FileNotFoundError):
                self.render(name)


if __name__ == '__main__':
    unittest.main()
