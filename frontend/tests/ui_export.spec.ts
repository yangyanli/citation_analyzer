import { test, expect } from './utils/test';

/**
 * ui_export.spec.ts
 *
 * Tests for the Export menu dropdown UI, download triggers, and print-readiness.
 * Uses API mocking to provide deterministic citation data.
 */

test.describe.parallel('Export Menu UI Tests', () => {

    test.beforeEach(async ({ page, context }) => {
        // Mock Auth
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

        // Block polling
        await page.addInitScript(() => {
            (window as unknown as Record<string, unknown>).setInterval = (cb: TimerHandler, ms: number | undefined) => window.setTimeout(cb, ms === 5000 ? 9999999 : ms);
        });
    });

    const TARGET_DATA = {
        targets: {
            "t1": { id: "t1", name: "Dr. Export Test", title: "Dr. Export Test", mode: "scholar", status: "completed", progress: 100, s2_total_citations: 5, total_citations: 5 }
        }
    };

    const CITATION_DATA = {
        records: [
            { citation_id: "c1", citing_title: "Paper Alpha", cited_title: "My Paper", notable_authors: [{ name: "Notable Person", evidence: "Award winner" }], is_seminal: true, year: 2024, url: "#", score: 9, contexts: ["good work"], raw_contexts: ["good work"], research_domain: "Computer Vision", usage_classification: "Extending / Using", positive_comment: "Great extension", sentiment_evidence: "demonstrates significant improvement", venue: "CVPR" },
            { citation_id: "c2", citing_title: "Paper Beta", cited_title: "My Paper", notable_authors: [], is_seminal: false, year: 2023, url: "#", score: 5, contexts: ["used it"], raw_contexts: ["used it"], research_domain: "Natural Language Processing", usage_classification: "Background", positive_comment: "", sentiment_evidence: "refers to prior work", venue: "ACL" },
            { citation_id: "c3", citing_title: "Paper Gamma", cited_title: "My Paper", notable_authors: [], is_seminal: false, year: 2023, url: "#", score: 7, contexts: ["compared results"], raw_contexts: ["compared results"], research_domain: "Computer Vision", usage_classification: "Experimental Comparison", positive_comment: "Favorable comparison", sentiment_evidence: "outperforms baselines", venue: "ICCV" },
        ]
    };

    const NO_DOMAIN_DATA = {
        records: [
            { citation_id: "c1", citing_title: "Paper A", cited_title: "Target", notable_authors: [], is_seminal: false, year: 2024, url: "#", score: 5, contexts: ["ctx"], raw_contexts: ["ctx"], research_domain: null, usage_classification: "Background", positive_comment: "", sentiment_evidence: "" },
        ]
    };

    async function setupMocks(context: any, targets = TARGET_DATA, citations = CITATION_DATA) {
        await context.route('**/api/targets', (route: any) => {
            route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(targets) });
        });
        await context.route('**/api/citations*', (route: any) => {
            route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(citations) });
        });
        await context.route('**/api/fallback-runs/pending', (route: any) => {
            route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ pendingFallback: null }) });
        });
    }

    test('Export button appears when records are loaded', async ({ page, context }) => {
        await setupMocks(context);
        await page.goto('/');
        await expect(page.locator('#export-menu-trigger')).toBeVisible({ timeout: 15000 });
        await expect(page.locator('#export-menu-trigger')).toContainText('Export');
    });

    test('Export button hidden when no records', async ({ page, context }) => {
        await setupMocks(context, TARGET_DATA, { records: [] });
        await page.goto('/');
        // Wait for page to settle
        await page.waitForTimeout(3000);
        await expect(page.locator('#export-menu')).not.toBeVisible();
    });

    test('Clicking Export opens dropdown with 4 options', async ({ page, context }) => {
        await setupMocks(context);
        await page.goto('/');
        await expect(page.locator('#export-menu-trigger')).toBeVisible({ timeout: 15000 });

        await page.locator('#export-menu-trigger').click();

        // All 4 options should be visible
        await expect(page.locator('#export-option-0')).toBeVisible();
        await expect(page.locator('#export-option-1')).toBeVisible();
        await expect(page.locator('#export-option-2')).toBeVisible();
        await expect(page.locator('#export-option-3')).toBeVisible();

        // Verify labels
        await expect(page.locator('#export-option-0')).toContainText('Raw JSON');
        await expect(page.locator('#export-option-1')).toContainText('Raw CSV');
        await expect(page.locator('#export-option-2')).toContainText('Domain Distribution');
        await expect(page.locator('#export-option-3')).toContainText('Standalone HTML');
    });

    test('Clicking outside closes dropdown', async ({ page, context }) => {
        await setupMocks(context);
        await page.goto('/');
        await expect(page.locator('#export-menu-trigger')).toBeVisible({ timeout: 15000 });

        // Open
        await page.locator('#export-menu-trigger').click();
        await expect(page.locator('#export-option-0')).toBeVisible();

        // Click outside (on the backdrop)
        await page.mouse.click(10, 10);
        await expect(page.locator('#export-option-0')).not.toBeVisible();
    });

    test('Export Raw JSON triggers download with correct data', async ({ page, context }) => {
        await setupMocks(context);
        await page.goto('/');
        await expect(page.locator('#export-menu-trigger')).toBeVisible({ timeout: 15000 });

        // Listen for download
        const downloadPromise = page.waitForEvent('download');
        await page.locator('#export-menu-trigger').click();
        await page.locator('#export-option-0').click();
        const download = await downloadPromise;

        // Verify filename
        expect(download.suggestedFilename()).toMatch(/^citations_.*\.json$/);

        // Verify content
        const content = await download.createReadStream().then(stream => {
            return new Promise<string>((resolve) => {
                let data = '';
                stream.on('data', (chunk: Buffer) => data += chunk.toString());
                stream.on('end', () => resolve(data));
            });
        });
        const parsed = JSON.parse(content);
        expect(parsed.target).toBe('Dr. Export Test');
        expect(parsed.total).toBe(3);
        expect(parsed.records).toHaveLength(3);
        expect(parsed.records[0].citing_title).toBe('Paper Alpha');
        expect(parsed.records[0].score).toBe(9);
        expect(parsed.records[0].research_domain).toBe('Computer Vision');
        expect(parsed.records[0].is_seminal).toBe(true);
        expect(parsed.records[0].notable_authors).toHaveLength(1);
    });

    test('Export Raw CSV triggers download with correct format', async ({ page, context }) => {
        await setupMocks(context);
        await page.goto('/');
        await expect(page.locator('#export-menu-trigger')).toBeVisible({ timeout: 15000 });

        const downloadPromise = page.waitForEvent('download');
        await page.locator('#export-menu-trigger').click();
        await page.locator('#export-option-1').click();
        const download = await downloadPromise;

        expect(download.suggestedFilename()).toMatch(/^citations_.*\.csv$/);

        const content = await download.createReadStream().then(stream => {
            return new Promise<string>((resolve) => {
                let data = '';
                stream.on('data', (chunk: Buffer) => data += chunk.toString());
                stream.on('end', () => resolve(data));
            });
        });
        const lines = content.trim().split('\n');
        // Header + 3 data rows
        expect(lines.length).toBe(4);
        expect(lines[0]).toContain('citing_title');
        expect(lines[0]).toContain('score');
        expect(lines[0]).toContain('research_domain');
    });

    test('Export Domain Distribution JSON has correct structure', async ({ page, context }) => {
        await setupMocks(context);
        await page.goto('/');
        await expect(page.locator('#export-menu-trigger')).toBeVisible({ timeout: 15000 });

        const downloadPromise = page.waitForEvent('download');
        await page.locator('#export-menu-trigger').click();
        await page.locator('#export-option-2').click();
        const download = await downloadPromise;

        expect(download.suggestedFilename()).toBe('domains.json');

        const content = await download.createReadStream().then(stream => {
            return new Promise<string>((resolve) => {
                let data = '';
                stream.on('data', (chunk: Buffer) => data += chunk.toString());
                stream.on('end', () => resolve(data));
            });
        });
        const parsed = JSON.parse(content);
        expect(parsed.target).toBe('Dr. Export Test');
        expect(parsed.target_id).toBe('t1');
        expect(parsed.domains).toHaveLength(2); // CV + NLP
        // CV has 2 citations, NLP has 1
        const cv = parsed.domains.find((d: any) => d.domain === 'Computer Vision');
        expect(cv.count).toBe(2);
        expect(cv.sentiment).toBeDefined();
        expect(cv.sentiment.length).toBeGreaterThan(0);
    });

    test('Export Standalone HTML generates valid HTML', async ({ page, context }) => {
        await setupMocks(context);
        await page.goto('/');
        await expect(page.locator('#export-menu-trigger')).toBeVisible({ timeout: 15000 });

        const downloadPromise = page.waitForEvent('download');
        await page.locator('#export-menu-trigger').click();
        await page.locator('#export-option-3').click();
        const download = await downloadPromise;

        expect(download.suggestedFilename()).toMatch(/^citation_report_.*\.html$/);

        const content = await download.createReadStream().then(stream => {
            return new Promise<string>((resolve) => {
                let data = '';
                stream.on('data', (chunk: Buffer) => data += chunk.toString());
                stream.on('end', () => resolve(data));
            });
        });
        // Should be a complete HTML document
        expect(content).toContain('<!DOCTYPE html>');
        expect(content).toContain('<title>Citation Analysis');
        expect(content).toContain('Dr. Export Test');
        // Should contain SVG pie chart
        expect(content).toContain('<svg');
        expect(content).toContain('</svg>');
        // Should contain table with records
        expect(content).toContain('Paper Alpha');
        expect(content).toContain('Paper Beta');
        expect(content).toContain('Paper Gamma');
        // Should contain inline CSS
        expect(content).toContain('<style>');
        // Should have citation-analyzer link
        expect(content).toContain('citation-analyzer');
    });

    test('Dropdown closes after selecting an export option', async ({ page, context }) => {
        await setupMocks(context);
        await page.goto('/');
        await expect(page.locator('#export-menu-trigger')).toBeVisible({ timeout: 15000 });

        // Listen for download (to prevent unhandled download error)
        page.on('download', () => {});
        await page.locator('#export-menu-trigger').click();
        await expect(page.locator('#export-option-0')).toBeVisible();

        await page.locator('#export-option-0').click();
        // Dropdown should close
        await expect(page.locator('#export-option-0')).not.toBeVisible();
    });

    test('Export menu is hidden in print mode via CSS', async ({ page, context }) => {
        await setupMocks(context);
        await page.goto('/');
        await expect(page.locator('#export-menu-trigger')).toBeVisible({ timeout: 15000 });

        // Emulate print media
        await page.emulateMedia({ media: 'print' });

        // Export menu should be hidden
        await expect(page.locator('#export-menu')).not.toBeVisible();
    });

    test('Print mode applies white background', async ({ page, context }) => {
        await setupMocks(context);
        await page.goto('/');
        await expect(page.locator('#export-menu-trigger')).toBeVisible({ timeout: 15000 });

        // Emulate print media
        await page.emulateMedia({ media: 'print' });

        // Body background should be white in print
        const bgColor = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
        // Should not be the dark theme color
        expect(bgColor).not.toContain('rgb(10');
    });

    test('Chevron rotates when dropdown is open', async ({ page, context }) => {
        await setupMocks(context);
        await page.goto('/');
        await expect(page.locator('#export-menu-trigger')).toBeVisible({ timeout: 15000 });

        // Click to open
        await page.locator('#export-menu-trigger').click();
        await expect(page.locator('#export-option-0')).toBeVisible();

        // The chevron should have rotate-180 class
        const chevron = page.locator('#export-menu-trigger svg:last-child');
        const classAttr = await chevron.getAttribute('class');
        expect(classAttr).toContain('rotate-180');
    });
});
