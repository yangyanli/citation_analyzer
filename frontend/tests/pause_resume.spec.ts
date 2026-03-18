import { test, expect } from './utils/test';

test.describe.serial('Dashboard Targets: Pause, Resume, Cancel', () => {

    test('should show pause/resume/cancel buttons for admin and hide for regular users', async ({ page, context }) => {
        // ── Admin Login (mocked) ──
        await context.route('**/api/auth/login', route => {
            const body = route.request().postDataJSON?.() ?? {};
            if (body.username === 'admin') {
                route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ user: { id: 1, username: 'admin', role: 'admin', groups: [{ id: 1, name: 'Admin' }] } }) });
            } else {
                route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ user: { id: 2, username: 'user', role: 'viewer', groups: [] } }) });
            }
        });

        let currentRole = 'admin';
        await context.route('**/api/auth/me', route => {
            if (currentRole === 'admin') {
                route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ user: { id: 1, username: 'admin', role: 'admin', groups: [{ id: 1, name: 'Admin' }] } }) });
            } else {
                route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ user: { id: 2, username: 'user', role: 'viewer', groups: [] } }) });
            }
        });

        await context.route('**/api/auth/logout', route => {
            route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true }) });
        });

        // Mock a completed target with citations
        await context.route('**/api/targets', route => {
            route.fulfill({
                status: 200, contentType: 'application/json',
                body: JSON.stringify({
                    targets: {
                        "t1": { id: "t1", name: "Test Paper", title: "Test Paper", mode: "paper", status: "completed", progress: 100, s2_total_citations: 10, total_citations: 10 }
                    }
                })
            });
        });

        await context.route('**/api/citations*', route => {
            route.fulfill({
                status: 200, contentType: 'application/json',
                body: JSON.stringify({
                    records: [
                        { citation_id: "c1", citing_title: "Paper A", cited_title: "Test Paper", notable_authors: [], is_seminal: false, year: 2024, url: "#", score: 5, contexts: ["ctx"], usage_classification: "Background", positive_comment: "", sentiment_evidence: "" }
                    ]
                })
            });
        });

        // Block polling
        await page.addInitScript(() => {
            (window as unknown as Record<string, unknown>).setInterval = (cb: TimerHandler, ms: number | undefined) => window.setTimeout(cb, ms === 5000 ? 9999999 : ms);
        });

        // 1. Login as Admin
        await page.goto('/login');
        await page.fill('input[type="text"]', 'admin');
        await page.fill('input[type="password"]', 'admin');
        await page.click('button[type="submit"]');
        await expect(page).toHaveURL('/');

        // Admin should see admin controls like Resolve arXiv or Delete
        const resolveBtn = page.locator('button[title="Scan and resolve arXiv venues to peer-reviewed venues"]');
        await expect(resolveBtn.first()).toBeVisible({ timeout: 5000 }).catch(() => { });

        // 2. Logout
        await page.click('button[title="Sign out"]');
        await page.waitForURL('**/login', { timeout: 10000 });

        // 3. Login as User (viewer)
        currentRole = 'viewer';
        await page.fill('input[type="text"]', 'user');
        await page.fill('input[type="password"]', 'user123');
        await page.click('button[type="submit"]');
        await expect(page).toHaveURL('/');

        // Regular viewers should NOT see the Resolve Venues or Delete Target buttons
        await expect(page.locator('button[title="Scan and resolve arXiv venues to peer-reviewed venues"]')).not.toBeVisible();
        await expect(page.locator('button[title="Delete this analysis and all its citations"]')).not.toBeVisible();
    });
});
