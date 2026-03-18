/* eslint-disable react-hooks/rules-of-hooks */
import { test as base } from '@playwright/test';
import type { Page } from '@playwright/test';
import { addCoverageReport } from 'monocart-reporter';

// Add coverage collection to the test fixture
export const test = base.extend<{ page: Page }>({
  page: async ({ page }, use) => {
    // start V8 JS coverage (Chromium only)
    if (test.info().project.name === 'chromium' && page.coverage) {
      await page.coverage.startJSCoverage({
        resetOnNavigation: false
      });
    }

    await use(page);

    // stop V8 JS coverage and feed it to monocart reporter
    if (test.info().project.name === 'chromium' && page.coverage) {
      const coverage = await page.coverage.stopJSCoverage();
      await addCoverageReport(coverage, test.info());
    }
  }
});

export { expect } from '@playwright/test';
