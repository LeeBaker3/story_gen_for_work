import { jest } from '@jest/globals';

describe('API base URL resolution', () => {
    beforeEach(() => {
        jest.resetModules();
        window.STORY_GENERATOR_CONFIG = {};
    });

    afterEach(() => {
        window.STORY_GENERATOR_CONFIG = {};
    });

    test('uses localhost backend by default during local development', async () => {
        await import('../../frontend/runtime-config.js');

        expect(
            window.resolveStoryGeneratorApiBaseUrl(
                new URL('http://localhost/'),
            ),
        ).toBe('http://127.0.0.1:8000');
    });

    test('uses configured API base URL when provided', async () => {
        window.STORY_GENERATOR_CONFIG = {
            apiBaseUrl: 'https://api.example.com/',
        };
        await import('../../frontend/runtime-config.js');

        expect(
            window.resolveStoryGeneratorApiBaseUrl(
                new URL('https://app.example.com/'),
            ),
        ).toBe('https://api.example.com');
    });

    test('falls back to same-origin requests outside local development', async () => {
        await import('../../frontend/runtime-config.js');

        expect(
            window.resolveStoryGeneratorApiBaseUrl(
                new URL('https://app.example.com/admin.html'),
            ),
        ).toBe('https://app.example.com');
    });
});