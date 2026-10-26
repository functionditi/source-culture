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
        snapshot = build(work / 'public/source-culture', '/source-culture/',
                         'https://source-test.supabase.co', 'sb_publishable_public_test_key_1234567890')
        snapshot['config'].update(mode='supabase', relationships=RELATIONSHIPS)
        server = ThreadingHTTPServer(('127.0.0.1', 0), partial(SimpleHTTPRequestHandler, directory=str(work / 'public')))
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

            visit('/contribute/?type=practice', '#f-title')
            assert c.evaluate('document.querySelector("#mode-notice").hidden')
            c.fill('#f-title', 'A browser-tested practice')
            c.fill('#f-summary', 'A small firsthand contribution')
            submit()
            c.fill('#f-relationship', 'personal experience')
            submit()
            c.fill('#f-account', 'This is the account entered through the real form.')
            submit()
            submit()
            c.fill('#f-email', 'contributor@example.test')
            c.click('input[name="publication_permission"]')
            c.click('input[name="rights_confirmation"]')
            submit()
            c.wait('document.querySelector(".public-preview") !== null')
            submit()
            c.wait('document.querySelector("#request-management") !== null')
            assert c.evaluate('window.__supabaseTest.submission.title === "A browser-tested practice"')
            assert c.evaluate('document.querySelector(".confirmation a").pathname === "/source-culture/explore"')
            c.click('#request-management')
            c.wait('document.querySelector("#request-management").textContent.includes("check your inbox")')
            visit('/manage/#token=synthetic-link-hash', '#verify-link')
            assert c.evaluate('location.hash === "" && location.pathname === "/source-culture/manage"')
            c.click('#verify-link')
            c.wait('document.querySelector(".login-state") !== null')
            c.click('.login-state a')
            c.wait('location.pathname === "/source-culture/admin" && document.querySelector(".queue-tabs") !== null')
            c.call('Page.reload')
            c.wait('document.querySelector(".queue-tabs") !== null')
            visit('/about/', '#privacy')
            assert c.evaluate('document.querySelector("#privacy").textContent.includes("Supabase")')
            assert not c.errors, c.errors
            c.call('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844, 'deviceScaleFactor': 1, 'mobile': True})
            visit('/contribute/?type=practice', '#contribution-form')
            assert c.evaluate('document.documentElement.scrollWidth <= innerWidth')
            screenshot = c.call('Page.captureScreenshot', {'format': 'png'})
            (artifacts / 'supabase-contribute-mobile.png').write_bytes(base64.b64decode(screenshot['data']))
            print('PASS: Supabase Pages form, submission transport, project-scoped links, explicit token confirmation, callback scrubbing, session reload, editor route, privacy copy, and mobile layout. Backend transport is synthetic; no remote project or email was used.')
        finally:
            process.terminate()
            process.wait(timeout=10)
            server.shutdown()
            server.server_close()


if __name__ == '__main__':
    run()
