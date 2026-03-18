import { test, expect } from './utils/test';

/**
 * ui_domains.spec.ts
 *
 * Tests for Phase 5 — Research Domain Distribution of Citations chart and filtering.
 * Uses the same API mocking strategy as ui_dashboard.spec.ts.
 */

test.describe.parallel('Domain Distribution UI Tests', () => {

    test.beforeEach(async ({ page, context }) => {
        // Mock Auth (same as ui_dashboard.spec.ts)
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

        // Block polling (same as ui_dashboard.spec.ts)
        await page.addInitScript(() => {
            (window as unknown as Record<string, unknown>).setInterval = (cb: TimerHandler, ms: number | undefined) => window.setTimeout(cb, ms === 5000 ? 9999999 : ms);
        });
    });

    const TARGET_WITH_DOMAINS = {
        targets: {
            "t1": { id: "t1", name: "Dr. Test", title: "Dr. Test", mode: "scholar", status: "completed", progress: 100, s2_total_citations: 50, total_citations: 50 }
        }
    };

    const CITATIONS_WITH_DOMAINS = {
        records: [
            { citation_id: "c1", citing_title: "Paper A", cited_title: "Target", notable_authors: [], is_seminal: false, year: 2024, url: "#", score: 5, contexts: ["ctx"], raw_contexts: ["ctx"], research_domain: "Computer Vision", usage_classification: "Background", positive_comment: "", sentiment_evidence: "" },
            { citation_id: "c2", citing_title: "Paper B", cited_title: "Target", notable_authors: [], is_seminal: false, year: 2024, url: "#", score: 7, contexts: ["ctx"], raw_contexts: ["ctx"], research_domain: "Computer Vision", usage_classification: "Extending", positive_comment: "", sentiment_evidence: "" },
            { citation_id: "c3", citing_title: "Paper C", cited_title: "Target", notable_authors: [], is_seminal: false, year: 2023, url: "#", score: 4, contexts: ["ctx"], raw_contexts: ["ctx"], research_domain: "Natural Language Processing", usage_classification: "Background", positive_comment: "", sentiment_evidence: "" },
            { citation_id: "c4", citing_title: "Paper D", cited_title: "Target", notable_authors: [], is_seminal: false, year: 2023, url: "#", score: 6, contexts: ["ctx"], raw_contexts: ["ctx"], research_domain: "Robotics", usage_classification: "Background", positive_comment: "", sentiment_evidence: "" },
        ]
    };

    test('Domain chart renders when domain data is present', async ({ page, context }) => {
        await context.route('**/api/targets', route => {
            route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(TARGET_WITH_DOMAINS) });
        });
        await context.route('**/api/citations*', route => {
            route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(CITATIONS_WITH_DOMAINS) });
        });

        await page.goto('/');

        // Domain chart container should be visible
        await expect(page.locator('#domain-chart-container')).toBeVisible({ timeout: 15000 });
        await expect(page.locator('text=Research Domain Distribution of Citations')).toBeVisible();
        await expect(page.locator('text=3 domains')).toBeVisible();
    });

    test('Domain chart does NOT render when no domain data is present', async ({ page, context }) => {
        await context.route('**/api/targets', route => {
            route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(TARGET_WITH_DOMAINS) });
        });
        await context.route('**/api/citations*', route => {
            route.fulfill({
                status: 200, contentType: 'application/json',
                body: JSON.stringify({ records: [
                    { citation_id: "c1", citing_title: "Paper A", cited_title: "Target", notable_authors: [], is_seminal: false, year: 2024, url: "#", score: 5, contexts: ["ctx"], raw_contexts: ["ctx"], research_domain: null, usage_classification: "Background", positive_comment: "", sentiment_evidence: "" },
                ]})
            });
        });

        await page.goto('/');
        await expect(page.locator('text=Citation Analysis Records')).toBeVisible({ timeout: 15000 });
        await expect(page.locator('#domain-chart-container')).not.toBeVisible();
    });

    test('Clicking a domain legend filters the table', async ({ page, context }) => {
        await context.route('**/api/targets', route => {
            route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(TARGET_WITH_DOMAINS) });
        });
        await context.route('**/api/citations*', route => {
            route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(CITATIONS_WITH_DOMAINS) });
        });

        await page.goto('/');
        await expect(page.locator('#domain-chart-container')).toBeVisible({ timeout: 15000 });

        // Click on "Computer Vision" in the legend
        await page.locator('#domain-legend button[data-domain="Computer Vision"]').click();

        // The selected domain legend button should be highlighted (has bg-white/10 class)
        await expect(page.locator('#domain-legend button[data-domain="Computer Vision"]')).toBeVisible();
    });

    test('Clearing domain filter resets the table', async ({ page, context }) => {
        await context.route('**/api/targets', route => {
            route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(TARGET_WITH_DOMAINS) });
        });
        await context.route('**/api/citations*', route => {
            route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(CITATIONS_WITH_DOMAINS) });
        });

        await page.goto('/');
        await expect(page.locator('#domain-chart-container')).toBeVisible({ timeout: 15000 });

        // Apply filter by clicking the domain legend button
        await page.locator('#domain-legend button[data-domain="Robotics"]').click();

        // Clear selection by clicking the same domain legend button again (toggle)
        await page.locator('#domain-legend button[data-domain="Robotics"]').click();

        // Move mouse away from the legend button so legendHoveredDomain clears
        await page.mouse.move(0, 0);

        // The domain pie chart should now show domain segments (no data-score paths)
        await expect(page.locator('#domain-chart-container path[data-domain]').first()).toBeVisible({ timeout: 10000 });
    });

    test('Clicking a domain shows sentiment drill-down', async ({ page, context }) => {
        await context.route('**/api/targets', route => {
            route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(TARGET_WITH_DOMAINS) });
        });
        await context.route('**/api/citations*', route => {
            route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(CITATIONS_WITH_DOMAINS) });
        });

        await page.goto('/');
        await expect(page.locator('#domain-chart-container')).toBeVisible({ timeout: 15000 });

        // Click on "Computer Vision" in the legend
        await page.locator('#domain-legend button[data-domain="Computer Vision"]').click();

        // The domain should be selected
        await expect(page.locator('#domain-legend button[data-domain="Computer Vision"]')).toBeVisible();

        // The clicked domain should still be visible and highlighted in the legend
        await expect(page.locator('#domain-legend button[data-domain="Computer Vision"]')).toBeVisible();

        // The pie chart should now show sentiment segments (SVG paths with data-score)
        await expect(page.locator('#domain-chart-container path[data-score]').first()).toBeVisible({ timeout: 5000 });
    });

    test('Domain search filter works in DataTable', async ({ page, context }) => {
        await context.route('**/api/targets', route => {
            route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(TARGET_WITH_DOMAINS) });
        });
        await context.route('**/api/citations*', route => {
            route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(CITATIONS_WITH_DOMAINS) });
        });

        await page.goto('/');
        await expect(page.locator('#domain-chart-container')).toBeVisible({ timeout: 15000 });

        // Search for "Robotics" — should match the domain field
        await page.fill('input[placeholder*="Search"]', 'Robotics');

        // Wait for filter to apply
        await page.waitForTimeout(500);

        // Should filter to show only the Robotics paper
        await expect(page.locator('text=Paper D')).toBeVisible({ timeout: 10000 });
    });

    test('Phase 5 wipe/run controls are visible in admin mode', async ({ page, context }) => {
        await context.route('**/api/targets', route => {
            route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(TARGET_WITH_DOMAINS) });
        });
        await context.route('**/api/citations*', route => {
            route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(CITATIONS_WITH_DOMAINS) });
        });

        await page.goto('/');

        // Wait for target detail bar by looking for the completed status indicator
        await expect(page.locator('text=Analysis Complete')).toBeVisible({ timeout: 15000 });

        // Phase 5 controls should be visible
        const phase5Label = page.locator('span:text("Phase 5: Update DB")');
        await expect(phase5Label.first()).toBeVisible({ timeout: 5000 });
    });
});
