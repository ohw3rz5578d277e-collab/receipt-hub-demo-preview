# Receipt Hub ZIP source intake — Draft PR #2

Mobile-friendly v119 source inspector. This is a **review-only tool**, not the Receipt Hub application or a deployment.

## How it works

1. With the HTML open in a compatible browser, select the original v79 ZIP. Optionally select v77 to compare both.
2. Run archive inspection. For full source comparison, click the SHA-256 content verification button.
3. Export the report JSON or a **source-only** ZIP to the device.
4. **Manually inspect exported source for confidential data before sharing.** Exclusion patterns are not a guarantee.

No receipt photo, customer record, original ZIP, or credential was committed to this repository.

## Regression tests

Requires Python 3, Playwright Python and Chromium (either available on PATH or installed by Playwright).

```sh
python -m pip install playwright
python -m playwright install chromium
python tools/source-intake/tests/test_browser.py
```

The suite performs 23 labeled test scenarios with synthetic ZIPs. It covers SHA-256 of decompressed source, CRC32 collision detection, source-only ZIP exports, directory/file collisions, disguised symlink metadata, path traversal, CRC mismatch, secret-pattern blocking, unsupported compression engines and related cases.

**Test scope:** Chromium at an iPhone-sized viewport plus WebKit on a Linux CI runner at 375×812. The WebKit compatibility smoke test covers synthetic ZIP import, source SHA-256 comparison, JSON export and no outbound network access. Run locally or in CI with:

```sh
python -m playwright install webkit
SKIP_CHROMIUM=1 python tools/source-intake/tests/test_browser_compat.py
```

GitHub Actions Run #4 on HEAD `3a11303a466ff6fd06dc8b75958ca4e02160bee4` completed **SUCCESS** for both browser jobs. These tests use **synthetic ZIP files** and Linux WebKit, **not** a physical iPhone Safari device and **not** the real v77/v79 ZIP files. Local `file://` handling is also not covered by this CI.

## Privacy and limitations

- All ZIP processing is local in the browser. Inline CSP uses a matching script hash and `connect-src 'none'`; no outbound network request code is present.
- ZIP source payload is never executed.
- Exclusion of secrets and personal data is best effort. Never use actual customer receipts or credentials for the test.
- This **repository is public already**. A Draft branch and Draft PR are still publicly readable, although the change has **not** been merged into main or published as a GitHub Pages page.
- Real v77/v79 source access, Receipt Hub app integration, iPhone Safari testing, production D1/R2 and accounting exports remain **unverified/unperformed**.

## Owner approval gate

Do not mark the PR ready, merge, configure Pages or change production without the owner's specific approval.