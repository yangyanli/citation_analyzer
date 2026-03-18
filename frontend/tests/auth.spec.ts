import { test, expect } from './utils/test';

test.describe.parallel('Authentication Flow', () => {
    test('should login as admin and view dashboard', async ({ page }) => {
        // Go to login page
        await page.goto('/login');

        // Fill the login form
        await page.fill('input[type="text"]', 'admin');
        await page.fill('input[type="password"]', 'admin');
        await page.click('button[type="submit"]');

        // Should redirect to dashboard and show admin UI elements
        await expect(page).toHaveURL('/', { timeout: 10000 });

        // Check if the username is displayed
        await expect(page.locator('text=admin').first()).toBeVisible();

        // Check if the "New Analysis" button exists (Admin only)
        await expect(page.locator('button:has-text("New Analysis"), button[title="Add New Analysis"]')).toBeVisible();
    });

    test('should login as regular user and have restricted dashboard', async ({ page }) => {
        await page.goto('/login');

        await page.fill('input[type="text"]', 'user');
        await page.fill('input[type="password"]', 'user123');
        await page.click('button[type="submit"]');

        await expect(page).toHaveURL('/', { timeout: 10000 });

        // Check username
        await expect(page.locator('text=user').first()).toBeVisible();

        // Regular users shouldn't see the "New Analysis" button
        await expect(page.locator('button:has-text("New Analysis"), button[title="Add New Analysis"]')).not.toBeVisible();
    });

    test('should logout successfully', async ({ page }) => {
        // Login first
        await page.goto('/login');
        await page.fill('input[type="text"]', 'admin');
        await page.fill('input[type="password"]', 'admin');
        await page.click('button[type="submit"]');

        // Wait for dashboard
        await expect(page).toHaveURL('/', { timeout: 10000 });

        // Click logout button (title "Sign out")
        await page.click('button[title="Sign out"]');

        // Should be redirected to login
        await expect(page).toHaveURL('/login', { timeout: 10000 });
    });
});
