#!/usr/bin/env python3
"""Local-only ZIP UI smoke test on Chromium/WebKit (synthetic source only)."""
import asyncio
import hashlib
import os
import shutil
import json
import socket
import tempfile
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
from playwright.async_api import async_playwright

HTML = Path(__file__).resolve().parent.parent / 'index.html'

class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

async def check(browser_type, source_dir: Path, url: str):
    engine=browser_type.name
    options={"headless": True}
    if engine == "chromium":
        local_chromium=shutil.which("chromium") or shutil.which("chromium-browser")
        if local_chromium:
            options["executable_path"] = local_chromium
            options["args"] = ["--no-sandbox"]
    browser=await browser_type.launch(**options)
    page=await browser.new_page(accept_downloads=True, viewport={"width": 375,"height": 812},is_mobile=True,device_scale_factor=2)
    errors=[]
    unexpected=[]
    page.on('pageerror', lambda ex:errors.append(str(ex)))
    page.on('request', lambda req: unexpected.append(req.url) if req.url.startswith(('http://','https://')) and not req.url.startswith('http://127.0.0.1:') else None)
    try:
        if os.environ.get('RUN_FILE_URL') == '1':
            await page.goto(HTML.resolve().as_uri(),wait_until='domcontentloaded')
        elif os.environ.get('RUN_OFFLINE_SET_CONTENT') == '1':
            await page.set_content(HTML.read_text(encoding='utf-8'))
        else:
            await page.goto(url,wait_until='domcontentloaded')
        assert await page.title(), 'Page title missing'
        await page.locator('#file79').set_input_files(str(source_dir/'v79.zip'))
        await page.locator('#file77').set_input_files(str(source_dir/'v77.zip'))
        await page.locator('#analyze').click()
        await page.locator('#results.visible').wait_for(timeout=25000)
        await page.locator('#verifyContent').click()
        await page.get_by_text('ソース内容SHA-256の検証結果（実データ）').wait_for(timeout=25000)
        async with page.expect_download(timeout=20000) as promise:
            await page.locator('#download').click()
        path=source_dir/f'comparison-{engine}.json'
        await (await promise.value).save_as(path)
        obj=json.loads(path.read_text())
        cv=obj['contentVerification']
        assert cv['status']=='PASS',cv
        assert cv['diff']['changed']==['src/app.js'],cv['diff']
        assert cv['diff']['added']==['src/mobile.js'],cv['diff']
        expected_hash=hashlib.sha256(b'const version=79;').hexdigest()
        assert cv['hashes']['v79']['src/app.js']==expected_hash,cv
        assert not errors, errors
        assert not unexpected, unexpected
        mode='file://' if os.environ.get('RUN_FILE_URL') == '1' else 'HTTP'
        print(f'PASS {engine} {mode}: ZIP comparison, source SHA-256, report JSON, 375x812 viewport, no outbound requests')
    finally:
        await browser.close()

async def run():
    with tempfile.TemporaryDirectory() as td:
        d=Path(td)
        with ZipFile(d/'v77.zip','w',ZIP_DEFLATED) as z:
            z.writestr('v77/src/app.js',b'const version=77;')
        with ZipFile(d/'v79.zip','w',ZIP_DEFLATED) as z:
            z.writestr('v79/src/app.js',b'const version=79;')
            z.writestr('v79/src/mobile.js',b'export const mobile=true;')
        server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(HTML.parent)))
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        url=f'http://127.0.0.1:{server.server_port}/index.html'
        try:
            async with async_playwright() as playwright:
                if os.environ.get("SKIP_CHROMIUM") != "1":
                    await check(playwright.chromium,d,url)
                if os.environ.get("SKIP_WEBKIT") != "1":
                    await check(playwright.webkit,d,url)
        finally:
            server.shutdown()

if __name__=='__main__':
    asyncio.run(run())