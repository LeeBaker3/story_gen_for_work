// Jest setup for DOM Testing Library and jsdom (ESM)
import '@testing-library/jest-dom/extend-expect';

// Provide a basic fetch mock; individual tests can override as needed
import './utils/mock-fetch.js';

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
