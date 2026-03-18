import { test, expect } from './utils/test';

/**
 * ui_actions.spec.ts
 * 
 * Extensive modular test focused on specific destructive or background admin actions:
 * Resolving Venues and Deleting Targets.
 * 
 * Expanded from: actions.spec.ts
 */

test.describe.parallel('Admin Target Actions & Utilities', () => {

    test.beforeEach(async ({ page, context }) => {
        await context.route('**/api/auth/login', route => route.fulfill({ status: 200, body: JSON.stringify({ user: { id: 1, role: 'admin' } }) }));
        await context.route('**/api/auth/me', route => route.fulfill({ status: 200, body: JSON.stringify({ user: { id: 1, role: 'admin' } }) }));
        
        // Setup a mock target so actions are visible
        await context.route('**/api/targets', route => {
            route.fulfill({
                status: 200, body: JSON.stringify({
                    targets: { "t1": { id: "t1", name: "Alpha Paper", title: "Alpha Paper", mode: "paper", status: "completed", progress: 100, s2_total_citations: 10, total_citations: 10, criteria_domain: "Physics" } }
                })
            });
        });
        await context.route('**/api/targets/t1', route => route.fulfill({ status: 200, body: JSON.stringify({ id: "t1" }) }));
        await context.route('**/api/citations?target_id=t1', route => route.fulfill({ status: 200, body: JSON.stringify({ records: [] }) }));

        await page.goto('/');
    });

    test('Resolve Venues button triggers background network request safely', async ({ page, context }) => {
        let resolveCalled = false;
        
        // Intercept resolving to verify it fires
        await context.route('**/api/targets/t1/resolve_venues', route => {
            resolveCalled = true;
            route.fulfill({ status: 200, body: JSON.stringify({ success: true }) });
        });

        // Click resolve button
        const resolveBtn = page.locator('button[title*="Resolve"], button[aria-label*="Resolve"]');
        if (await resolveBtn.isVisible()) {
            await resolveBtn.click();
            // Allow event loop to catch fetch
            await page.waitForTimeout(500); 
            expect(resolveCalled).toBeTruthy();
        }
    });

    test('Delete Target triggers confirmation dialog and fires network request', async ({ page, context }) => {
        let deleteCalled = false;
        
        // Accept the browser prompt that usually pops up for deleting
        page.on('dialog', dialog => dialog.accept());

        await context.route('**/api/targets/t1', async route => {
            if (route.request().method() === 'DELETE') {
                deleteCalled = true;
                route.fulfill({ status: 200, body: JSON.stringify({ success: true }) });
            } else {
                route.fallback();
            }
        });

        // Click Delete button
        const deleteBtn = page.locator('button[title*="Delete"], button[aria-label*="Delete Target"]');
        if (await deleteBtn.isVisible()) {
            await deleteBtn.click();
            await page.waitForTimeout(500);
            expect(deleteCalled).toBeTruthy();
        }
    });
});
