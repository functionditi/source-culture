"""Dependency-free Chrome DevTools smoke tests, using an isolated temporary database.

Run with: python3 tests/verify_browser.py
Use --appearance-only for the palette, theme preference, and responsive checks.
Use --grids-only for decorative column-fill layout and resize checks.
Use --image-only to verify the treated repository images in their shared views.
Use --cache-only to check recovery from a previously cached Prāsa placeholder.
Screenshots are written to ignored test-results/. Chrome must be installed locally.
"""
import base64
import hashlib
import json
import os
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from server.app import Handler, Store, ThreadingHTTPServer


class CDP:
    def __init__(self, url):
        parsed = urlparse(url)
        self.socket = socket.create_connection((parsed.hostname, parsed.port), timeout=15)
        self.socket.settimeout(30)
        key = base64.b64encode(os.urandom(16)).decode()
        self.socket.sendall(f'GET {parsed.path} HTTP/1.1\r\nHost: {parsed.netloc}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n'.encode())
        header = b''
        while not header.endswith(b'\r\n\r\n'):
            header += self.socket.recv(1)
        assert header.startswith(b'HTTP/1.1 101 '), header
        self.counter = 0
        self.errors = []

    def read(self, size):
        data = b''
        while len(data) < size:
            part = self.socket.recv(size - len(data))
            if not part: raise ConnectionError('Browser connection closed')
            data += part
        return data

    def receive(self):
        message = b''
        while True:
            first, second = self.read(2)
            size = second & 127
            if size == 126: size = struct.unpack('!H', self.read(2))[0]
            if size == 127: size = struct.unpack('!Q', self.read(8))[0]
            mask = self.read(4) if second & 128 else None
            payload = self.read(size)
            if mask: payload = bytes(x ^ mask[i % 4] for i, x in enumerate(payload))
            message += payload
            if first & 128: return json.loads(message)

    def call(self, method, params=None):
        self.counter += 1
        payload = json.dumps({'id': self.counter, 'method': method, 'params': params or {}}).encode()
        mask = os.urandom(4)
        length = len(payload)
        header = bytes([129, 128 | length]) if length < 126 else bytes([129, 254]) + struct.pack('!H', length) if length < 65536 else bytes([129, 255]) + struct.pack('!Q', length)
        self.socket.sendall(header + mask + bytes(x ^ mask[i % 4] for i, x in enumerate(payload)))
        while True:
            result = self.receive()
            if result.get('method') == 'Runtime.exceptionThrown': self.errors.append(result['params'])
            if result.get('id') == self.counter:
                if 'error' in result: raise RuntimeError(result['error'])
                return result.get('result', {})

    def evaluate(self, expression):
        result = self.call('Runtime.evaluate', {'expression': expression, 'returnByValue': True, 'awaitPromise': True})
        if 'exceptionDetails' in result: raise AssertionError(result['exceptionDetails'])
        return result.get('result', {}).get('value')

    def wait(self, expression, timeout=15):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.evaluate(expression): return
            time.sleep(.08)
        raise AssertionError('Timed out waiting for ' + expression + '\n' + str(self.evaluate('document.body.innerText')))

    def click(self, selector):
        self.evaluate(f'document.querySelector({json.dumps(selector)}).click()')

    def fill(self, selector, value):
        self.evaluate(f'(() => {{ const el=document.querySelector({json.dumps(selector)}); el.value={json.dumps(value)}; el.dispatchEvent(new Event("input",{{bubbles:true}})); el.dispatchEvent(new Event("change",{{bubbles:true}})); }})()')


def run():
    chrome = os.getenv('CHROME_BIN', '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
    artifacts = ROOT / 'test-results'
    artifacts.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='source-culture-browser-') as work:
        class PreviewHandler(Handler):
            def get(self):
                path = urlparse(self.path).path
                if self.server.old_renderer and (path == '/' or path.startswith('/js/')):
                    source = (ROOT / ('index.html' if path == '/' else path.lstrip('/'))).read_text()
                    source = source.replace('?v=prasa-background-grid-1', '')
                    if path == '/js/views/notebook.js':
                        source = source.replace('<img src="/project-images/prasa-example.png" alt="White poetic text arranged across a textured olive-green background." width="1800" height="1219" loading="lazy">', '<div class="project-image-placeholder">cached Prāsa placeholder</div>')
                    self.send_response(200)
                    self.headers_common(path == '/')
                    self.send_header('Content-Type', 'text/html' if path == '/' else 'text/javascript')
                    self.end_headers()
                    self.wfile.write(source.encode())
                    return
                if self.server.static_preview and self.path.startswith('/api/'):
                    self.send_response(404)
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(b'<!DOCTYPE html><title>Cannot GET API in a static preview</title>')
                    return
                return super().get()

        server = ThreadingHTTPServer(('127.0.0.1', 0), PreviewHandler)
        server.static_preview = True
        server.old_renderer = '--cache-only' in sys.argv
        base = f'http://127.0.0.1:{server.server_port}'
        server.store = Store(Path(work) / 'data', editors=['editor@example.test'], base_url=base)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        profile = Path(work) / 'chrome'
        process = subprocess.Popen([chrome, '--headless=new', '--disable-gpu', '--disable-background-networking', '--no-first-run', '--no-default-browser-check', '--remote-debugging-port=0', '--user-data-dir=' + str(profile), 'about:blank'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            active = profile / 'DevToolsActivePort'
            for _ in range(150):
                if active.exists(): break
                if process.poll() is not None: raise RuntimeError('Chrome exited before opening the test browser')
                time.sleep(.1)
            port = active.read_text().splitlines()[0]
            tabs = json.load(urllib.request.urlopen(f'http://127.0.0.1:{port}/json'))
            c = CDP(next(t['webSocketDebuggerUrl'] for t in tabs if t['type'] == 'page'))
            c.call('Page.enable'); c.call('Runtime.enable')

            def visit(path, selector='h1'):
                c.call('Page.navigate', {'url': base + path})
                c.wait(f'document.querySelector({json.dumps(selector)}) !== null && !document.querySelector(".loading")')

            def screenshot(name, width, height):
                c.call('Emulation.setDeviceMetricsOverride', {'width': width, 'height': height, 'deviceScaleFactor': 1, 'mobile': width < 600})
                c.evaluate('document.fonts.ready')
                time.sleep(.75)
                c.evaluate('new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve(true))))')
                assert c.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), f'Horizontal overflow at {width}px'
                assert c.evaluate('''Array.from(document.querySelectorAll('.project-image-placeholder')).every(el =>
                  el.getBoundingClientRect().right <= el.closest('figure').getBoundingClientRect().right + 1)
                '''), f'Image placeholder exceeds its column at {width}px'
                data = c.call('Page.captureScreenshot', {'format': 'png', 'captureBeyondViewport': False})
                (artifacts / name).write_bytes(base64.b64decode(data['data']))

            c.call('Emulation.setDeviceMetricsOverride', {'width': 1440, 'height': 1100, 'deviceScaleFactor': 1, 'mobile': False})
            visit('/')
            c.wait('document.querySelector("h1").textContent.includes("app server is needed")')
            assert c.evaluate('document.querySelector("a[href=\\"http://127.0.0.1:8000/\\"]")!==null')
            assert not c.evaluate('document.body.innerText.includes("Unexpected token")')
            server.static_preview = False
            c.click('#retry-page')
            c.wait('document.querySelectorAll("[data-notebook-entry]").length === 2')
            c.wait('document.querySelector("#pattern-canvas canvas") !== null')
            if '--cache-only' in sys.argv:
                assert c.evaluate('document.querySelector(".project-image-placeholder")!==null')
                c.wait('document.querySelector("img[src=\\"/project-images/experiments-with-rice.JPG\\"]")?.naturalWidth === 1350')
                server.old_renderer = False
                visit('/')
                c.wait('document.querySelector("img[src=\\"/project-images/prasa-example.png\\"]")?.naturalWidth === 1800')
                assert c.evaluate('document.querySelector(".project-image-placeholder")===null')
                screenshot('prasa-image-cache-recovery.png', 1440, 1100)
                print('PASS: with the old placeholder renderer cached for an hour, a normal visit loads the treated project image through the versioned client files; browser caching remains enabled.')
                return
            if '--image-only' in sys.argv:
                def repository_headings(expected):
                    headings = c.evaluate('''Array.from(document.querySelectorAll('#notebook-collection .column-title, #notebook-variations .column-title')).map(el => el.textContent)''')
                    assert headings == expected, headings
                    for title in expected:
                        assert c.evaluate(f'Array.from(document.querySelectorAll(".column-title, .repository-project h3, .repository-invitation h2")).filter(el => el.textContent.trim() === {json.dumps(title)}).length') == 1

                def image_loaded(name, width):
                    image = f'img[src="/project-images/{name}"]'
                    c.wait(f'(() => {{ const image = document.querySelector({json.dumps(image)}); return image?.complete && image.naturalWidth === {width}; }})()')
                    assert c.evaluate(f'document.querySelector({json.dumps(image)}).naturalWidth') == width
                    assert not c.evaluate('document.body.innerText.includes("No project image or code has been reproduced")')
                    assert not c.evaluate('document.body.innerText.includes("Image placeholder: rice")')

                image_loaded('prasa-example.png', 1800)
                image_loaded('experiments-with-rice.JPG', 1350)
                repository_headings(['experiments with rice', 'Prāsa'])
                c.click('#notebook-collection [data-expand-column]')
                screenshot('rice-image-home.png', 1440, 1100)
                c.click('#notebook-variations [data-expand-column]')
                screenshot('prasa-image-home.png', 1440, 1100)
                for category, title in [('project', 'Prāsa'), ('experiment', 'experiments with rice'), ('practice', 'nothing here yet')]:
                    c.click(f'[data-repository-filter={category}]')
                    c.wait(f'location.search.includes("view={category}") && document.querySelector("[data-repository-filter={category}]").getAttribute("aria-pressed") === "true"')
                    repository_headings([title, 'what belongs here next?'])
                c.click('[data-repository-filter=all]')
                c.wait('document.querySelectorAll("[data-notebook-entry]").length === 2')
                repository_headings(['experiments with rice', 'Prāsa'])
                c.call('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844, 'deviceScaleFactor': 1, 'mobile': True})
                c.evaluate('document.querySelector("#notebook-collection").scrollIntoView({block:"start"})')
                screenshot('repository-project-mobile.png', 390, 844)
                visit('/explore?q=Pr%C4%81sa')
                image_loaded('prasa-example.png', 1800)
                visit('/explore?q=experiments+with+rice')
                image_loaded('experiments-with-rice.JPG', 1350)
                visit('/practices/prasa', '#account')
                image_loaded('prasa-example.png', 1800)
                screenshot('prasa-image-detail.png', 1440, 1100)
                c.evaluate('window.scrollTo(0, 0)')
                screenshot('prasa-image-mobile.png', 390, 844)
                visit('/practices/experiments-with-rice', '#account')
                image_loaded('experiments-with-rice.JPG', 1350)
                screenshot('rice-image-detail.png', 1440, 1100)
                c.evaluate('window.scrollTo(0, 0)')
                screenshot('rice-image-mobile.png', 390, 844)
                assert not c.errors, c.errors
                print('PASS: distinct project column headings follow all repository filters without duplicate titles; treated rice and Prāsa images load before hover and in collection/detail views, with correct proportions and no desktop/mobile overflow. Screenshots: test-results/{rice,prasa}-image-* and repository-project-mobile.png')
                return
            if '--grids-only' in sys.argv:
                c.evaluate('document.fonts.ready')
                time.sleep(.8)
                assert c.evaluate('''Array.from(document.querySelectorAll('.column-heading button')).every(el => {
                  const style = getComputedStyle(el);
                  return style.fontFamily.includes('Editorial New') && parseFloat(style.fontSize) >= 28 && style.color === 'rgb(221, 150, 69)';
                })''')
                assert c.evaluate('''(() => {
                  const grid = document.querySelector('.wordmark-grid'), r = grid.getBoundingClientRect();
                  const logo = document.querySelector('.site-header .wordmark').getBoundingClientRect();
                  const explore = document.querySelector('[data-nav="explore"]').getBoundingClientRect();
                  return grid.children.length === 20 && grid.getAttribute('aria-hidden') === 'true'
                    && getComputedStyle(grid).gridTemplateRows.split(' ').length === 4
                    && r.width > 120 && r.height === 32 && Math.abs(r.left - logo.right - 16) < 1
                    && Math.abs(explore.left - r.right - 16) < 1;
                })()''')
                wordmark_colours = c.evaluate('document.querySelector(".wordmark-grid").getAttribute("style")')
                screenshot('column-grid-headings-desktop.png', 1440, 1100)
                screenshot('column-grid-headings-tablet.png', 1024, 1000)
                c.call('Emulation.setDeviceMetricsOverride', {'width': 1440, 'height': 1100, 'deviceScaleFactor': 1, 'mobile': False})
                time.sleep(.8)
                def check_grids():
                    data = c.evaluate('''Array.from(document.querySelectorAll('[data-reading-column]')).map(column => {
                      const grid = column.querySelector('.column-grid'), r = grid.getBoundingClientRect();
                      const copy = column.querySelector('.reading-copy').getBoundingClientRect();
                      const colours = ['--grid-colour-a','--grid-colour-b'].map(name => grid.style.getPropertyValue(name));
                      return {top:r.top, bottom:r.bottom, width:r.width, height:r.height, contentBottom:copy.bottom,
                        contentWidth:copy.width, columnBottom:column.getBoundingClientRect().bottom, colours,
                        hidden:grid.getAttribute('aria-hidden'), cells:grid.children.length};
                    })''')
                    palette = c.evaluate('''['--caramel','--rust','--olive','--slate','--sand','--brick','--ink','--paper']
                      .map(name => getComputedStyle(document.documentElement).getPropertyValue(name).trim())''')
                    assert data
                    assert len({item['colours'][1] for item in data}) == len(data), data
                    assert len({round(item['bottom']) for item in data}) <= 2, data
                    assert any(item['height'] > 100 for item in data), data
                    for item in data:
                        assert item['top'] >= item['contentBottom'] + 19, item
                        assert abs(item['bottom'] - item['columnBottom']) < 2, item
                        assert abs(item['width'] - item['contentWidth']) < 2, item
                        assert item['hidden'] == 'true' and item['cells'] >= 30, item
                        assert item['colours'][0] == 'var(--background)' and item['colours'][1] in palette, item
                    assert c.evaluate('''Array.from(document.querySelectorAll('.column-grid')).every(grid => {
                      const background = getComputedStyle(document.body).backgroundColor;
                      return getComputedStyle(grid.children[0]).backgroundColor === background
                        && getComputedStyle(grid.children[1]).backgroundColor !== background;
                    })''')
                    assert c.evaluate('''(() => {
                      const grid = document.querySelector('.wordmark-grid'), background = getComputedStyle(document.body).backgroundColor;
                      const first = getComputedStyle(grid.children[0]).backgroundColor;
                      const second = getComputedStyle(grid.children[1]).backgroundColor;
                      return first === background && second !== background;
                    })()''')
                    assert c.evaluate('''Array.from(document.querySelectorAll('[data-reading-column], .repository-overview'))
                      .every(el => getComputedStyle(el).borderLeftWidth === '0px')''')
                    headings = c.evaluate('''Array.from(document.querySelectorAll('.contribution-heading'))
                      .map(el => ({text:el.textContent, colour:getComputedStyle(el).color}))''')
                    if headings:
                        assert len(headings) == 3 and all(item['colour'] == 'rgb(99, 120, 163)' for item in headings), headings
                    return [item['colours'] for item in data]

                colours = check_grids()
                column_ids = ['notebook-introduction', 'notebook-collection', 'notebook-variations', 'notebook-connections']
                for index, column_id in enumerate(column_ids):
                    c.click(f'#{column_id} [data-expand-column]')
                    time.sleep(.8)
                    assert check_grids() == colours
                    c.evaluate('window.scrollTo(0, document.documentElement.scrollHeight)')
                    screenshot(f'column-grid-{index + 1}-bottom.png', 1440, 1100)
                # Moving over a decorative grid still expands its reading column.
                target = c.evaluate('''(() => {
                  const r = document.querySelector('#notebook-collection .column-grid').getBoundingClientRect();
                  return {x:r.x+r.width/2, y:Math.max(10, Math.min(innerHeight-100, (r.top+r.bottom)/2))};
                })()''')
                c.call('Input.dispatchMouseEvent', {'type': 'mouseMoved', **target})
                c.wait('document.querySelector("#notebook-collection").dataset.active === "true"')
                time.sleep(.8)
                assert check_grids() == colours
                c.call('Input.dispatchMouseEvent', {'type': 'mouseMoved', 'x': 0, 'y': 0})
                for theme in ['white', 'charcoal', 'olive']:
                    c.click(f'[data-theme-choice="{theme}"]')
                    assert check_grids() == colours
                    assert c.evaluate('document.querySelector(".wordmark-grid").getAttribute("style")') == wordmark_colours
                c.evaluate('window.scrollTo(0, 0)')
                screenshot('column-grid-mobile.png', 390, 844)
                assert c.evaluate('Array.from(document.querySelectorAll(".column-grid")).every(el => getComputedStyle(el).display === "none")')
                c.click('[data-column-jump="notebook-connections"]')
                c.wait('document.querySelector("#notebook-connections").getBoundingClientRect().top < 110 && scrollY > 0')
                c.evaluate('window.scrollTo(0, 0)')
                screenshot('column-grid-320.png', 320, 760)
                assert c.evaluate('getComputedStyle(document.querySelector(".wordmark-grid")).display') == 'grid'
                c.call('Emulation.setDeviceMetricsOverride', {'width': 1440, 'height': 1100, 'deviceScaleFactor': 1, 'mobile': False})
                time.sleep(.8)
                assert check_grids() == colours
                c.click('[data-repository-filter=practice]')
                c.wait('document.querySelector(".repository-empty")!==null')
                time.sleep(.8)
                check_grids()
                visit('/explore')
                time.sleep(.8)
                check_grids()
                assert c.evaluate('document.querySelector(".wordmark-grid").children.length') == 20
                c.evaluate('window.scrollTo(0, document.documentElement.scrollHeight)')
                screenshot('column-grid-collection.png', 1440, 1100)
                c.call('Network.enable'); c.call('Network.setCacheDisabled', {'cacheDisabled': True})
                c.call('Network.setBlockedURLs', {'urls': ['*p5-2.3.3.min.js']})
                visit('/')
                c.wait('document.querySelector("#pattern-canvas").textContent.includes("unavailable")')
                time.sleep(.8)
                check_grids()
                assert not c.errors, c.errors
                print('PASS: slate-blue contribution headings, no vertical column rules, distinct bottom-grid accents remain stable across expansion and theme changes, logo and column grids use the current background, shared bottom edge after all four expansions, artwork hover, mobile section jumps, filtered/collection views, and p5-independent rendering. Screenshots: test-results/column-grid-*')
                return
            # Olive is the default in both system modes; explicit choices still persist.
            assert c.evaluate('document.documentElement.dataset.theme') == 'olive'
            assert c.evaluate('Array.from(document.querySelectorAll(".wordmark")).every(el => el.textContent === "<source culture>")')
            c.call('Emulation.setEmulatedMedia', {'features': [{'name': 'prefers-color-scheme', 'value': 'dark'}]})
            assert c.evaluate('document.documentElement.dataset.theme') == 'olive'
            c.call('Emulation.setEmulatedMedia', {'features': [{'name': 'prefers-color-scheme', 'value': 'light'}]})
            assert c.evaluate('document.documentElement.dataset.theme') == 'olive'
            for theme, background in [('olive', 'rgb(73, 81, 44)'), ('charcoal', 'rgb(18, 15, 5)'), ('white', 'rgb(244, 244, 244)')]:
                c.fill('#your-definition', 'Keep these words while changing appearance.')
                c.click(f'[data-theme-choice="{theme}"]')
                assert c.evaluate('document.querySelector("#your-definition").value.includes("Keep these words")')
                assert c.evaluate('document.querySelectorAll("[data-theme-choice][aria-pressed=true]").length===1')
                c.call('Emulation.setEmulatedMedia', {'features': [{'name': 'prefers-color-scheme', 'value': 'dark' if theme == 'white' else 'light'}]})
                assert c.evaluate('document.documentElement.dataset.theme') == theme
                visit('/')
                assert c.evaluate('document.documentElement.dataset.theme') == theme
                assert c.evaluate('getComputedStyle(document.body).backgroundColor') == background
                colors = c.evaluate('''(() => {
                  const color = selector => getComputedStyle(document.querySelector(selector)).color;
                  const link = getComputedStyle(document.querySelector(".project-link a"));
                  return {
                    body:color(".reading-copy p"), heading:color("#notebook-collection .column-heading button"),
                    link:link.color, linkBackground:link.backgroundColor, linkDecoration:link.textDecorationLine,
                    surface:getComputedStyle(document.querySelector(".repository-overview")).backgroundColor
                  };
                })()''')

                def luminance(color):
                    channels = [int(x.strip()) / 255 for x in color[4:-1].split(',')]
                    linear = [x / 12.92 if x <= .04045 else ((x + .055) / 1.055) ** 2.4 for x in channels]
                    return sum(x * y for x, y in zip(linear, [.2126, .7152, .0722]))

                for foreground, minimum, surfaces in [
                    (colors['body'], 4.5, [background, colors['surface']]),
                    (colors['heading'], 3, [background, colors['surface']]),
                ]:
                    for surface in surfaces:
                        light, dark = sorted([luminance(foreground), luminance(surface)], reverse=True)
                        assert (light + .05) / (dark + .05) >= minimum, (theme, foreground, surface)
                assert colors['link'] == 'rgb(255, 255, 255)'
                assert colors['linkBackground'] == 'rgb(99, 120, 163)'
                assert colors['linkDecoration'] == 'underline'
                if theme == 'white':
                    assert colors['body'] == 'rgb(73, 81, 44)'
                    assert colors['heading'] == 'rgb(158, 37, 36)'
                else:
                    assert colors['body'] == 'rgb(255, 255, 255)'
                    assert colors['heading'] == 'rgb(221, 150, 69)'
                    assert c.evaluate('getComputedStyle(document.querySelector(".repository-overview h2")).color') == 'rgb(221, 150, 69)'
                screenshot(f'appearance-{theme}-desktop.png', 1440, 1100)
                screenshot(f'appearance-{theme}-mobile.png', 390, 844)
                screenshot(f'appearance-{theme}-320.png', 320, 760)
                if theme != 'white':
                    visit('/contribute?type=practice', '#contribution-form')
                    assert c.evaluate('document.documentElement.dataset.theme') == theme
                    c.evaluate('document.querySelector("[name=title]").focus()')
                    screenshot(f'appearance-{theme}-form.png', 390, 844)
                    visit('/')
            c.call('Emulation.setEmulatedMedia', {'features': [{'name': 'prefers-color-scheme', 'value': 'light'}]})
            screenshot('appearance-white-tablet.png', 1024, 900)
            if '--appearance-only' in sys.argv:
                assert not c.errors, c.errors
                print('PASS: Olive default in both system modes, bracketed wordmark, pure-white dark reading text, caramel accents, white underlined links on #6378A3 in all three appearances, saved choice across reload/navigation, preserved form input, body/heading contrast, and desktop/tablet/mobile/320px layouts. Screenshots: test-results/appearance-*')
                return
            c.call('Emulation.setDeviceMetricsOverride', {'width': 1440, 'height': 1100, 'deviceScaleFactor': 1, 'mobile': False})
            c.evaluate('document.fonts.ready')
            assert c.evaluate('getComputedStyle(document.querySelector(".reading-copy p")).fontFamily.includes("Mori")')
            assert c.evaluate('getComputedStyle(document.querySelector("#notebook-collection .column-heading h2")).fontFamily.includes("Editorial New")')
            assert c.evaluate('document.fonts.check(\'400 30px "Editorial New"\')')
            assert c.evaluate('document.querySelectorAll(".reading-reference").length===4')
            assert c.evaluate('document.body.innerText.includes("What might a recipe, a weaving pattern, a poem, or a homemade game reveal")')
            assert c.evaluate('document.querySelector("[data-project-type=project] .project-link a").href.includes("10.1007/s00146-025-02689-w")')
            c.click('[data-repository-filter=project]')
            c.wait('document.querySelectorAll("[data-notebook-entry]").length===1 && location.search.includes("view=project")')
            assert c.evaluate('document.querySelector("#notebook-collection .column-title").textContent === "Prāsa"')
            c.click('[data-repository-filter=experiment]')
            c.wait('document.querySelectorAll("[data-notebook-entry]").length===1 && location.search.includes("view=experiment")')
            assert c.evaluate('document.querySelector("#notebook-collection .column-title").textContent === "experiments with rice"')
            c.click('[data-repository-filter=practice]')
            c.wait('document.querySelectorAll("[data-notebook-entry]").length===0 && document.querySelector(".repository-empty")!==null')
            assert c.evaluate('document.querySelector("#notebook-variations .column-title").textContent === "what belongs here next?"')
            c.click('[data-repository-filter=all]')
            c.wait('document.querySelectorAll("[data-notebook-entry]").length===2')
            c.fill('#your-definition', 'QA definition: a situated way of working with rules.')
            c.click('#definition-suggestion button')
            c.wait('document.querySelector("[name=account]")!==null')
            assert c.evaluate('document.querySelector("[name=account]").value.includes("QA definition")')
            assert c.evaluate('document.querySelector("[name=title]").value==="a definition of vernacular computing"')
            visit('/practices/experiments-with-rice', '#account')
            assert c.evaluate('document.querySelector("#account").textContent.includes("potential computational material")')
            assert c.evaluate('document.querySelector(".project-media img").getAttribute("src")==="/project-images/experiments-with-rice.JPG"')
            visit('/')
            c.wait('document.querySelectorAll("[data-reading-column]").length===4')
            initial_widths = c.evaluate('Array.from(document.querySelectorAll("[data-reading-column]")).map(x=>x.getBoundingClientRect().width)')
            assert initial_widths[0] > initial_widths[1] * 1.5, initial_widths
            screenshot('home-desktop.png', 1440, 1100)
            rect = c.evaluate('(() => { const r=document.querySelectorAll("[data-reading-column]")[1].getBoundingClientRect(); return {x:r.x+r.width/2,y:r.y+100}; })()')
            c.call('Input.dispatchMouseEvent', {'type': 'mouseMoved', **rect})
            c.wait('document.querySelectorAll("[data-reading-column]")[1].dataset.active==="true"')
            time.sleep(.75)
            widths = c.evaluate('Array.from(document.querySelectorAll("[data-reading-column]")).map(x=>x.getBoundingClientRect().width)')
            assert widths[1] > widths[0] * 1.5, widths
            assert c.evaluate('parseFloat(getComputedStyle(document.querySelectorAll("[data-reading-column]")[1]).fontSize)>parseFloat(getComputedStyle(document.querySelectorAll("[data-reading-column]")[0]).fontSize)')
            screenshot('home-column-expanded.png', 1440, 1100)
            c.call('Input.dispatchMouseEvent', {'type': 'mouseMoved', 'x': 5, 'y': 5})
            assert c.evaluate('document.querySelectorAll("[data-reading-column]")[1].dataset.active==="true"')
            c.evaluate('document.querySelectorAll("[data-expand-column]")[2].focus()')
            c.wait('document.querySelectorAll("[data-reading-column]")[2].dataset.active==="true"')
            c.click('[data-expand-column]')
            c.evaluate('window.scrollTo(0,0)')
            screenshot('home-mobile.png', 390, 844)
            c.click('[data-column-jump="notebook-connections"]')
            c.wait('document.querySelector("#notebook-connections").getBoundingClientRect().top<110 && window.scrollY>0')
            screenshot('home-mobile-connections.png', 390, 844)
            c.evaluate('window.scrollTo(0,0)')
            screenshot('home-320.png', 320, 760)
            visit('/explore')
            c.fill('#search', 'nothing-matches-this'); c.click('#search-form button[type=submit]')
            c.wait('document.querySelector(".empty") !== null')
            c.call('Page.reload'); c.wait('document.querySelector(".empty") !== null && !document.querySelector(".loading")')
            assert c.evaluate('location.search.includes("nothing-matches-this")')
            visit('/explore?tag=food+and+cooking')
            c.wait('document.querySelectorAll("[data-notebook-entry]").length===2')
            c.click('[data-tag="craft and making"]')
            c.wait('document.querySelector(".empty") !== null')
            c.evaluate('history.back()'); c.wait('document.querySelectorAll("[data-notebook-entry]").length===2')
            visit('/practices/rice-water', '#account')
            c.click('.citation-ref'); c.wait('location.hash==="#reference-1"')
            c.click('#reference-1 > a'); c.wait('document.querySelector("#source-reference")!==null')
            assert c.evaluate('document.body.innerText.includes("documents this practice")')
            screenshot('source-mobile.png', 390, 844)
            visit('/contribute?type=practice&prompt=measuring+without+a+tool', '#contribution-form')
            c.fill('[name=title]', 'QA — a familiar measure')
            c.click('#contribution-form button[type=submit]')
            assert c.evaluate('document.querySelector("[name=title]").value === "QA — a familiar measure"')
            assert c.evaluate('document.querySelector("[name=summary]").validity.valueMissing')
            c.fill('[name=summary]', 'An automated browser test account, not cultural testimony.')
            c.click('#contribution-form button[type=submit]'); c.wait('document.querySelector("[name=relationship]")!==null')
            c.fill('[name=relationship]', 'personal experience'); c.fill('[name=context]', 'A clearly labelled test account.')
            c.click('#contribution-form button[type=submit]'); c.wait('document.querySelector("[name=account]")!==null')
            c.fill('[name=account]', 'Observe a familiar measure and adjust it.')
            c.click('#form-back'); c.wait('document.querySelector("[name=relationship]")!==null')
            assert c.evaluate('document.querySelector("[name=relationship]").value==="personal experience"')
            c.click('#contribution-form button[type=submit]'); c.wait('document.querySelector("[name=account]")!==null')
            assert c.evaluate('document.querySelector("[name=account]").value.includes("Observe")')
            c.click('#contribution-form button[type=submit]'); c.wait('document.querySelector("#add-reference")!==null')
            c.click('#contribution-form button[type=submit]'); c.wait('document.querySelector("[name=email]")!==null')
            c.fill('[name=display_name]', 'Browser test contributor'); c.fill('[name=email]', 'browser@example.test')
            c.click('[name=publication_permission]'); c.click('[name=rights_confirmation]')
            screenshot('contribution-mobile.png', 390, 844)
            c.click('#contribution-form button[type=submit]'); c.wait('document.querySelector(".public-preview")!==null')
            assert not c.evaluate('document.querySelector(".public-preview").innerText.includes("browser@example.test")')
            c.click('#contribution-form button[type=submit]'); c.wait('document.querySelector(".confirmation")!==null')
            c.click('#request-management'); c.wait('document.querySelector("#request-management").innerText.includes("requested")')
            outbox = Path(work) / 'data/mail.jsonl'
            access = json.loads(outbox.read_text().splitlines()[-1])['link']
            c.call('Page.navigate', {'url': access}); c.wait('document.querySelector("#verify-link")!==null')
            c.click('#verify-link'); c.wait('document.querySelector(".submission-card")!==null')
            assert c.evaluate('document.body.innerText.includes("QA — a familiar measure")')
            c.evaluate('document.querySelector("[data-owner-confirm]").closest("details").querySelector("summary").click()')
            c.click('[data-owner-confirm] input')
            c.click('[data-owner-confirm] label:nth-of-type(2) input')
            c.click('[data-owner-confirm] button')
            c.wait('document.querySelector("[data-owner-confirm]")===null && document.querySelector(".submission-card")!==null && !document.querySelector(".loading")')
            screenshot('manage-desktop.png', 1200, 900)
            # Confirm the public cannot see the submitted account, then review using an explicit editor.
            c.click('#sign-out'); c.wait('document.querySelector("#login-form")!==null')
            server.store.mail_link('editor@example.test')
            editor_link = json.loads(outbox.read_text().splitlines()[-1])['link']
            c.call('Page.navigate', {'url': editor_link}); c.wait('document.querySelector("#verify-link")!==null')
            c.click('#verify-link'); c.wait('document.querySelector("#sign-out")!==null')
            visit('/admin', '.queue-tabs')
            c.evaluate('Array.from(document.querySelectorAll(".submission-card")).find(x=>x.innerText.includes("QA — a familiar measure")).querySelector("a").click()')
            c.wait('document.querySelector("#review-form")!==null')
            c.fill('#decision', 'published'); c.click('#review-form button')
            c.wait('document.querySelector(".queue-tabs")!==null && !document.querySelector("#review-form")')
            assert any(x['title'] == 'QA — a familiar measure' for x in server.store.collection('practice'))
            screenshot('admin-desktop.png', 1440, 1000)
            # Source-only suggestions can become annotated links to several practices.
            visit('/contribute?type=source', '#contribution-form')
            c.fill('[name="source.type"]', 'book or chapter')
            c.fill('[name="source.title"]', 'QA source — a print reference')
            c.fill('[name="source.annotation"]', 'A clearly labelled test reference without a URL.')
            c.fill('[name="source.locator"]', 'p. 12')
            c.click('#contribution-form button[type=submit]'); c.wait('document.querySelector("[name=email]")!==null')
            c.click('[name=publication_permission]'); c.click('[name=rights_confirmation]')
            c.click('#contribution-form button[type=submit]'); c.wait('document.querySelector(".public-preview")!==null')
            c.click('#contribution-form button[type=submit]'); c.wait('document.querySelector(".confirmation")!==null')
            with server.store.connect() as db:
                source_id = db.execute('SELECT entities.id FROM entities JOIN revisions ON revisions.entity_id=entities.id WHERE entities.kind="source" AND revisions.content LIKE ?', ('%QA source — a print reference%',)).fetchone()[0]
            visit('/admin?review=' + source_id, '#review-form')
            c.fill('[data-link-field=practice_id]', 'demo-rice-water')
            c.fill('[data-link-field=annotation]', 'A test connection to the first practice.')
            c.click('#add-connection')
            c.fill('[data-connection]:nth-of-type(2) [data-link-field=practice_id]', 'demo-knitting-repeat')
            c.fill('[data-connection]:nth-of-type(2) [data-link-field=annotation]', 'A separate test connection to another practice.')
            c.fill('#decision', 'published'); c.click('#review-form button[type=submit], #review-form > button:last-child')
            c.wait('document.querySelector(".queue-tabs")!==null && !document.querySelector("#review-form")')
            assert len([x for x in server.store.collection('source') if x['id'] == source_id]) == 1
            for slug in ['rice-water', 'knitting-repeat']:
                assert any(x['source_id'] == source_id for x in server.store.detail(slug, 'practice')['citations'])
            # Repeating source fields preserve mixed metadata, Unicode, and media input.
            visit('/contribute?type=practice', '#contribution-form')
            c.fill('[name=title]', 'QA — mixed attachments'); c.fill('[name=summary]', 'Test only.')
            c.click('#contribution-form button[type=submit]'); c.wait('document.querySelector("[name=relationship]")!==null')
            c.fill('[name=relationship]', 'source-based research')
            c.click('#contribution-form button[type=submit]'); c.wait('document.querySelector("[name=account]")!==null')
            c.fill('[name=account]', 'A test account with several references.')
            c.click('#contribution-form button[type=submit]'); c.wait('document.querySelector("#add-reference")!==null')
            c.click('#contribution-form button[type=submit]')
            c.wait('!document.querySelector("[data-error]").hidden')
            for index, typ, title, url in [(0, 'academic article', 'QA paper', ''), (1, 'video', 'QA timestamp', 'https://www.youtube.com/watch?v=TESTFIXTURE&t=90'), (2, 'blog or essay', 'QA — مقال تجريبي', 'https://example.test/blog')]:
                c.click('#add-reference'); c.fill(f'[name="ref.{index}.type"]', typ)
                c.fill(f'[name="ref.{index}.title"]', title)
                if url: c.fill(f'[name="ref.{index}.url"]', url)
            assert c.evaluate('document.querySelector("[name=\\"ref.1.url\\"]").value.includes("t=90")')
            screenshot('attachments-mobile.png', 320, 760)
            # A missing optional p5 script leaves all essential browsing intact.
            c.call('Network.enable'); c.call('Network.setCacheDisabled', {'cacheDisabled': True})
            c.call('Network.setBlockedURLs', {'urls': ['*p5-2.3.3.min.js']})
            visit('/')
            c.wait('document.querySelector("#pattern-canvas").textContent.includes("unavailable")')
            assert c.evaluate('document.querySelectorAll("[data-notebook-entry]").length > 0')
            c.call('Network.setBlockedURLs', {'urls': []})
            # Keyboard focus and reduced-motion behavior are DOM-visible checks.
            visit('/')
            c.call('Emulation.setEmulatedMedia', {'features': [{'name': 'prefers-reduced-motion', 'value': 'reduce'}]})
            c.call('Input.dispatchKeyEvent', {'type': 'keyDown', 'key': 'Tab', 'code': 'Tab', 'windowsVirtualKeyCode': 9})
            c.call('Input.dispatchKeyEvent', {'type': 'keyUp', 'key': 'Tab', 'code': 'Tab', 'windowsVirtualKeyCode': 9})
            assert c.evaluate('document.activeElement.tagName !== "BODY"')
            assert c.evaluate('getComputedStyle(document.querySelector("[data-reading-column]")).transitionDuration==="0s"')
            assert not c.errors, c.errors
            print('PASS: all three appearances, system preference, saved appearance, palette contrast, expanding columns on hover/focus, persistent reading selection, touch navigation, desktop/mobile/320px, fonts, p5 and p5 failure, search refresh/back, citations, staged validation/recovery, editorial copy/readings, project filters, definition suggestion, rice detail, mixed reference fields, private preview, persistence, email access, verified consent, editorial publication, source-only/multiple connections, keyboard focus, reduced motion. Screenshots: test-results/')
        finally:
            process.terminate()
            try: process.wait(timeout=8)
            except subprocess.TimeoutExpired: process.kill(); process.wait()
            server.shutdown(); server.server_close()


def inspect_reference():
    """Inspect the user-supplied layout reference in a fresh, isolated browser."""
    chrome = os.getenv('CHROME_BIN', '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
    artifacts = ROOT / 'test-results'
    artifacts.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='source-culture-reference-') as work:
        process = subprocess.Popen([chrome, '--headless=new', '--disable-gpu', '--disable-background-networking', '--no-first-run', '--no-default-browser-check', '--remote-debugging-port=0', '--user-data-dir=' + work, 'about:blank'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            active = Path(work) / 'DevToolsActivePort'
            for _ in range(150):
                if active.exists(): break
                if process.poll() is not None: raise RuntimeError('Chrome exited before inspection')
                time.sleep(.1)
            port = active.read_text().splitlines()[0]
            tabs = json.load(urllib.request.urlopen(f'http://127.0.0.1:{port}/json'))
            c = CDP(next(t['webSocketDebuggerUrl'] for t in tabs if t['type'] == 'page'))
            c.call('Page.enable'); c.call('Runtime.enable')
            c.call('Emulation.setDeviceMetricsOverride', {'width': 1440, 'height': 1000, 'deviceScaleFactor': 1, 'mobile': False})
            c.call('Page.navigate', {'url': 'https://www.negotiating-ungers.eu/'})
            c.wait('document.querySelectorAll(".column").length===4', timeout=30)
            time.sleep(1)
            for name in ['reference-initial.png', 'reference-hover.png']:
                if 'hover' in name:
                    rect = c.evaluate('(() => { const r=document.querySelector("#two").getBoundingClientRect(); return {x:r.x+r.width/2,y:160}; })()')
                    c.call('Input.dispatchMouseEvent', {'type': 'mouseMoved', **rect})
                    time.sleep(1)
                shot = c.call('Page.captureScreenshot', {'format': 'png'})
                (artifacts / name).write_bytes(base64.b64decode(shot['data']))
                print(name, c.evaluate('Array.from(document.querySelectorAll(".column")).map(x=>Math.round(x.getBoundingClientRect().width))'))
        finally:
            process.terminate()
            try: process.wait(timeout=8)
            except subprocess.TimeoutExpired: process.kill(); process.wait()


if __name__ == '__main__':
    if '--reference' in sys.argv:
        inspect_reference()
    else:
        run()
