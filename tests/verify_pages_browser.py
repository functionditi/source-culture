"""Chrome smoke test of the actual static export, without the Python API.

Run: python3 tests/verify_pages_browser.py
Uses the existing local CDP harness and an isolated temporary browser profile.
"""
import base64
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from server.build_pages import build
from verify_browser import CDP


def run():
    artifacts = ROOT / 'test-results'
    artifacts.mkdir(exist_ok=True)
    chrome = os.getenv('CHROME_BIN', '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
    with tempfile.TemporaryDirectory(prefix='source-culture-pages-') as temporary:
        work = Path(temporary)
        build(work / 'public/source-culture', '/source-culture/')
        handler = partial(SimpleHTTPRequestHandler, directory=str(work / 'public'))
        server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        origin = f'http://127.0.0.1:{server.server_port}'
        base = origin + '/source-culture'
        profile = work / 'chrome'
        process = subprocess.Popen([chrome, '--headless=new', '--disable-gpu', '--disable-background-networking',
                                    '--no-first-run', '--no-default-browser-check', '--remote-debugging-port=0',
                                    '--user-data-dir=' + str(profile), 'about:blank'],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            active = profile / 'DevToolsActivePort'
            for _ in range(150):
                if active.exists():
                    break
                if process.poll() is not None:
                    raise RuntimeError('Chrome exited before opening the test browser')
                time.sleep(.1)
            port = active.read_text().splitlines()[0]
            tabs = json.load(urllib.request.urlopen(f'http://127.0.0.1:{port}/json'))
            c = CDP(next(tab['webSocketDebuggerUrl'] for tab in tabs if tab['type'] == 'page'))
            c.call('Page.enable')
            c.call('Runtime.enable')

            def ready(selector):
                c.wait(f'document.querySelector({json.dumps(selector)}) !== null && !document.querySelector(".loading")')
                c.evaluate('document.fonts.ready')
                assert c.evaluate('document.fonts.check(\'16px "Mori"\') && document.fonts.check(\'28px "Editorial New"\')')
                assert c.evaluate('getComputedStyle(document.body).backgroundColor === "rgb(73, 81, 44)"')
                assert c.evaluate('Array.from(document.querySelectorAll("a[href]")).filter(a => a.origin === location.origin).every(a => a.pathname.startsWith("/source-culture/"))')
                assert c.evaluate('performance.getEntriesByType("resource").every(r => !new URL(r.name).pathname.startsWith("/api/"))')
                assert not c.errors, c.errors

            def visit(path, selector='h1'):
                c.call('Page.navigate', {'url': base + path})
                ready(selector)

            def screenshot(name, width):
                c.call('Emulation.setDeviceMetricsOverride', {'width': width, 'height': 1100, 'deviceScaleFactor': 1, 'mobile': width < 600})
                time.sleep(.6)
                assert c.evaluate('document.documentElement.scrollWidth <= innerWidth'), f'Horizontal overflow at {width}px'
                data = c.call('Page.captureScreenshot', {'format': 'png', 'captureBeyondViewport': False})
                (artifacts / name).write_bytes(base64.b64decode(data['data']))

            c.call('Emulation.setDeviceMetricsOverride', {'width': 1440, 'height': 1100, 'deviceScaleFactor': 1, 'mobile': False})
            visit('/')
            c.wait('document.querySelectorAll("[data-notebook-entry]").length === 2')
            c.wait('Array.from(document.querySelectorAll(".project-media img")).every(img => img.naturalWidth > 0)')
            assert c.evaluate('document.querySelector("#mode-notice").hidden')
            assert c.evaluate('document.querySelector("#definition-suggestion") === null')
            assert c.evaluate('document.body.innerText.includes("read-only")')
            screenshot('pages-desktop.png', 1440)
            screenshot('pages-mobile.png', 390)
            screenshot('pages-small-mobile.png', 320)
            c.click('[data-repository-filter="experiment"]')
            c.wait('document.querySelectorAll("[data-notebook-entry]").length === 1')
            assert c.evaluate('location.pathname === "/source-culture/" && location.search === "?view=experiment"')
            c.click('[data-nav="explore"]')
            ready('#search-form')
            c.fill('#search', 'rice')
            c.evaluate('document.querySelector("#search-form").requestSubmit()')
            c.wait('document.querySelectorAll("[data-notebook-entry]").length === 1')
            assert c.evaluate('location.pathname === "/source-culture/explore" && location.search.includes("rice")')
            c.call('Page.reload')
            ready('#search-form')
            c.wait('document.querySelectorAll("[data-notebook-entry]").length === 1')
            c.click('[data-notebook-entry] h3 a')
            ready('.article-head')
            c.wait('document.querySelector(".project-media img")?.naturalWidth > 0')
            assert c.evaluate('document.querySelector("#entry-citation").textContent.includes(location.origin + "/source-culture/practices/experiments-with-rice")')
            visit('/practices/prasa/#account', '.article-head')
            c.wait('document.querySelector(".project-media img")?.naturalWidth > 0')
            c.click('.reference-list a')
            ready('#source-reference')
            assert c.evaluate('location.pathname.startsWith("/source-culture/sources/vernacular-computing")')
            visit('/sources/')
            assert c.evaluate('document.querySelectorAll(".source-card").length === 4')
            visit('/about/#privacy')
            assert c.evaluate('document.querySelector("#privacy").textContent.includes("does not accept submissions")')
            for path in ['/contribute/?type=practice', '/manage/', '/admin/']:
                visit(path)
                assert c.evaluate('document.querySelector("#main").textContent.includes("read-only")')
                assert c.evaluate('document.querySelector("#main form") === null')
            assert not c.errors, c.errors
            print('PASS: static Pages build at /source-culture/; CSS/fonts/images; project filters; search and refresh; direct links and citations; four sources; read-only pages; desktop/mobile layouts; no API calls or JavaScript errors.')
        finally:
            process.terminate()
            process.wait(timeout=10)
            server.shutdown()


if __name__ == '__main__':
    run()
