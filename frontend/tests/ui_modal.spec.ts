import { test, expect } from './utils/test';

/**
 * ui_modal.spec.ts
 * 
 * Extensive modular tests for the Analysis Modal. Exercises all form elements,
 * toggles, limits, and validation states without kicking off a real LLM run.
 * 
 * Replaces: new_analysis.spec.ts and pieces of modular_analysis_flow.spec.ts
 */

test.describe.parallel('Analysis Form Modal Exhaustive Checks', () => {

    test.beforeEach(async ({ page, context }) => {
        await context.route('**/api/auth/login', route => route.fulfill({
            status: 200, contentType: 'application/json',
            body: JSON.stringify({ user: { id: 1, username: 'admin', role: 'admin', groups: [{ id: 999, name: 'Mock Group' }] } })
        }));
        await context.route('**/api/auth/me', route => route.fulfill({
            status: 200, contentType: 'application/json',
            body: JSON.stringify({ user: { id: 1, username: 'admin', role: 'admin', groups: [{ id: 999, name: 'Mock Group' }] } })
        }));
        await context.route('**/api/targets', route => route.fulfill({
            status: 200, contentType: 'application/json',
            body: JSON.stringify({ targets: { "t1": { id: "t1", name: "Mock Paper", mode: "paper", status: "completed", progress: 100 } } })
        }));
        await context.route('**/api/citations*', route => route.fulfill({
            status: 200, contentType: 'application/json', body: JSON.stringify({ records: [] })
        }));

        // Block polling so UI stays stable during assertions
        await page.addInitScript(() => {
            (window as unknown as Record<string, unknown>).setInterval = (cb: TimerHandler, ms: number | undefined) => window.setTimeout(cb, ms === 5000 ? 9999999 : ms);
        });

        await page.goto('/login');
        await page.fill('input[type="text"]', 'admin');
        await page.fill('input[type="password"]', 'admin');
        await page.click('button[type="submit"]');
        await expect(page).toHaveURL('/', { timeout: 10000 });
        await expect(page.locator('[data-testid="add-analysis-btn"]').first()).toBeVisible({ timeout: 10000 });
        
        // Open Modal explicitly
        await page.locator('[data-testid="add-analysis-btn"]').first().click();
        await expect(page.locator('.fixed select').nth(1)).toHaveValue('999', { timeout: 10000 });
        await expect(page.locator('h2:has-text("New Analysis")')).toBeVisible();
    });

    test('Mode Toggle: Swaps between Publication and Researcher forms appropriately', async ({ page }) => {
        // Default is usually Researcher. Check for scholar placeholder
        const resInput = page.locator('input[placeholder*="9RxI7UAAAAAJ"]');
        await expect(resInput).toBeVisible();

        // Switch to Publication
        await page.click('button:has-text("Publication")');
        const pubInput = page.locator('input[placeholder*="Attention Is All You Need"]');
        await expect(pubInput).toBeVisible();
        await expect(resInput).toBeHidden();

        // Switch back
        await page.click('button:has-text("Researcher")');
        await expect(resInput).toBeVisible();
        await expect(pubInput).toBeHidden();
    });

    test('Advanced Settings: Expanding and updating limits works correctly', async ({ page }) => {
        // Modal is in a fixed overlay. Pick the first select within the modal
        const selectLimit = page.locator('.fixed select').first();
        await selectLimit.selectOption('50');
        expect(await selectLimit.inputValue()).toBe('50');

        await selectLimit.selectOption('500');
        expect(await selectLimit.inputValue()).toBe('500');
    });

    test('Modal progresses from Step 1 (Criteria) to Step 2 (Review) via Mock', async ({ page, context }) => {
        // Mock Criteria API to succeed instantly
        await context.route('**/api/criteria', route => {
            route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    success: true,
                    criteria: { domain: "Test", notable_criteria: "Test Notable", seminal_criteria: "Test Seminal" }
                })
            });
        });

        await page.click('button:has-text("Publication")');
        await page.fill('input[placeholder*="Attention Is All You Need"]', 'A Valid Spec Title');
        await page.click('button:has-text("Generate AI Criteria")');

        // It should progress to step 2 review
        await expect(page.locator('h2:has-text("Review Criteria")')).toBeVisible();
        
        // The mock values should be placed into the textareas
        await expect(page.locator('textarea').first()).toHaveValue(/Test/);
    });

    test('Modal progresses from Step 2 to closure upon submitting Analysis via Mock', async ({ page, context }) => {
        // Fast-track hit Step 2
        await context.route('**/api/criteria', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true, criteria: { domain: "T", notable_criteria: "T", seminal_criteria: "T" } }) }));
        await context.route('**/api/analyze', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true, targetId: 999 }) }));
        
        await page.click('button:has-text("Publication")');
        await page.fill('input[placeholder*="Attention Is All You Need"]', 'A Valid Spec Title');
        await page.click('button:has-text("Generate AI Criteria")');
        await expect(page.locator('h2:has-text("Review Criteria")')).toBeVisible();

        // Submit Analysis
        await page.click('button:has-text("Start Semantic Analysis")');
        
        // Modal should hide or overlay loading
        await expect(page.locator('h2:has-text("Review Criteria")')).toBeHidden();
    });
});
