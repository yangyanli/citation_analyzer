import { test, expect } from './utils/test';

test.describe('Settings Page', () => {
    test.beforeEach(async ({ page, context }) => {
        await context.route('**/api/auth/login', route => route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ user: { id: 1, username: 'admin', role: 'admin' } })
        }));
        await context.route('**/api/auth/me', route => route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ user: { id: 1, username: 'admin', role: 'admin' } })
        }));

        // We log in
        await page.goto('/login');
        await page.fill('input[type="text"]', 'admin');
        await page.fill('input[type="password"]', 'admin');
        await page.click('button[type="submit"]');
        await expect(page).toHaveURL('/');
    });

    test('views and updates passwords', async ({ page }) => {
        await page.route('**/api/auth/users', async route => {
            if (route.request().method() === 'PUT') {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({ message: 'Password updated successfully' })
                });
            } else {
                await route.continue();
            }
        });

        await page.goto('/settings');
        await expect(page.locator('h1')).toHaveText(/Account Settings/i);

        // Update password
        await page.locator('input[type="password"]').nth(0).fill('newadminpass');
        await page.locator('input[type="password"]').nth(1).fill('newadminpass');
        await page.click('button:has-text("Update Password")');

        await expect(page.getByText('Password updated successfully.')).toBeVisible({ timeout: 5000 });
    });

    test('password mismatch error', async ({ page }) => {
        await page.goto('/settings');
        await page.locator('input[type="password"]').nth(0).fill('newadminpass');
        await page.locator('input[type="password"]').nth(1).fill('wrongpass');
        await page.click('button:has-text("Update Password")');

        await expect(page.getByText('Passwords do not match.')).toBeVisible();
    });
});
