#!/usr/bin/env node
/**
 * Add Stickerboard OAuth redirect URIs to the forge-lenses Web client in GCP Console.
 * Uses a persistent Chrome profile when available (must be logged into Google Cloud).
 *
 *   node scripts/gcp-add-stickerboard-redirects.mjs
 */
import { chromium } from 'playwright';
import path from 'node:path';
import os from 'node:os';

const PROJECT = process.env.LENSES_OIDC_GCP_PROJECT || 'forge-lenses';
const CLIENT_ID =
  process.env.LENSES_OIDC_CLIENT_ID ||
  '886172952932-l4bgb977h450qsfqke5gj2o4cbepclb7.apps.googleusercontent.com';

const REDIRECTS = [
  'http://127.0.0.1:8080/stickerboard/api/auth/oidc/callback',
  'http://127.0.0.1:9999/api/auth/oidc/callback',
  'https://leo.forgedc.net/stickerboard/api/auth/oidc/callback',
];

const url = `https://console.cloud.google.com/auth/clients/${encodeURIComponent(CLIENT_ID)}?project=${PROJECT}`;

const chromeDefault = path.join(os.homedir(), '.config', 'google-chrome');
const userDataDir = process.env.PLAYWRIGHT_CHROME_PROFILE || chromeDefault;

const context = await chromium.launchPersistentContext(userDataDir, {
  channel: 'chrome',
  headless: false,
  viewport: { width: 1280, height: 900 },
});

const page = context.pages()[0] || (await context.newPage());
await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 120_000 });

console.log('Opened:', page.url());
console.log('If you see the client editor, add these Authorized redirect URIs:');
for (const r of REDIRECTS) console.log('  -', r);
console.log('Waiting 90s for manual save (or automate when logged in)…');
await page.waitForTimeout(90_000);
await context.close();
