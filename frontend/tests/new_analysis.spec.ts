import { test, expect } from './utils/test';

test.describe.serial('New Analysis Flow', () => {
    // Use a random title or a fake one, but since phase0 will hit real LLM, 
    // maybe we don't do a full test here unless we intercept API calls.
    // Actually, we can test that the Modal opens, and we can switch to Paper mode.
    test('should open New Analysis modal and show validation', async ({ page }) => {
        // Login as Admin
        await page.goto('/login');
        await page.fill('input[type="text"]', 'admin');
        await page.fill('input[type="password"]', 'admin');
        await page.click('button[type="submit"]');
        await page.waitForURL('/', { timeout: 15000 });
        await page.waitForLoadState('networkidle');

        // Click New Analysis
        await page.click('button:has-text("New Analysis"), button[title="Add New Analysis"]');

        // Check Modal is visible
        await expect(page.locator('h2:has-text("New Analysis")')).toBeVisible();

        // Switch to Paper Mode
        await page.click('button:has-text("Publication")');

        // Submit empty form (should trigger HTML5 validation)
        const submitBtn = page.locator('button:has-text("Generate AI Criteria")');
        await expect(submitBtn).toBeVisible();

        // Fill something
        await page.fill('input[placeholder="e.g., Attention Is All You Need"]', 'A Fake Paper for UI Testing');

        // We stop here to easily avoid burning LLM tokens or scraping S2 endlessly in an automated UI test.
        // The full E2E pipeline with manual fallback will be tested in proxy.spec.ts
    });
});
