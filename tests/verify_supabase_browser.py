"""Check the real Pages frontend with a synthetic Supabase transport.

The SQL and Edge Function have separate integration tests. This test exercises
the browser's form, routing, callback, and session behavior without a live account.
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
from server.app import RELATIONSHIPS
from verify_browser import CDP


def run():
    artifacts = ROOT / 'test-results'
    artifacts.mkdir(exist_ok=True)
    chrome = os.getenv('CHROME_BIN', '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
    with tempfile.TemporaryDirectory(prefix='source-culture-supabase-browser-') as temporary:
        work = Path(temporary)
        snapshot = build(work / 'public/source-culture', '/source-culture/')
        snapshot['config'].update(mode='supabase', relationships=RELATIONSHIPS)
        class CachedPagesHandler(SimpleHTTPRequestHandler):
            def end_headers(self):
                self.send_header('Cache-Control', 'public, max-age=3600')
                super().end_headers()

        server = ThreadingHTTPServer(('127.0.0.1', 0), partial(CachedPagesHandler, directory=str(work / 'public')))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = f'http://127.0.0.1:{server.server_port}/source-culture'
        profile = work / 'chrome'
        process = subprocess.Popen([chrome, '--headless=new', '--disable-gpu', '--disable-background-networking', '--no-first-run',
                                    '--no-default-browser-check', '--remote-debugging-port=0', '--user-data-dir=' + str(profile), 'about:blank'],
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
            mock = 'const snapshot=' + json.dumps(snapshot) + ';' + '''
              const originalFetch=window.fetch;
              window.__supabaseTest={};
              window.fetch=async function(url,options={}) {
                const target=new URL(url,location.href);
                if(target.hostname!=='source-test.supabase.co')return originalFetch(url,options);
                const path=target.searchParams.get('path'),payload=JSON.parse(options.body||'{}');
                const signed=options.headers?.Authorization==='Bearer synthetic-browser-token';
                let data;
                if(path==='/config')data=snapshot.config;
                else if(path==='/session')data={user:signed?{email:'editor@example.test',editor:true}:null,csrf:null};
                else if(path==='/auth/verify')data={access_token:'synthetic-browser-token',expires_at:Math.floor(Date.now()/1000)+3600};
                else if(path==='/auth/request')data={message:'Check your inbox.'};
                else if(path==='/submissions'){window.__supabaseTest.submission=payload;data={id:'synthetic-submission'};}
                else if(path==='/mine'||path==='/admin')data=[];
                else if(path==='/practices')data=snapshot.practices;
                else if(path==='/sources')data=snapshot.sources;
                else data={error:'Unexpected browser test request'};
                return new Response(JSON.stringify(data),{status:data.error?500:200,headers:{'Content-Type':'application/json'}});
              };
            '''
            c.call('Page.addScriptToEvaluateOnNewDocument', {'source': mock})

            def visit(path, selector):
                c.call('Page.navigate', {'url': base + path})
                c.wait(f'document.querySelector({json.dumps(selector)}) !== null && !document.querySelector(".loading")')

            def submit():
                c.evaluate('document.querySelector("#contribution-form").requestSubmit()')

            def screenshot(name, width, height=1000):
                c.call('Emulation.setDeviceMetricsOverride', {'width': width, 'height': height, 'deviceScaleFactor': 1, 'mobile': width < 600})
                c.evaluate('document.fonts.ready')
                assert c.evaluate('document.documentElement.scrollWidth <= innerWidth')
                shot = c.call('Page.captureScreenshot', {'format': 'png'})
                (artifacts / name).write_bytes(base64.b64decode(shot['data']))

            # Reproduce a returning visitor: HTML and the complete static module
            # graph are still fresh in the browser cache when live forms launch.
            visit('/manage/', 'h1')
            c.wait('document.body.innerText.includes("This version of Source Culture is read-only.")')
            build(work / 'public/source-culture', '/source-culture/',
                  'https://source-test.supabase.co', 'sb_publishable_public_test_key_1234567890')
            visit('/manage/?v=contributions-20261026#token=synthetic-warm-cache', '#verify-link')
            assert c.evaluate('location.hash === "" && location.pathname === "/source-culture/manage"')

            visit('/contribute/', '.contribution-choices')
            assert c.evaluate('document.querySelectorAll(".contribution-choices a").length === 2')
            assert c.evaluate('!document.querySelector("[data-disclosure=ideas]").open')
            screenshot('contribution-choices-desktop.png', 1440)
            screenshot('contribution-choices-mobile.png', 390, 844)
            screenshot('contribution-choices-320.png', 320, 760)

            visit('/contribute/?type=practice', '#f-title')
            assert c.evaluate('document.querySelector("#mode-notice").hidden')
            assert c.evaluate('document.querySelectorAll("#contribution-form input, #contribution-form textarea").length === 2')
            screenshot('contribution-write-desktop.png', 1440)
            screenshot('contribution-write-mobile.png', 390, 844)
            c.fill('#f-title', 'A browser-tested practice')
            c.fill('#f-account', 'This is the account entered through the real form.')
            submit()
            c.fill('#f-relationship', 'personal experience')
            assert c.evaluate('Array.from(document.querySelectorAll("#contribution-form details")).every(d => !d.open)')
            screenshot('contribution-context-mobile.png', 390, 844)
            submit()
            c.fill('#f-email', 'contributor@example.test')
            c.click('input[name="publication_permission"]')
            c.click('input[name="rights_confirmation"]')
            c.click('[data-disclosure=preview] > summary')
            assert c.evaluate('document.querySelector(".public-preview").textContent.includes("This is the account")')
            submit()
            c.wait('document.querySelector("#request-management") !== null')
            assert c.evaluate('window.__supabaseTest.submission.title === "A browser-tested practice"')
            assert c.evaluate('window.__supabaseTest.submission.summary === "This is the account entered through the real form."')
            assert c.evaluate('document.querySelector(".confirmation a").pathname === "/source-culture/explore"')
            c.click('#request-management')
            c.wait('document.querySelector("#request-management").textContent.includes("check your inbox")')
            visit('/manage/?v=contributions-20261026#token=synthetic-link-hash', '#verify-link')
            assert c.evaluate('location.hash === "" && location.pathname === "/source-culture/manage"')
            c.click('#verify-link')
            c.wait('document.querySelector(".login-state") !== null')
            # The old unversioned Manage HTML is still cached. Reloading after
            # sign-in must keep the version marker while the token stays removed.
            c.call('Page.reload')
            c.wait('document.querySelector(".login-state") !== null')
            assert c.evaluate('location.hash === "" && new URLSearchParams(location.search).get("v") === "contributions-20261026"')
            c.click('.login-state a')
            c.wait('location.pathname === "/source-culture/admin" && document.querySelector(".queue-tabs") !== null')
            c.call('Page.reload')
            c.wait('document.querySelector(".queue-tabs") !== null')
            visit('/about/', '#privacy')
            assert c.evaluate('document.querySelector("#privacy").textContent.includes("stays private")')
            assert c.evaluate('!document.querySelector("#privacy").open && document.querySelector("#participate a").getAttribute("href").includes("/contribute")')

            # Required fields inside optional sections must become reachable.
            visit('/contribute/?type=practice', '#f-title')
            c.fill('#f-title', 'A research account')
            c.fill('#f-account', 'An account based on a print source.')
            submit()
            c.fill('#f-relationship', 'source-based research')
            assert c.evaluate('document.querySelector("[data-disclosure=attachments]").open')
            submit()
            assert c.evaluate('!document.querySelector("[data-error]").hidden')
            c.click('#add-reference')
            c.fill('[name="ref.0.type"]', 'book or chapter')
            c.click('[data-disclosure=attachments] > summary')
            submit()
            assert c.evaluate('document.querySelector("[data-disclosure=attachments]").open')
            assert c.evaluate('document.querySelector("[name=\\"ref.0.title\\"]").validity.valueMissing')
            c.fill('[name="ref.0.title"]', 'A print reference')
            submit()
            c.wait('document.querySelector("#f-email") !== null')
            c.click('[data-disclosure=draft] > summary')
            c.fill('#f-display_name', 'Draft credit')
            c.click('#save-draft')
            c.call('Page.reload')
            c.wait('document.querySelector("#f-title") !== null')
            assert c.evaluate('document.querySelector("#f-title").value === "A research account"')
            assert c.evaluate('document.querySelector("#f-account").value === "An account based on a print source."')
            submit()
            assert c.evaluate('document.querySelector("[name=\\"ref.0.title\\"]").value === "A print reference"')
            submit()
            assert c.evaluate('document.querySelector("#f-display_name").value === "Draft credit"')
            assert c.evaluate('!document.querySelector("[name=publication_permission]").checked && !document.querySelector("[name=rights_confirmation]").checked')
            c.click('[data-disclosure=draft] > summary')
            c.click('#clear-draft')

            # Oral sources retain explicit permission; corrections and variations
            # still reach review without the removed description field.
            visit('/contribute/?type=source', '#contribution-form')
            c.fill('[name="source.type"]', 'interview or oral account')
            c.fill('[name="source.title"]', 'An oral account')
            c.fill('[name="source.annotation"]', 'A related firsthand account.')
            submit()
            assert c.evaluate('document.querySelector("[name=\\"source.oral_permission\\"]").validity.valueMissing')
            c.click('[name="source.oral_permission"]')
            submit()
            c.wait('document.querySelector("#f-email") !== null')
            visit('/contribute/?type=correction', '#f-title')
            c.fill('#f-title', 'A correction')
            c.fill('#f-account', 'Please update this detail.')
            submit()
            c.wait('document.querySelector("#f-email") !== null')
            visit('/contribute/?type=variation&parent=' + snapshot['practices'][0]['id'], '#f-title')
            c.fill('#f-title', 'Another way')
            c.fill('#f-account', 'My version of this practice.')
            c.fill('#f-similar', 'The basic approach.')
            c.fill('#f-changes', 'The measure we use.')
            submit()
            c.fill('#f-relationship', 'learned from someone')
            submit()
            c.wait('document.querySelector("#f-email") !== null')

            assert not c.errors, c.errors
            c.call('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844, 'deviceScaleFactor': 1, 'mobile': True})
            visit('/contribute/?type=practice', '#contribution-form')
            assert c.evaluate('document.documentElement.scrollWidth <= innerWidth')
            screenshot = c.call('Page.captureScreenshot', {'format': 'png'})
            (artifacts / 'supabase-contribute-mobile.png').write_bytes(base64.b64decode(screenshot['data']))
            print('PASS: Simple contribution choices, responsive forms, three-stage practice submission, research reference validation, collapsed-field recovery, draft restoration, oral permission, corrections, variations, returning cached visitors, submission transport, project links, sign-in, and editor access. Backend transport is synthetic; no remote project or email was used.')
        finally:
            process.terminate()
            process.wait(timeout=10)
            server.shutdown()
            server.server_close()


if __name__ == '__main__':
    run()
