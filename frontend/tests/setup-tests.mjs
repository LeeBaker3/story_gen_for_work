// Jest setup for DOM Testing Library and jsdom (ESM)
import '@testing-library/jest-dom';
import { afterEach, beforeEach, jest } from '@jest/globals';
import { format } from 'node:util';

// Provide a basic fetch mock; individual tests can override as needed
import './utils/mock-fetch.js';

/**
 * Treat unexpected console output as test failures.
 *
 * These tests load parts of `frontend/script.js`, which currently logs a handful
 * of “missing element” messages under jsdom (because tests don’t always render
 * the full app DOM). We allow-list those known messages so real regressions
 * don’t get buried in noisy output.
 *
 * To temporarily disable strict console behavior (e.g., while authoring a new
 * test), run:
 * - `ALLOW_CONSOLE=1 npm test`
 */
if (!process.env.ALLOW_CONSOLE) {
    const originalError = console.error.bind(console);
    const originalWarn = console.warn.bind(console);
    const showAllowedConsole = Boolean(process.env.SHOW_ALLOWED_CONSOLE);

    /**
     * Collect unexpected console output per-test and fail in `afterEach`.
     * Throwing immediately can cause cascading failures when application code
     * catches and logs errors as part of normal failure-path behavior.
     */
    let unexpectedErrors = [];
    let unexpectedWarns = [];

    const allowedErrorPatterns = [
        /^\[populateDropdown\] Select element with ID '.+' not found\.$/,
        /^CRITICAL ERROR: 'Add Character' button \(id: add-character-button\) not found in the DOM\./,
        /^\[auth\] signupForm not found; signup will not work\.$/,
        /^\[auth\] loginForm not found; login will not work\.$/,
        /^Export PDF button not found during event listener setup\.$/,
        /^CRITICAL: main-characters-fieldset not found for event delegation!$/,
        /^Error during status polling:/,
        /^\[resetFormAndState\] storyCreationForm is null!$/,
        /^Failed to load stories:/,
        /^\[apiRequest\] API Error:/,
        /^API Error \((GET|POST|PUT|PATCH|DELETE) .+\):/,
        /^\[Character Library\] Load failed:/,
        /^Failed to fetch admin stats:/,
    ];

    const allowedWarnPatterns = [
        /^\[populateDropdown\] No active items found for list: .+$/,
    ];

    const isAllowed = (text, patterns) => patterns.some((p) => p.test(text));

    beforeEach(() => {
        unexpectedErrors = [];
        unexpectedWarns = [];
    });

    afterEach(() => {
        if (unexpectedErrors.length === 0 && unexpectedWarns.length === 0) {
            return;
        }

        const lines = [];
        for (const msg of unexpectedErrors) {
            lines.push(`[console.error] ${msg}`);
        }
        for (const msg of unexpectedWarns) {
            lines.push(`[console.warn] ${msg}`);
        }
        throw new Error(`Unexpected console output:\n${lines.join('\n')}`);
    });

    console.error = (...args) => {
        const text = format(...args);
        if (isAllowed(text, allowedErrorPatterns)) {
            if (showAllowedConsole) {
                originalError(...args);
            }
            return;
        }
        unexpectedErrors.push(text);
        originalError(...args);
    };

    console.warn = (...args) => {
        const text = format(...args);
        if (isAllowed(text, allowedWarnPatterns)) {
            if (showAllowedConsole) {
                originalWarn(...args);
            }
            return;
        }
        unexpectedWarns.push(text);
        originalWarn(...args);
    };
}

// Reduce noisy animations and timers during tests
Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: jest.fn().mockImplementation((query) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: jest.fn(), // deprecated
        removeListener: jest.fn(), // deprecated
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
        dispatchEvent: jest.fn(),
    })),
});
