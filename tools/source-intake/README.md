# Receipt Hub ZIP source intake — Draft only

This is the v119 source-only ZIP inspector prepared for mobile browsers.

## Intended workflow
1. Open `tools/source-intake/index.html` in a browser **after explicit approval to merge and publish**.
2. Select the original v79 ZIP, optionally the v77 ZIP.
3. Run ZIP inspection and, with both originals, source SHA-256 comparison.
4. Export a source-only ZIP for a later private review.

## Privacy and limitations
- Client-side only. The bundled page has Content Security Policy `connect-src 'none'` and contains no outbound request handlers.
- The ZIP source payload is never executed.
- Common file-name and secret-pattern exclusions are best-effort only; review the extracted contents before sharing.
- The page and repository are public if published via GitHub Pages. Do not upload receipts or customer records to it.
- This is **not** the Receipt Hub application, and it has **not** been tested with the real v77/v79 original ZIPs or on iPhone Safari.
- No production D1, R2, Drive, accounting exports or deployment is part of this change.

## Deployment safety
This branch and its Draft PR are for source review. Never merge or publish without the owner's specific approval.
