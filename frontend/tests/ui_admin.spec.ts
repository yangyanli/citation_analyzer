import { test, expect } from './utils/test';

test.describe('Admin LLM Logs', () => {
    test.beforeEach(async ({ page }) => {
        await page.route('**/api/auth/me', route => route.fulfill({
            status: 200, body: JSON.stringify({ user: { id: 1, username: 'admin', role: 'admin' } })
        }));
        // We log in
        await page.goto('/login');
        await page.fill('input[type="text"]', 'admin');
        await page.fill('input[type="password"]', 'admin');
        await page.click('button[type="submit"]');
        await expect(page).toHaveURL('/');
    });

    test('views llm logs page with data', async ({ page }) => {
        await page.route('**/api/admin/llm-logs*', route => route.fulfill({
            status: 200,
            body: JSON.stringify({ logs: [{ id: 1, prompt_text: 'Hello', response_text: 'Hi', tokens: 10, timestamp: new Date().toISOString() }], total: 1 })
        }));
        
        await page.goto('/admin/llm-logs');
        await expect(page.locator('h1')).toHaveText(/LLM Request Logs/i);
        await expect(page.locator('text=Input Text Preview')).toBeVisible();
    });
});

test.describe('Admin Groups', () => {
    test.beforeEach(async ({ page }) => {
        await page.route('**/api/auth/me', route => route.fulfill({
            status: 200, body: JSON.stringify({ user: { id: 1, username: 'admin', role: 'admin' } })
        }));
        // We log in
        await page.goto('/login');
        await page.fill('input[type="text"]', 'admin');
        await page.fill('input[type="password"]', 'admin');
        await page.click('button[type="submit"]');
        await expect(page).toHaveURL('/');
    });

    test('views and adds groups', async ({ page }) => {
        await page.route('**/api/groups', route => {
            if (route.request().method() === 'GET') {
                return route.fulfill({ status: 200, body: JSON.stringify([{ id: 1, name: 'Default' }]) });
            } else if (route.request().method() === 'POST') {
                return route.fulfill({ status: 200, body: JSON.stringify({ message: "Success" }) });
            }
        });
        
        await page.goto('/admin/groups');
        await expect(page.locator('h1')).toHaveText(/Group Management/i);

        // Add
        await page.fill('input[placeholder="e.g. Stanford AI Lab"]', 'New Group');
        await page.click('button:has-text("Create")');
    });

    test('deletes empty group but not populated group', async ({ page }) => {
        await page.route('**/api/admin/groups', route => {
            return route.fulfill({
                status: 200, body: JSON.stringify({
                    groups: [
                        { id: 1, name: 'Populated', is_public: 1, members: [{ id: 1, username: 'admin', role: 'admin' }] },
                        { id: 2, name: 'Empty', is_public: 0, members: [] }
                    ]
                })
            });
        });

        // Mock the DELETE endpoint
        await page.route('**/api/admin/groups/2', route => {
            return route.fulfill({ status: 200, body: JSON.stringify({ success: true }) });
        });

        // Handle confirm dialog
        page.on('dialog', dialog => dialog.accept());

        await page.goto('/admin/groups');
        
        // Populated group should NOT have a delete button
        const populatedRow = page.locator('tr').filter({ hasText: 'Populated' });
        await expect(populatedRow.locator('button:has-text("Delete")')).toHaveCount(0);

        // Empty group SHOULD have a delete button
        const emptyRow = page.locator('tr').filter({ hasText: 'Empty' });
        await expect(emptyRow.locator('button:has-text("Delete")')).toHaveCount(1);
        
        // Click delete on the empty group
        await emptyRow.locator('button:has-text("Delete")').click();
        
        // The empty row should disappear from UI
        await expect(emptyRow).toHaveCount(0);
        await expect(populatedRow).toBeVisible();
    });
});

test.describe('Admin Users', () => {
    test.beforeEach(async ({ page }) => {
        await page.route('**/api/auth/me', route => route.fulfill({
            status: 200, body: JSON.stringify({ user: { id: 1, username: 'admin', role: 'admin' } })
        }));
        // We log in
        await page.goto('/login');
        await page.fill('input[type="text"]', 'admin');
        await page.fill('input[type="password"]', 'admin');
        await page.click('button[type="submit"]');
        await expect(page).toHaveURL('/');
    });

    test('views and changes roles', async ({ page }) => {
        await page.route('**/api/admin/groups', route => route.fulfill({
            status: 200, body: JSON.stringify({ groups: [{ id: 1, name: 'Default', is_public: 1, members: [] }] })
        }));
        await page.route('**/api/admin/users', async route => {
            if (route.request().method() === 'PUT') {
                await route.fulfill({ status: 200, body: JSON.stringify({ message: "Success" }) });
            } else {
                await route.fulfill({ status: 200, body: JSON.stringify({ users: [{ id: 999, username: 'testuser', role: 'viewer', created_at: '2026-03-09' }] }) });
            }
        });
        
        await page.goto('/admin/users');
        await expect(page.locator('h1')).toHaveText(/User Management/i);

        // Interact with selects
        await page.selectOption('select', 'admin');
    });
});
