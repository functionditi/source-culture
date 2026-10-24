"""Repeatable display treatment for originals in assets/projects.

Run `python3 -m server.project_images` to warm every supported image.
The HTTP route uses the same function and renders only when a source/style changes.
"""
import hashlib
import io
import json
import os
import random
import tempfile
from pathlib import Path

from PIL import Image, ImageChops, ImageColor, ImageOps

ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIRECTORY = ROOT / 'assets/projects'
STYLE_FILE = ROOT / 'data/project-image-style.json'
SUPPORTED = {'.jpg', '.jpeg', '.png', '.webp', '.tif', '.tiff'}
RECIPE_VERSION = 'duotone-grain-1'


def read_style(path=STYLE_FILE):
    style = json.loads(Path(path).read_text())
    for name in ['shadow', 'highlight']:
        if len(ImageColor.getrgb(style[name])) != 3:
            raise ValueError('Duotone colours must be RGB colours.')
    if not isinstance(style['noise'], int) or not 0 <= style['noise'] <= 64:
        raise ValueError('Noise must be an integer between 0 and 64.')
    if not isinstance(style['autocontrast'], (int, float)) or not 0 <= style['autocontrast'] < 20:
        raise ValueError('Autocontrast must be between 0 and 20 percent.')
    if not isinstance(style['max_edge'], int) or not 64 <= style['max_edge'] <= 4096:
        raise ValueError('Maximum image edge must be between 64 and 4096 pixels.')
    if not isinstance(style['quality'], int) or not 1 <= style['quality'] <= 100:
        raise ValueError('WebP quality must be between 1 and 100.')
    return style


def render_project_image(name, cache_directory, source_directory=SOURCE_DIRECTORY, style_file=STYLE_FILE):
    """Return a cached WebP; never overwrite or save metadata from the original."""
    source_directory = Path(source_directory).resolve()
    if not name or '/' in name or '\\' in name or name.startswith('.'):
        raise FileNotFoundError('Project image not found.')
    source = source_directory / name
    if source.is_symlink() or not source.is_file() or source.suffix.lower() not in SUPPORTED:
        raise FileNotFoundError('Project image not found.')
    if source.resolve().parent != source_directory:
        raise FileNotFoundError('Project image not found.')

    style = read_style(style_file)
    original = source.read_bytes()
    recipe = json.dumps(style, sort_keys=True).encode() + RECIPE_VERSION.encode()
    fingerprint = hashlib.sha256(original + recipe).hexdigest()
    cache_directory = Path(cache_directory)
    cache_directory.mkdir(parents=True, exist_ok=True)
    target = cache_directory / (fingerprint + '.webp')
    if target.is_file():
        return target

    with Image.open(io.BytesIO(original)) as image:
        image = ImageOps.exif_transpose(image).convert('RGBA')
        # Transparent source pixels sit on the chosen highlight colour.
        background = Image.new('RGBA', image.size, style['highlight'])
        image = Image.alpha_composite(background, image).convert('RGB')
        image.thumbnail((style['max_edge'], style['max_edge']), Image.Resampling.LANCZOS)
        gray = ImageOps.autocontrast(ImageOps.grayscale(image), cutoff=style['autocontrast'])
        result = ImageOps.colorize(gray, black=style['shadow'], white=style['highlight'])

    if style['noise']:
        # Monochromatic uniform noise after duotoning, with a stable seed so
        # resizing/reloading never makes the texture flicker.
        generator = random.Random(int(fingerprint, 16))
        noise = Image.frombytes('L', result.size, generator.randbytes(result.width * result.height))
        strength = style['noise']
        noise = noise.point([128 + round((value / 255 * 2 - 1) * strength) for value in range(256)])
        result = ImageChops.add(result, noise.convert('RGB'), offset=-128)
    result.info.clear()
    handle, temporary = tempfile.mkstemp(dir=cache_directory, suffix='.webp')
    os.close(handle)
    try:
        result.save(temporary, format='WEBP', quality=style['quality'], method=6)
        os.replace(temporary, target)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return target


def main():
    cache = Path(os.getenv('DATA_DIR', ROOT / '.runtime')) / 'project-images'
    for source in sorted(SOURCE_DIRECTORY.iterdir()):
        if source.is_file() and not source.is_symlink() and source.suffix.lower() in SUPPORTED:
            output = render_project_image(source.name, cache)
            with Image.open(output) as image:
                print(f'{source.name} → {output} ({image.width} × {image.height})')


if __name__ == '__main__':
    main()
