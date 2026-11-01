import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';
import test from 'node:test';

const html = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const readme = readFileSync(new URL('../README.md', import.meta.url), 'utf8');

test('public preview has no executable backend or credential files', () => {
  const files = readdirSync(new URL('..', import.meta.url)).filter(name => !name.startsWith('.'));
  assert.ok(files.includes('index.html'));
  assert.ok(files.includes('README.md'));
  assert.ok(!files.some(name => /^(wrangler\.toml|\.env|package\.json|server\.[cm]?js)$/i.test(name)));
});

test('public preview explicitly warns against entering real data', () => {
  assert.match(readme, /Do \*\*not\*\* enter real receipts/);
  assert.match(readme, /devices do \*\*not\*\* synchronize/);
  assert.match(readme, /not a production accounting or archival service/);
  assert.match(html, /試用デモ/);
});

test('demo data stays browser-local and no network transport is wired', () => {
  assert.match(html, /localStorage\.getItem\(KEY\)/);
  assert.match(html, /localStorage\.setItem\(KEY,/);
  assert.doesNotMatch(html, /\bfetch\s*\(|\bXMLHttpRequest\b|\bnavigator\.sendBeacon\b|\bWebSocket\s*\(/);
  assert.doesNotMatch(html, /<script[^>]+src\s*=|<iframe[^>]+src\s*=/i);
});

test('demo uses sample-only receipt capture, not actual OCR or image upload', () => {
  assert.match(html, /id=['"]simulate['"]/);
  assert.match(html, /サンプル店舗/);
  assert.doesNotMatch(html, /<input[^>]+type=['"]file['"]/i);
});
