
# Project Overview
This project is a **full-stack web application** with:  
- **Backend:** Python (FastAPI)  
- **Frontend:** JavaScript + HTML (with CSS framework as needed)  
- **Database:** SQLit
- **Purpose:** The app is used to generate custom stories and images

Copilot should **maintain consistency between frontend and backend code** and follow the conventions below.  

# Python Coding Conventions

## Python Instructions

- Write clear and concise comments for each function.
- Ensure functions have descriptive names and include type hints.
- Provide docstrings following PEP 257 conventions.
- Use the `typing` module for type annotations (e.g., `List[str]`, `Dict[str, int]`).
- Break down complex functions into smaller, more manageable functions.

## JavaScript / Frontend Instructions
- Use ES6 modules (import/export), no var.
- Use fetch with async/await for API calls.
- Keep functions small and modular.
- Avoid jQuery unless explicitly needed.
- DOM queries are scoped (#app, component roots) to avoid leaks.
- Avoid adding dependencies unless necessary.

## HTML Instructions
- Use semantic HTML5 (<main>, <section>, <nav>, <header>, <footer> etc).
- Use kebab-case for IDs and class names.
- Include accessibility features (ARIA roles, alt text).

## General Instructions

- Always prioritize readability and clarity.
- For algorithm-related code, include explanations of the approach used.
- Write code with good maintainability practices, including comments on why certain design decisions were made.
- Handle edge cases and write clear exception handling.
- For libraries or external dependencies, mention their usage and purpose in comments.
- Use consistent naming conventions and follow language-specific best practices.
- Write concise, efficient, and idiomatic code that is also easily understandable.
- Maintain contract parity (types, field names, status codes) across backend and frontend.
- Provide safe defaults and guard rails (input validation, error handling, timeouts).
- Surface TODOs as code comments with clear next actions.
- Co‑generate:
	•	Endpoint code + model/schema + validation
	•	Matching frontend API wrapper + UI wiring
	•	Tests and doc snippets (README/CONFIG/CHANGELOG stubs)

## Code Style and Formatting

- Follow the **PEP 8** style guide for Python use type hints.
- Maintain proper indentation (use 4 spaces for each level of indentation).
- Ensure lines do not exceed 79 characters.
- Place function and class docstrings immediately after the `def` or `class` keyword.
- Use blank lines to separate functions, classes, and code blocks where appropriate.
- API endpoints must return JSON with proper HTTP status codes.  
- Error format should be consistent:  

## Edge Cases and Testing

- Always include test cases for critical paths of the application.
- Account for common edge cases like empty inputs, invalid data types, and large datasets.
- Include comments for edge cases and the expected behavior in those cases.
- Write unit tests for functions and document them with docstrings explaining the test cases.
- Backend: pytest for unit tests. (structure: backend/test).
- Frontend: Test JS logic with Jest if configured (structure: frontend/tests).
- Linters/formatters: ruff/flake8 + black (Python), eslint + prettier (JS).

## Example of Proper Documentation

```python
def calculate_area(radius: float) -> float:
    """
    Calculate the area of a circle given the radius.
    
    Parameters:
    radius (float): The radius of the circle.
    
    Returns:
    float: The area of the circle, calculated as π * radius^2.
    """
    import math
    return math.pi * radius ** 2
```

# Project Maintenance & Git Workflow

## Before committing changes:

1. Update Documentation Files
- README.md: Ensure usage, setup, and instructions are up to date.
	•	Setup, run, and deployment instructions current
	•	API overview and key endpoints updated
	•	Screenshots/GIFs reflect current UI (if present)
- CONFIG.md: Reflect any new or changed configuration options.
	•	All new/changed environment variables documented
	•	Default values and secure examples (no secrets)
	•	Migration/upgrade notes for config changes
- CHANGELOG.md: Add an entry summarizing changes.
	•	Add an entry for every user‑visible or developer‑facing change
	•	Follow the format below
- PRODUCT_REQUIREMENTS_DOCUMENT.md: Update with new features or changes.
	•	Reflect any new or changed user requirements
	•	Ensure all features are described with acceptance criteria
	•	Ensure any API changes are reflected in the API contracts section

Changelog Format

Follow the existing Keep a Changelog style:
- ## Version heading: [X.Y.Z] - YYYY-MM-DD

Sections:
- ### Added – new features.
- ### Changed – modifications to existing functionality.
- ### Fixed – bug fixes.
- ### (Optional) Removed – deprecated/removed features.

Example:
## [0.4.2] - 2025-08-20
### Added
- New API endpoint for story search with pagination.

### Changed
- Updated frontend to use async/await consistently for fetch calls.

### Fixed
- Prevent crash when uploading malformed image files.

2. Review GitHub Workflow Files (.github/workflows/)
- Ensure CI/CD reflects new dependencies, tests, or build steps.
- Update triggers if new branches or environments are introduced.
- Validate YAML syntax before pushing.

3. Run Tests & Linting
- Run all unit tests (pytest, Jest).
- Lint Python (flake8, black) and JavaScript (ESLint). Run and fix issues as needed


4. Commit Format
Use Conventional Commits:
- feat: for new features
- fix: for bug fixes
- docs: for documentation changes
- chore: for maintenance tasks
- refactor: code change that neither fixes a bug nor adds a feature
- test: adding or correcting tests
- build: build system or external dependencies
- ci: CI/CD changes


Example:
feat(api): add search endpoint with pagination
fix(ui): prevent crash on malformed image upload
ci(workflows): add Python 3.12 to test matrix
docs: update README with docker-compose usage

# Checklists

## Pre‑Commit Checklist
- README updated
- CONFIG updated
- CHANGELOG updated with today’s date
- PRODUCT REQUIREMENTS DOCUMENT updated
- Workflows reviewed/updated as needed
- Tests pass locally
- Linters/formatters clean
	•	Conventional Commit message prepared

## PR Checklist
- Screenshots or API examples included (if UI/API change)
- Backwards compatibility or migration notes
- Security considerations documented (secrets, permissions)
- CI green across all jobs