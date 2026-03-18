import { test, expect } from './utils/test';

/**
 * ui_dashboard.spec.ts
 * 
 * Extensive modular test for the main Dashboard view.
 * This directly checks the frontend's ability to render various states of target 
 * and citation data without invoking the actual python backend or LLM API.
 * 
 * Replaces: extensive_interaction.spec.ts, modular_analysis_flow.spec.ts
 */

test.describe.parallel('Dashboard Extensive UI Tests', () => {

    test.beforeEach(async ({ page, context }) => {
        // Mock Auth check to bypass login routing
        await context.route('**/api/auth/login', route => {
            route.fulfill({
                status: 200, contentType: 'application/json',
                body: JSON.stringify({ user: { id: 1, username: 'admin', role: 'admin', groups: [{ id: 1, name: 'Admin Group' }] } })
            });
        });
        await context.route('**/api/auth/me', route => {
            route.fulfill({
                status: 200, contentType: 'application/json',
                body: JSON.stringify({ user: { id: 1, username: 'admin', role: 'admin', groups: [{ id: 1, name: 'Admin Group' }] } })
            });
        });

        // Block polling so UI stays stable during assertions
        await page.addInitScript(() => {
            (window as unknown as Record<string, unknown>).setInterval = (cb: TimerHandler, ms: number | undefined) => window.setTimeout(cb, ms === 5000 ? 9999999 : ms);
        });
    });

    test('Dashboard renders empty state correctly when no targets exist', async ({ page, context }) => {
        await context.route('**/api/targets', route => {
            route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ targets: {} }) });
        });

        await page.goto('/');
        
        await expect(page.locator('button:has-text("New Analysis"), [data-testid="add-analysis-btn"]').first()).toBeVisible();
    });

    test('Dashboard renders populated state and handles complex target interactions', async ({ page, context }) => {
        // Mock 2 targets: one completed paper, one processing researcher
        await context.route('**/api/targets', route => {
            route.fulfill({
                status: 200, contentType: 'application/json', body: JSON.stringify({
                    targets: {
                        "t1": { id: "t1", name: "Alpha Paper", title: "Alpha Paper", mode: "paper", status: "completed", progress: 100, s2_total_citations: 10, total_citations: 10, criteria_domain: "Physics" },
                        "t2": { id: "t2", name: "Dr. Beta", title: "Dr. Beta", mode: "scholar", status: "processing", progress: 45, s2_total_citations: 0, total_citations: 0, criteria_domain: "" }
                    }
                })
            });
        });

        // Mock citation data for target "t1"
        await context.route('**/api/citations*', route => {
            if (route.request().url().includes('target_id=t1')) {
                route.fulfill({
                    status: 200, contentType: 'application/json', body: JSON.stringify({
                        records: [
                            { citation_id: "c1", citing_title: "Beta study", cited_title: "Alpha Paper", notable_authors: [{name: "Smith"}], is_seminal: true, year: 2024, url: "http://example.com/c1", s2_citation_count: 50, sentiment_evidence: "This relies on Alpha", positive_comment: "Great work", usage_classification: "Extending / Using", contexts: ["This relies on Alpha \\( x^2 \\)"], score: 9 },
                            { citation_id: "c2", citing_title: "Gamma review", cited_title: "Alpha Paper", notable_authors: [], is_seminal: false, year: 2023, url: "http://example.com/c2", s2_citation_count: 5, sentiment_evidence: "Mentioned briefly.", usage_classification: "Background", contexts: ["Mentioned briefly."], score: 3 }
                        ]
                    })
                });
            } else {
                route.fallback();
            }
        });

        await context.route('**/api/targets/t1', route => {
            route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ id: "t1" }) });
        });

        await page.goto('/');

        // Validate default active target rendering (t2)
        await expect(page.locator('text=45%')).toBeVisible(); // Check progress bar text render
        const optionBeta = page.locator('option[value="t2"]');
        await expect(optionBeta).toBeAttached();

        // Select 'Alpha Paper' from the select dropdown explicitly
        await page.locator('select').filter({ hasText: 'Alpha Paper' }).selectOption('t1');
        
        // Validate Target list rendering
        await expect(page.locator('span[title="Alpha Paper"], span:has-text("Alpha Paper")').first()).toBeVisible();

        // Wait for citations to fully render and DOM to stabilize after target switch
        await expect(page.locator('span:has-text("Extending / Using")').first()).toBeVisible({ timeout: 10000 });

        // 3. Validate Context hover expansion
        const quoteGroup = page.locator('text="Evidence Quote"').first();
        await quoteGroup.waitFor({ state: 'visible', timeout: 10000 });
        await quoteGroup.hover();
        await expect(page.locator('text=This relies on Alpha').first()).toBeVisible();

        // 4. Validate citation cards show usage classification styles
        const extendingBadge = page.locator('span:has-text("Extending / Using")').first();
        await expect(extendingBadge).toBeVisible();
        
        const backgroundBadge = page.locator('span:has-text("Background")').first();
        await expect(backgroundBadge).toBeVisible();

        // 5. Test Tab Switching
        const authorsTab = page.locator('button[aria-label="Authors Tab"]');
        if (await authorsTab.isVisible()) {
            await authorsTab.click();
            await expect(page.locator('text=Smith')).toBeVisible();
        }
    });

    test('Dashboard renders phase estimates correctly for processing targets', async ({ page, context }) => {
        // Mock 1 processing target with estimates
        await context.route('**/api/targets', route => {
            route.fulfill({
                status: 200, contentType: 'application/json', body: JSON.stringify({
                    targets: {
                        "t1": {
                            id: "t1", name: "Est Paper", title: "Est Paper", mode: "paper", status: "processing", progress: 50, s2_total_citations: 0, total_citations: 0,
                            p2_est_batches: 5, p2_est_cost: 0.1234,
                            p3_est_batches: 2, p3_est_cost: 0.0567,
                            p4_est_batches: 10, p4_est_cost: 0.9876
                        }
                    }
                })
            });
        });

        await context.route('**/api/citations*', route => {
            route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ records: [] }) });
        });

        await page.goto('/');

        // Verify the estimates are visible
        await expect(page.locator('text=Phase 2 (Authors): 5 batches')).toBeVisible();
        await expect(page.locator('text=est. $0.1234')).toBeVisible();
        
        await expect(page.locator('text=Phase 3 (Seminal): 2 batches')).toBeVisible();
        await expect(page.locator('text=est. $0.0567')).toBeVisible();

        await expect(page.locator('text=Phase 4 (Sentiment): 10 batches')).toBeVisible();
        await expect(page.locator('text=est. $0.9876')).toBeVisible();
    });

    test('Dashboard citation table pagination handles boundaries correctly', async ({ page, context }) => {
        // Generate 55 mock citations to force pagination (default 10 items per page limit in UI)
        const mockCitations = Array.from({length: 55}, (_, i) => ({
            citation_id: `c${i}`, citing_title: `Paper ${i}`, cited_title: "Paginated", notable_authors: [], is_seminal: false, year: 2023, url: "#", s2_citation_count: i, contexts: ["text"], sentiment_label: "neutral", score: 1
        }));

        await context.route('**/api/targets', route => {
            route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ targets: { "p1": { id: "p1", name: "Paginated", mode: "paper", status: "completed", progress: 100 } } }) });
        });
        await context.route('**/api/targets/p1', route => {
            route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ id: "p1" }) });
        });
        await context.route('**/api/citations*', route => {
            if (route.request().url().includes('target_id=p1')) {
                route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ records: mockCitations }) });
            } else {
                route.fallback();
            }
        });

        await page.goto('/');

        // Dashboard auto-selects the first available target ('p1')

        // Validate Page 1 (default 10 per page)
        await expect(page.locator('span').filter({ hasText: 'Showing 1 to 10 of 55 results' })).toBeVisible();
        const nextButton = page.locator('button:has-text("Next")').first();
        
        // Go Page 2
        await nextButton.click();
        await expect(page.locator('span').filter({ hasText: 'Showing 11 to 20 of 55 results' })).toBeVisible();

        // Next button should NOT be disabled (there are still pages remaining)
        await expect(nextButton).toBeEnabled();
    });
});
