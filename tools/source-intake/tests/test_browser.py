from __future__ import annotations
import asyncio
import hashlib
from pathlib import Path
import tempfile
import threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from functools import partial
from zipfile import ZipFile, ZIP_DEFLATED
from playwright.async_api import async_playwright

HTML = Path(__file__).with_name('index.html')


def zipit(path: Path, items: dict[str, bytes]) -> None:
    with ZipFile(path, 'w', ZIP_DEFLATED) as out:
        for name, contents in items.items():
            out.writestr(name, contents)


async def run():
    with tempfile.TemporaryDirectory() as d:
        base = Path(d)
        v77 = base/'receipt_hub_v77_mac_local_trial.zip'
        v79 = base/'receipt_hub_v79_mac_ready_manual_or_ocr.zip'
        unsafe = base/'invalid_source.zip'
        duplicate = base/'duplicate_source.zip'
        reserved = base/'reserved_source.zip'
        no_source = base/'no_source.zip'
        corrupt = base/'corrupt.zip'
        sensitive = base/'sensitive_source.zip'
        zipit(v77, {
            'receipt_hub_v77_mac_local_trial/src/app.js': b'const version=77;',
            'receipt_hub_v77_mac_local_trial/src/ocr.py': b'def main(): pass',
            'receipt_hub_v77_mac_local_trial/docs/old.md': b'old',
        })
        zipit(v79, {
            'receipt_hub_v79_mac_ready_manual_or_ocr/src/app.js': b'const version=79;',
            'receipt_hub_v79_mac_ready_manual_or_ocr/src/ocr.py': b'def main(): pass',
            'receipt_hub_v79_mac_ready_manual_or_ocr/src/new.ts': b'export const add = true;',
            '__MACOSX/._junk': b'mac',
        })
        zipit(unsafe, {'../data.js': b'alert(1)'})
        zipit(duplicate, {'src/test.js': b'a', 'src/TEST.js': b'b'})
        zipit(reserved, {'CON.js': b'a'})
        zipit(no_source, {'readme.md': b'hello'})
        corrupt.write_bytes(b'not-a-zip-file-data-xxxx')
        zipit(sensitive, {'app.js': b'hello', '.env': b'should-not-be-in-shared-source'})
        async with async_playwright() as play:
            browser = await play.chromium.launch(headless=True, executable_path='/usr/bin/chromium', args=['--no-sandbox'])
            page = await browser.new_page(accept_downloads=True, viewport={'width': 375, 'height': 812})
            msgs=[]; network=[]
            page.on('console', lambda m: msgs.append(m.text) if m.type=='error' else None)
            page.on('request', lambda r: network.append(r.url) if r.url.startswith('https:') or r.url.startswith('http:') else None)
            await page.set_content(HTML.read_text(encoding='utf-8'))
            await page.locator('#file79').set_input_files(str(v79))
            await page.locator('#file77').set_input_files(str(v77))
            await page.locator('#analyze').click()
            await page.locator('#results.visible').wait_for(timeout=15000)
            assert '追加' in await page.locator('#metrics').inner_text()
            data = await page.locator('#metrics').inner_text()
            assert data.split()[0] == '1', data
            assert data.split()[2] == '1', data
            assert data.split()[4] == '1', data
            assert data.split()[6] == '1', data
            assert '変更候補' in await page.locator('#details').inner_text()
            assert await page.locator('#error').is_hidden()
            async with page.expect_download() as dlinfo:
                await page.locator('#download').click()
            dl = await dlinfo.value
            saved=base/'manifest.json'; await dl.save_as(saved)
            import json
            manifest=json.loads(saved.read_text())
            assert manifest['method']=='ZIP_CENTRAL_DIRECTORY_CRC32_SIZE_NO_DECOMPRESSION'
            assert manifest['diff']=={'added':['src/new.ts'],'changed':['src/app.js'],'removed':['docs/old.md'],'unchanged':['src/ocr.py']},manifest['diff']
            assert manifest['v79']['sha256'] == hashlib.sha256(v79.read_bytes()).hexdigest()
            assert not network, network
            print('PASS mobile Chrome ZIP v77/v79 compare, real SHA-256, Mac metadata, JSON export, no outbound requests')
            # v119: actual decompressed source contents are hashed and checked.
            await page.locator('#verifyContent').click()
            await page.get_by_text('ソース内容SHA-256の検証結果（実データ）').wait_for(timeout=15000)
            detail_text=await page.locator('#details').inner_text()
            assert 'ソース内容SHA-256の検証結果' in detail_text, detail_text
            async with page.expect_download() as content_download:
                await page.locator('#download').click()
            source_manifest_file=base/'content_manifest.json'
            await (await content_download.value).save_as(source_manifest_file)
            verified=json.loads(source_manifest_file.read_text())['contentVerification']
            assert verified['status']=='PASS',verified
            assert verified['diff']=={'added':['src/new.ts'],'changed':['src/app.js'],'removed':[],'unchanged':['src/ocr.py']},verified['diff']
            assert verified['sourceFilesHashed']=={'v77':2,'v79':3}
            assert verified['hashes']['v77']['src/app.js']==hashlib.sha256(b'const version=77;').hexdigest()
            assert verified['hashes']['v79']['src/app.js']==hashlib.sha256(b'const version=79;').hexdigest()
            assert not network
            print('PASS v119 full decompressed source SHA-256 verification and manifest hashes')
            # A real, reproducible CRC32 collision: identical size and CRC32, different bytes.
            # The metadata-only pass must not mislead the stronger SHA-256 pass.
            import zlib
            left=b'BJQKJNUHCS'; right=b'PWRIMQDXUV'
            assert left != right and len(left)==len(right) and zlib.crc32(left)==zlib.crc32(right)
            collision77=base/'collision-v77.zip'; collision79=base/'collision-v79.zip'
            zipit(collision77, {'src/app.js':left})
            zipit(collision79, {'src/app.js':right})
            await page.locator('#reset').click()
            await page.locator('#file77').set_input_files(str(collision77))
            await page.locator('#file79').set_input_files(str(collision79))
            await page.locator('#analyze').click()
            await page.locator('#results.visible').wait_for(timeout=15000)
            assert '1' in await page.locator('#metrics').inner_text()
            assert '1' in (await page.locator('#metrics').inner_text()).split()[6],await page.locator('#metrics').inner_text()
            await page.locator('#verifyContent').click()
            await page.get_by_text('ソース内容SHA-256の検証結果（実データ）').wait_for(timeout=15000)
            async with page.expect_download() as dl_collision:
                await page.locator('#download').click()
            collision_json=base/'collision.json'
            await (await dl_collision.value).save_as(collision_json)
            collision_result=json.loads(collision_json.read_text())['contentVerification']['diff']
            assert collision_result == {'added': [],'changed':['src/app.js'],'removed': [],'unchanged': []},collision_result
            print('PASS v119 genuine CRC32 collision classified as changed by decompressed SHA-256')
            # Exercise the SHA-256 fallback across block boundaries with UTF-8 source.
            large_payload=("const message = 'お宮参り';\n"*160).encode('utf-8')
            large77=base/'large-v77.zip';large79=base/'large-v79.zip'
            zipit(large77, {'src/app.js':large_payload})
            zipit(large79, {'src/app.js':large_payload})
            await page.locator('#reset').click()
            await page.locator('#file77').set_input_files(str(large77))
            await page.locator('#file79').set_input_files(str(large79))
            await page.locator('#analyze').click()
            await page.locator('#results.visible').wait_for(timeout=15000)
            await page.locator('#verifyContent').click()
            await page.get_by_text('ソース内容SHA-256の検証結果（実データ）').wait_for(timeout=15000)
            async with page.expect_download() as dl_large:
                await page.locator('#download').click()
            large_json=base/'large.json'
            await (await dl_large.value).save_as(large_json)
            large_result=json.loads(large_json.read_text())['contentVerification']
            assert large_result['hashes']['v79']['src/app.js']==hashlib.sha256(large_payload).hexdigest()
            assert large_result['diff']=={'added':[],'changed':[],'removed':[],'unchanged':['src/app.js']}
            print('PASS v119 multiline Japanese UTF-8 and >64-byte SHA-256 block verification')



            await page.locator('#reset').click()
            await page.locator('#file79').set_input_files(str(v79))
            await page.locator('#analyze').click()
            await page.locator('#results.visible').wait_for(timeout=15000)
            assert 'v77未指定' in await page.locator('#result-note').inner_text()
            print('PASS v79-only mode')
            await page.locator('#verifyContent').click()
            await page.locator('#error:not([hidden])').wait_for(timeout=15000)
            assert '両方選択' in await page.locator('#error').inner_text()
            print('PASS v119 SHA verification needs both archives')

            await page.locator('#reset').click()
            await page.locator('#file79').set_input_files(str(unsafe))
            await page.locator('#analyze').click()
            await page.locator('#error:not([hidden])').wait_for(timeout=15000)
            assert '危険なパス構造' in await page.locator('#error').inner_text()
            assert await page.locator('#results').is_hidden()
            print('PASS traversal rejected')
            await page.locator('#reset').click()
            await page.locator('#file79').set_input_files(str(duplicate))
            await page.locator('#analyze').click()
            await page.locator('#error:not([hidden])').wait_for(timeout=15000)
            assert '重複' in await page.locator('#error').inner_text()
            print('PASS casefold duplicates rejected')
            for f,needle,label in [(reserved,'予約デバイス名','reserved names'),(no_source,'ソースコードが見つかりません','source required'),(corrupt,'ZIP終端','corrupt ZIP')]:
                await page.locator('#reset').click()
                await page.locator('#file79').set_input_files(str(f))
                await page.locator('#analyze').click()
                await page.locator('#error:not([hidden])').wait_for(timeout=15000)
                assert needle in await page.locator('#error').inner_text(),label
                print('PASS',label,'rejected')
            await page.locator('#reset').click()
            await page.locator('#file79').set_input_files(str(sensitive))
            await page.locator('#analyze').click()
            await page.locator('#results.visible').wait_for(timeout=15000)
            assert '要注意パス' in await page.locator('#metrics').inner_text()
            async with page.expect_download() as dlinfo2:
                await page.locator('#download').click()
            dl2=await dlinfo2.value
            saved2=base/'sensitive_report.json';await dl2.save_as(saved2)
            assert '.env' in __import__('json').loads(saved2.read_text())['v79']['sensitivePaths']
            assert 'should-not-be-in-shared-source' not in saved2.read_text()
            print('PASS sensitive file names flagged, contents never exported')
            # v117: source-only ZIP repacking, including exclusions and stored/deflated entries.
            source_v79=base/'source_candidate_v79.zip'
            zipit(source_v79, {
                'receipt_hub_v79_mac_ready_manual_or_ocr/src/app.js': b'const live = true;',
                'receipt_hub_v79_mac_ready_manual_or_ocr/config/settings.json': b'{"endpoint":"local"}',
                'receipt_hub_v79_mac_ready_manual_or_ocr/docs/README.md': b'## Intro',
                'receipt_hub_v79_mac_ready_manual_or_ocr/.env': b'PRIVATE=secret-do-not-share',
                'receipt_hub_v79_mac_ready_manual_or_ocr/secrets.json': b'{"password":"secret"}',
                'receipt_hub_v79_mac_ready_manual_or_ocr/data/receipt.png': b'\x89PNG\x00-personal-data',
                'receipt_hub_v79_mac_ready_manual_or_ocr/node_modules/lib.js': b'const thirdparty=1;',
                '__MACOSX/._app': b'metadata',
            })
            await page.locator('#reset').click()
            await page.locator('#file79').set_input_files(str(source_v79))
            await page.locator('#analyze').click()
            await page.locator('#results.visible').wait_for(timeout=15000)
            assert '共有候補 3ファイル' in await page.locator('#exportStats').inner_text()
            async with page.expect_download() as source_download:
                await page.locator('#exportSource').click()
            source_artifact=await source_download.value
            assert source_artifact.suggested_filename == 'ReceiptHub_v79_source_only_v119_for_review.zip'
            output_zip=base/'v117-export.zip'; await source_artifact.save_as(output_zip)
            with ZipFile(output_zip) as exported, ZipFile(source_v79) as original:
                names=set(exported.namelist())
                assert names == {'src/app.js','config/settings.json','docs/README.md'}, names
                for internal in names:
                    assert exported.read(internal) == original.read('receipt_hub_v79_mac_ready_manual_or_ocr/'+internal)
            assert b'PRIVATE=secret' not in output_zip.read_bytes()
            assert b'personal-data' not in output_zip.read_bytes()
            print('PASS v117 source-only ZIP export, payload extraction, secret/image/vendor exclusion')

            # ZIP local-header spoofing must not result in an export.
            tampered=base/'tampered-local-header-v79.zip'
            data=bytearray(source_v79.read_bytes())
            needle=b'src/app.js'
            # Local filename first occurrence; the central filename is intentionally unchanged.
            idx=data.find(needle)
            assert idx >= 0
            data[idx:idx+len(needle)]=b'src/axp.js'
            tampered.write_bytes(data)
            await page.locator('#reset').click()
            await page.locator('#file79').set_input_files(str(tampered))
            await page.locator('#analyze').click()
            await page.locator('#results.visible').wait_for(timeout=15000)
            await page.locator('#exportSource').click()
            await page.locator('#error:not([hidden])').wait_for(timeout=15000)
            assert 'ファイル名が不一致' in await page.locator('#error').inner_text()
            print('PASS v117 tampered local header rejected during source export')

            # Reject a file that is also an ancestor of another entry.
            # Older ZIP inspector accepted this ambiguous filesystem structure.
            parent_collision=base/'file-dir-collision.zip'
            zipit(parent_collision, {'src/app.js': b'const x=1;', 'src/app.js/child.js': b'const y=2;'})
            await page.locator('#reset').click()
            await page.locator('#file79').set_input_files(str(parent_collision))
            await page.locator('#analyze').click()
            await page.locator('#error:not([hidden])').wait_for(timeout=15000)
            assert 'ファイルとディレクトリが衝突' in await page.locator('#error').inner_text()
            assert await page.locator('#results').is_hidden()
            print('PASS file-as-directory collision rejected before source export')

            # Symlink metadata cannot be laundered by faking the creator platform.
            disguised_symlink=base/'spoofed-symlink.zip'
            from zipfile import ZipInfo, ZIP_STORED
            with ZipFile(disguised_symlink, 'w') as out:
                out.writestr('app.js', b'hello')
                link=ZipInfo('src/link.js');link.create_system=3;link.external_attr=0o120777<<16
                out.writestr(link,'app.js',compress_type=ZIP_STORED)
            fake=bytearray(disguised_symlink.read_bytes())
            c=0
            while True:
                c=fake.find(b'PK\x01\x02',c)
                assert c>=0
                nlen=int.from_bytes(fake[c+28:c+30],'little')
                name=bytes(fake[c+46:c+46+nlen])
                if name==b'src/link.js':
                    fake[c+5]=0  # origin OS byte, forged as MS-DOS
                    break
                c+=46+nlen+int.from_bytes(fake[c+30:c+32],'little')+int.from_bytes(fake[c+32:c+34],'little')
            disguised_symlink.write_bytes(fake)
            await page.locator('#reset').click()
            await page.locator('#file79').set_input_files(str(disguised_symlink))
            await page.locator('#analyze').click()
            await page.locator('#error:not([hidden])').wait_for(timeout=15000)
            assert 'シンボリックリンク' in await page.locator('#error').inner_text()
            print('PASS disguised Unix symlink mode rejected')

            # Symlinks cannot pass ZIP inspection.
            from zipfile import ZipInfo, ZIP_STORED
            symlink=base/'symlink-v79.zip'
            with ZipFile(symlink, 'w') as out:
                out.writestr('app.js', b'hello')
                link=ZipInfo('link.js'); link.create_system=3; link.external_attr=0o120777<<16
                out.writestr(link, 'app.js', compress_type=ZIP_STORED)
            await page.locator('#reset').click()
            await page.locator('#file79').set_input_files(str(symlink))
            await page.locator('#analyze').click()
            await page.locator('#error:not([hidden])').wait_for(timeout=15000)
            assert 'シンボリックリンク' in await page.locator('#error').inner_text()
            print('PASS v117 symlink rejected before source export')
            # v118: ZIP central directory CRC tampering must fail closed on export.
            crc_bad = base/'crc-tampered.zip'
            crc_data = bytearray(source_v79.read_bytes())
            cix = crc_data.find(b'PK\x01\x02')
            assert cix >= 0
            crc_data[cix + 16] ^= 0x01
            crc_data[14] ^= 0x01  # Keep local and central CRC metadata equally forged.
            crc_bad.write_bytes(crc_data)
            await page.locator('#reset').click()
            await page.locator('#file79').set_input_files(str(crc_bad))
            await page.locator('#analyze').click()
            await page.locator('#results.visible').wait_for(timeout=15000)
            await page.locator('#exportSource').click()
            await page.locator('#error:not([hidden])').wait_for(timeout=15000)
            assert 'CRC32が一致しません' in await page.locator('#error').inner_text(), await page.locator('#error').inner_text()
            print('PASS v118 tampered central CRC rejected before source ZIP export')
            # CRC must also be enforced before claiming SHA-256 verified comparison.
            await page.locator('#reset').click()
            await page.locator('#file77').set_input_files(str(v77))
            await page.locator('#file79').set_input_files(str(crc_bad))
            await page.locator('#analyze').click()
            await page.locator('#results.visible').wait_for(timeout=15000)
            await page.locator('#verifyContent').click()
            await page.locator('#error:not([hidden])').wait_for(timeout=15000)
            assert 'CRC32が一致しません' in await page.locator('#error').inner_text()
            print('PASS v119 forged CRC cannot pass SHA-256 comparison')


            # Bytes that are not UTF-8 source text must not be relabeled as .js.
            bad_text=base/'binary-masquerade.zip'
            zipit(bad_text, {'src/app.js': b'const safe = 1;\x00binary\xff'})
            await page.locator('#reset').click()
            await page.locator('#file79').set_input_files(str(bad_text))
            await page.locator('#analyze').click()
            await page.locator('#results.visible').wait_for(timeout=15000)
            await page.locator('#exportSource').click()
            await page.locator('#error:not([hidden])').wait_for(timeout=15000)
            assert 'バイナリ内容を検出' in await page.locator('#error').inner_text()
            print('PASS v118 binary masquerade rejected')

            invalid_utf8=base/'invalid-utf8.zip'
            zipit(invalid_utf8, {'src/app.js': b'hello\xff'})
            await page.locator('#reset').click()
            await page.locator('#file79').set_input_files(str(invalid_utf8))
            await page.locator('#analyze').click()
            await page.locator('#results.visible').wait_for(timeout=15000)
            await page.locator('#exportSource').click()
            await page.locator('#error:not([hidden])').wait_for(timeout=15000)
            assert 'UTF-8以外' in await page.locator('#error').inner_text()
            print('PASS v118 invalid UTF-8 source rejected')

            # These tokens are synthetic test values, never a real key.
            key_candidate=base/'secret-inline.zip'
            zipit(key_candidate, {'src/app.js': b'const key = "ghp_' + b'A'*26 + b'";'})
            await page.locator('#reset').click()
            await page.locator('#file79').set_input_files(str(key_candidate))
            await page.locator('#analyze').click()
            await page.locator('#results.visible').wait_for(timeout=15000)
            await page.locator('#exportSource').click()
            await page.locator('#error:not([hidden])').wait_for(timeout=15000)
            assert '鍵・認証情報の可能性' in await page.locator('#error').inner_text()
            print('PASS v118 high-specificity inline secret pattern rejected')

            # Browser implementations without raw DEFLATE decoding must refuse export.
            await page.evaluate("window.__SavedDS = window.DecompressionStream; window.DecompressionStream = undefined")
            await page.locator('#reset').click()
            await page.locator('#file79').set_input_files(str(source_v79))
            await page.locator('#analyze').click()
            await page.locator('#results.visible').wait_for(timeout=15000)
            await page.locator('#exportSource').click()
            await page.locator('#error:not([hidden])').wait_for(timeout=15000)
            assert '非対応' in await page.locator('#error').inner_text()
            await page.evaluate("() => { window.DecompressionStream = window.__SavedDS; return true; }")
            print('PASS v118 unsupported browser fails closed')
            assert not msgs, msgs
            await page.screenshot(path=str(base/'mobile.png'),full_page=True)
            await browser.close()


if __name__=='__main__':
    asyncio.run(run())