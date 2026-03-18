import { test, expect } from './utils/test';

test.describe('Registration Flow', () => {
    test('renders registration form and successfully submits', async ({ page }) => {
        // Intercept API call
        await page.route('**/api/auth/register', route => route.fulfill({ 
            status: 200, 
            body: JSON.stringify({ user: { id: 2, username: 'new_user', role: 'viewer', groups: [] } }) 
        }));
        
        await page.goto('/register');
        await expect(page.locator('h1')).toHaveText(/Create an Account/i);
        
        await page.fill('input[placeholder="johndoe"]', 'new_user');
        await page.locator('input[placeholder="••••••••"]').first().fill('securepassword');
        await page.locator('input[placeholder="••••••••"]').nth(1).fill('securepassword');
        await page.click('button[type="submit"]');

        // Check if redirect to dashboard happened
        await expect(page).toHaveURL('/');
    });

    test('shows error on failed registration', async ({ page }) => {
        await page.route('**/api/auth/register', route => route.fulfill({ status: 400, body: JSON.stringify({ error: "Username already exists" }) }));
        await page.goto('/register');
        
        await page.fill('input[placeholder="johndoe"]', 'existing_user');
        await page.locator('input[placeholder="••••••••"]').first().fill('securepassword');
        await page.locator('input[placeholder="••••••••"]').nth(1).fill('securepassword');
        await page.click('button[type="submit"]');

        await expect(page.locator('text=Username already exists')).toBeVisible();
    });
});
