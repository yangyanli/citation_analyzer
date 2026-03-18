# Contributing to Citation Analyzer

First off, thank you for considering contributing to Citation Analyzer! It's people like you that make this tool great.

## Code of Conduct

This project and everyone participating in it is governed by the [Citation Analyzer Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## How Can I Contribute?

### Reporting Bugs
This section guides you through submitting a bug report for Citation Analyzer. Following these guidelines helps maintainers and the community understand your report, reproduce the behavior, and find related reports.
* Use a clear and descriptive title for the issue.
* Describe the exact steps which reproduce the problem.
* Provide specific examples to demonstrate the steps.

### Suggesting Enhancements
This section guides you through submitting an enhancement suggestion for Citation Analyzer, including completely new features and minor improvements to existing functionality.
* Use a clear and descriptive title for the issue.
* Provide a step-by-step description of the suggested enhancement.
* Explain why this enhancement would be useful to most Citation Analyzer users.

### Pull Requests
* Fill in the required template.
* Do not include issue numbers in the PR title.
* Include screenshots and animated GIFs in your pull request whenever possible.
* Follow the TypeScript and Python styleguides.
* End files with a newline.

## Setup for Development

1. **Backend:**
    * Clone the repository.
    * Install dependencies with `pip install -r backend/requirements.txt`
    * Setup `.env` file with `GEMINI_API_KEY=your_key_here`
    * Run formatters (`black`) and linters (`flake8`) before committing.

2. **Frontend:**
    * Navigate to `frontend/`.
    * Run `npm install`
    * Run `npm run dev` to start the development server.

## Testing
Please make sure that the test suite passes before submitting your PR.
* Backend: `pytest backend/tests/`
* Frontend: `npm run test` (requires a valid `GEMINI_API_KEY` or wait for the LLM fallback timeout).

We look forward to your contributions!
