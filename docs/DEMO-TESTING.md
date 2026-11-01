# Public demo safety test runbook

This repository is a **public sample UI only**. Do not enter actual receipts, personal data, accounting records, credentials or invoice numbers. The demo uses browser-local sample state; it is not a production or legally compliant receipt archive.

## Offline test

With Node.js 20 or later, from the repository root:

```sh
node --test tests/public-demo-safety.test.mjs
```

This command only reads local files and runs static assertions. It does not start a server, use Cloudflare, send network requests or modify browser data.

## What the test protects

- The README retains the public demo's data-safety warning and no-sync limitation.
- The demo remains browser-local with no application network transport.
- The sample capture control is not replaced with real image upload or OCR.
- No backend entrypoint or common credential configuration file is introduced.

This is a guardrail, **not** a comprehensive security audit. Static checks cannot establish that the browser runtime is secure or that a future application is ready for real financial records.

## Future real Receipt Hub

Implement the real application in a **separate private repository and environment**. Keep the phone capture interface and cross-device accounting review behind authentication; design asynchronous OCR, draft persistence, per-business decisions, export, retention and audit logs separately. Cloudflare Workers/D1, Google Drive, Yayoi, external AI, public routes and actual receipt ingestion require their own approvals and security reviews.

No GitHub Pages setting or published HTML is changed by this runbook.
