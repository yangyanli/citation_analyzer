import { test, expect } from './utils/test';

/**
 * ui_error_states.spec.ts
 * 
 * Extensive modular test focused on ensuring components safely catch and render
 * standard HTTP error states without crashing.
 * 
 * Replaces: extensive_error_handling.spec.ts
 */

test.describe.parallel('Error State Banner Modularity', () => {

    test.beforeEach(async ({ page, context }) => {
        await context.route('**/api/auth/me', route => route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ user: { id: 1, username: 'admin', role: 'admin', groups: [{ id: 999, name: 'Mock Group' }] } })
        }));

        await page.goto('/login');
        await page.fill('input[type="text"]', 'admin');
        await page.fill('input[type="password"]', 'admin');
        await page.click('button[type="submit"]');
        await expect(page).toHaveURL('/');
        await expect(page.locator('[data-testid="add-analysis-btn"]').first()).toBeVisible();
    });

    test('Modal catches and renders 500 Internal Server error during Criteria generation', async ({ page, context }) => {
        await context.route('**/api/criteria', route => route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ error: 'Internal Server Error simulated' }) }));

        await page.locator('[data-testid="add-analysis-btn"]').first().click();
        await expect(page.locator('.fixed select').nth(1)).toHaveValue('999');
        await page.click('button:has-text("Publication")');
        await page.fill('input[placeholder="e.g., Attention Is All You Need"]', '500 Sim Paper');
        await page.click('button:has-text("Generate AI Criteria")');

        const errorToast = page.locator('text=Internal Server Error simulated');
        await expect(errorToast).toBeVisible();
    });

    test('Modal catches and renders 429 Rate Limit error gracefully', async ({ page, context }) => {
        await context.route('**/api/criteria', route => route.fulfill({ status: 429, contentType: 'application/json', body: JSON.stringify({ error: 'Rate limit exceeded. Try again.' }) }));

        await page.locator('[data-testid="add-analysis-btn"]').first().click();
        await expect(page.locator('.fixed select').nth(1)).toHaveValue('999');
        await page.click('button:has-text("Publication")');
        await page.fill('input[placeholder="e.g., Attention Is All You Need"]', '429 Sim Paper');
        await page.click('button:has-text("Generate AI Criteria")');

        const errorToast = page.locator('text=Rate limit exceeded');
        await expect(errorToast).toBeVisible();
    });

    test('Modal catches and renders 404 Profile Not Found gracefully', async ({ page, context }) => {
        await context.route('**/api/criteria', route => route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ error: 'Scholar profile not found.' }) }));

        await page.locator('[data-testid="add-analysis-btn"]').first().click();
        await expect(page.locator('.fixed select').nth(1)).toHaveValue('999');
        await page.click('button:has-text("Researcher")');
        await page.fill('input[placeholder*="9RxI7UAAAAAJ"]', 'fake_scholar_123');
        await page.click('button:has-text("Generate AI Criteria")');

        const errorToast = page.locator('text=Scholar profile not found');
        await expect(errorToast).toBeVisible();
    });

    test('Dashboard safely handles network failure string during target polling', async ({ page, context }) => {
        // Mock a failure while the dashboard actively tries to fetch targets
        await context.route('**/api/targets', route => route.abort('failed'));
        
        await page.reload();
        
        // Since we abort network, the UI shouldn't crash, it should just display a generic warning or empty state.
        // Most apps fallback to displaying nothing or a standard fetch error.
        try {
            await expect(page.locator('text=Error fetching targets').or(page.locator('text=Failed to fetch'))).toBeVisible({ timeout: 2000 });
        } catch {
             // Or at least it renders an empty state instead of a blank white screen crash
            await expect(page.locator('button:has-text("New Analysis"), [data-testid="add-analysis-btn"]').first()).toBeVisible();
        }
    });
});
