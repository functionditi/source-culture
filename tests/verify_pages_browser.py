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

            def visit(path, selector='h1', dismiss_welcome=True):
                c.call('Page.navigate', {'url': base + path})
                ready(selector)
                if dismiss_welcome:
                    c.evaluate('document.querySelector(".welcome-dialog[open] .welcome-close")?.click()')

            home_spacing = {}

            def screenshot(name, width):
                c.call('Emulation.setDeviceMetricsOverride', {'width': width, 'height': 1100, 'deviceScaleFactor': 1, 'mobile': width < 600})
                time.sleep(.6)
                assert c.evaluate('document.documentElement.scrollWidth <= innerWidth'), f'Horizontal overflow at {width}px'
                spacing = c.evaluate('''(() => {
                  const main = getComputedStyle(document.querySelector('main'));
                  const header = getComputedStyle(document.querySelector('.site-header'));
                  return [main.paddingLeft, main.paddingRight, header.paddingTop, header.paddingBottom];
                })()''')
                if c.evaluate('document.body.dataset.view === "notebook"'):
                    home_spacing[width] = spacing
                elif c.evaluate('document.body.dataset.view === "browse"'):
                    assert spacing == home_spacing[width], f'Page padding differs from home at {width}px: {spacing}'
                data = c.call('Page.captureScreenshot', {'format': 'png', 'captureBeyondViewport': False})
                (artifacts / name).write_bytes(base64.b64decode(data['data']))

            c.call('Emulation.setDeviceMetricsOverride', {'width': 1440, 'height': 1100, 'deviceScaleFactor': 1, 'mobile': False})
            visit('/', dismiss_welcome=False)
            c.wait('document.querySelectorAll("[data-notebook-entry]").length === 2')
            c.wait('document.querySelector(".welcome-dialog")?.open')
            assert c.evaluate('document.querySelector(".welcome-dialog").matches(":modal") && document.querySelector(".welcome-dialog").contains(document.activeElement)')
            assert c.evaluate('document.querySelector(".welcome-dialog a").pathname === "/source-culture/about"')
            screenshot('welcome-desktop.png', 1440)
            screenshot('welcome-mobile.png', 390)
            screenshot('welcome-320.png', 320)
            for _ in range(4):
                c.call('Input.dispatchKeyEvent', {'type': 'keyDown', 'key': 'Tab', 'code': 'Tab', 'windowsVirtualKeyCode': 9})
                c.call('Input.dispatchKeyEvent', {'type': 'keyUp', 'key': 'Tab', 'code': 'Tab', 'windowsVirtualKeyCode': 9})
                assert c.evaluate('document.querySelector(".welcome-dialog").contains(document.activeElement)')
            c.call('Input.dispatchKeyEvent', {'type': 'keyDown', 'key': 'Escape', 'code': 'Escape', 'windowsVirtualKeyCode': 27})
            c.call('Input.dispatchKeyEvent', {'type': 'keyUp', 'key': 'Escape', 'code': 'Escape', 'windowsVirtualKeyCode': 27})
            c.wait('document.querySelector(".welcome-dialog") === null')
            assert c.evaluate('!document.documentElement.classList.contains("welcome-open")')
            c.wait('Array.from(document.querySelectorAll(".project-media img")).every(img => img.naturalWidth > 0)')
            assert c.evaluate('document.querySelector("#mode-notice").hidden')
            assert c.evaluate('document.querySelector("#definition-suggestion") === null')
            assert c.evaluate('document.body.innerText.includes("read-only")')
            screenshot('pages-desktop.png', 1440)
            screenshot('pages-mobile.png', 390)
            screenshot('pages-small-mobile.png', 320)
            c.click('[data-repository-filter="experiment"]')
            c.wait('document.querySelectorAll("[data-notebook-entry]").length === 1')
            assert c.evaluate('document.querySelector(".welcome-dialog") === null')
            assert c.evaluate('location.pathname === "/source-culture/" && location.search === "?view=experiment"')
            c.click('[data-nav="explore"]')
            ready('#search-form')
            assert c.evaluate('document.querySelector(".explore-gallery") !== null && document.querySelector("[data-reading-room]") === null')
            assert c.evaluate('!document.querySelector(".browse-filters").open')
            widths = c.evaluate('Array.from(document.querySelectorAll(".gallery-entry")).map(el => el.getBoundingClientRect().width)')
            assert len(widths) == 2 and abs(widths[0] - widths[1]) < 1
            point = c.evaluate('(() => { const r = document.querySelectorAll(".gallery-entry")[1].getBoundingClientRect(); return {x:r.x+r.width/2,y:r.y+80}; })()')
            c.call('Input.dispatchMouseEvent', {'type': 'mouseMoved', **point})
            c.evaluate('document.querySelectorAll(".gallery-entry h2 a")[1].focus()')
            time.sleep(.7)
            assert c.evaluate('Array.from(document.querySelectorAll(".gallery-entry")).map(el => el.getBoundingClientRect().width)') == widths
            c.evaluate('window.scrollTo(0,0)')
            screenshot('explore-gallery-desktop.png', 1440)
            screenshot('explore-gallery-mobile.png', 390)
            screenshot('explore-gallery-320.png', 320)
            c.call('Emulation.setDeviceMetricsOverride', {'width': 1440, 'height': 1100, 'deviceScaleFactor': 1, 'mobile': False})
            c.fill('#search', 'rice')
            c.evaluate('document.querySelector("#search-form").requestSubmit()')
            c.wait('document.querySelectorAll("[data-notebook-entry]").length === 1')
            assert c.evaluate('location.pathname === "/source-culture/explore" && location.search.includes("rice")')
            c.call('Page.reload')
            ready('#search-form')
            c.wait('document.querySelectorAll("[data-notebook-entry]").length === 1')
            c.click('[data-notebook-entry] h2 a')
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
            assert c.evaluate('document.querySelector("#source-theme-all").checked')
            screenshot('sources-list-desktop.png', 1440)
            screenshot('sources-list-mobile.png', 390)
            screenshot('sources-list-320.png', 320)
            c.click('#source-theme-vernacular')
            c.wait('document.querySelectorAll(".source-card").length === 2')
            assert c.evaluate('document.activeElement.id === "source-theme-vernacular"')
            assert c.evaluate('document.querySelector(".source-list").textContent.includes("Dhulipalla") && document.querySelector(".source-list").textContent.includes("Swalwell")')
            c.call('Page.reload')
            ready('#source-search')
            assert c.evaluate('document.querySelector("#source-theme-vernacular").checked && document.querySelectorAll(".source-card").length === 2')
            c.fill('#source-type', 'book or chapter')
            c.wait('document.querySelectorAll(".source-card").length === 1')
            assert c.evaluate('document.querySelector(".source-list").textContent.includes("Swalwell")')
            c.click('#source-theme-culture-power')
            c.wait('document.querySelector(".source-list").textContent.includes("Yuk Hui")')
            assert c.evaluate('document.querySelectorAll(".source-card").length === 1 && document.querySelector("#source-type").value === "book or chapter"')
            c.call('Input.dispatchKeyEvent', {'type': 'keyDown', 'key': 'ArrowLeft', 'code': 'ArrowLeft', 'windowsVirtualKeyCode': 37})
            c.call('Input.dispatchKeyEvent', {'type': 'keyUp', 'key': 'ArrowLeft', 'code': 'ArrowLeft', 'windowsVirtualKeyCode': 37})
            c.wait('document.querySelector("#source-theme-vernacular")?.checked && document.querySelector(".source-list").textContent.includes("Swalwell")')
            assert c.evaluate('document.activeElement.id === "source-theme-vernacular"')
            c.fill('#q', 'Hui')
            c.evaluate('document.querySelector("#source-search").requestSubmit()')
            c.wait('document.querySelector(".browse-empty") !== null')
            c.click('.browse-results-meta a')
            c.wait('document.querySelectorAll(".source-card").length === 4')
            c.fill('#source-type', 'academic article')
            c.wait('document.querySelectorAll(".source-card").length === 1')
            assert c.evaluate('location.search.includes("type=academic")')
            c.call('Page.reload')
            ready('#source-search')
            assert c.evaluate('document.querySelectorAll(".source-card").length === 1')
            c.click('.browse-results-meta a')
            c.wait('document.querySelectorAll(".source-card").length === 4')
            c.fill('#q', 'Swalwell')
            c.evaluate('document.querySelector("#source-search").requestSubmit()')
            c.wait('document.querySelectorAll(".source-card").length === 1')
            c.click('.source-card h2 a')
            ready('#source-reference')
            assert c.evaluate('document.querySelector("#source-reference").textContent.includes("Swalwell")')
            visit('/about/', '.about-page')
            assert c.evaluate('Array.from(document.querySelectorAll(".about-details details")).every(el => !el.open)')
            screenshot('about-simple-desktop.png', 1440)
            screenshot('about-simple-mobile.png', 390)
            screenshot('about-simple-320.png', 320)
            c.click('.site-footer a[href$="#privacy"]')
            c.wait('document.querySelector("#privacy")?.open')
            visit('/about/#sharing', '#sharing')
            assert c.evaluate('document.querySelector("#sharing").open')
            visit('/about/#privacy')
            assert c.evaluate('document.querySelector("#privacy").open')
            assert c.evaluate('document.querySelector("#privacy").textContent.includes("does not accept submissions")')
            visit('/', dismiss_welcome=False)
            c.wait('document.querySelector(".welcome-dialog")?.open')
            for kind in ['mousePressed', 'mouseReleased']:
                c.call('Input.dispatchMouseEvent', {'type': kind, 'x': 4, 'y': 4, 'button': 'left', 'clickCount': 1})
            c.wait('document.querySelector(".welcome-dialog") === null')
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
