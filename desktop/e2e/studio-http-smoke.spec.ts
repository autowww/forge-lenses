/**
 * Contract smoke against a running Lenses server (Studio + JSON API).
 *
 * Start: `python3 -m lenses` (default http://127.0.0.1:8080), then:
 *   LENSES_E2E=1 npx playwright test studio-http-smoke.spec.ts
 */
import { test, expect } from "@playwright/test";

const base = (process.env.LENSES_E2E_BASE || "http://127.0.0.1:8080").replace(/\/$/, "");

const run = process.env.LENSES_E2E === "1";
const d = run ? test.describe : test.describe.skip;

d("Lenses HTTP smoke (Sprint 10)", () => {
  test("Studio shell responds", async ({ request }) => {
    const res = await request.get(`${base}/studio/`);
    expect(res.ok()).toBeTruthy();
    const ct = res.headers()["content-type"] || "";
    expect(ct).toContain("text/html");
  });

  test("Connector health JSON shape", async ({ request }) => {
    const res = await request.get(`${base}/api/connectors/health`);
    expect(res.ok()).toBeTruthy();
    const j = (await res.json()) as Record<string, unknown>;
    expect(j.ok).toBe(true);
    expect(Array.isArray(j.connectors)).toBe(true);
    expect(j.summary).toBeTruthy();
  });

  test("Governance scopes JSON", async ({ request }) => {
    const res = await request.get(`${base}/api/governance/scopes`);
    expect(res.ok()).toBeTruthy();
    const j = (await res.json()) as Record<string, unknown>;
    expect(j.ok).toBe(true);
    expect(Array.isArray(j.scopes)).toBe(true);
  });

  test("OIDC status JSON", async ({ request }) => {
    const res = await request.get(`${base}/api/auth/oidc/status`);
    expect(res.ok()).toBeTruthy();
    const j = (await res.json()) as Record<string, unknown>;
    expect(j.ok).toBe(true);
    expect(typeof j.configured).toBe("boolean");
  });

  test("Auth status includes governance fields", async ({ request }) => {
    const res = await request.get(`${base}/api/auth/status`);
    expect(res.ok()).toBeTruthy();
    const j = (await res.json()) as Record<string, unknown>;
    expect("auth_provider" in j).toBe(true);
    expect("oidc_configured" in j).toBe(true);
  });

  test("Sticker board registry GET (regression: json UnboundLocalError)", async ({ request }) => {
    const res = await request.get(`${base}/api/sticker-board-registry`);
    expect(res.ok()).toBeTruthy();
    const j = (await res.json()) as Record<string, unknown>;
    expect(j.version).toBe(1);
    expect(typeof j.projects).toBe("object");
  });
});
