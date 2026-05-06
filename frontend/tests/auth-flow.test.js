import { fireEvent, waitFor } from '@testing-library/dom';
import { jest } from '@jest/globals';

import fs from 'node:fs';
import path from 'node:path';

function mountRealAppDom() {
    const htmlPath = path.resolve(process.cwd(), 'frontend/index.html');
    const html = fs.readFileSync(htmlPath, 'utf8');
    document.documentElement.innerHTML = html;
}

function buildJsonResponse(payload, status = 200) {
    return {
        ok: status >= 200 && status < 300,
        status,
        json: async () => payload,
        headers: { get: () => 'application/json' },
    };
}

describe('auth form flows', () => {
    beforeEach(async () => {
        jest.resetModules();
        window.localStorage.clear();
        mountRealAppDom();

        global.fetch = jest.fn(async (url, options = {}) => {
            const value = String(url);
            const method = String(options.method || 'GET').toUpperCase();

            if (value.includes('/api/v1/users/me') && method === 'GET') {
                return buildJsonResponse({ id: 7, username: 'reader', role: 'admin' });
            }

            if (value.includes('/api/v1/users/') && method === 'POST') {
                return buildJsonResponse({ id: 12, username: 'new-reader' }, 201);
            }

            if (value.includes('/api/v1/stories/') || value.includes('/api/v1/dynamic-lists/')) {
                return buildJsonResponse([]);
            }

            return buildJsonResponse({});
        });

        await import('../../frontend/script.js');
        document.dispatchEvent(new Event('DOMContentLoaded'));
    });

    afterEach(() => {
        jest.restoreAllMocks();
    });

    test('login posts token form data, persists auth token, and initializes logged-in nav state', async () => {
        global.fetch.mockImplementation(async (url, options = {}) => {
            const value = String(url);
            const method = String(options.method || 'GET').toUpperCase();

            if (value.includes('/api/v1/token') && method === 'POST') {
                return buildJsonResponse({ access_token: 'token-123', token_type: 'bearer' });
            }

            if (value.includes('/api/v1/users/me') && method === 'GET') {
                return buildJsonResponse({ id: 7, username: 'reader', role: 'admin' });
            }

            if (value.includes('/api/v1/stories/') || value.includes('/api/v1/dynamic-lists/')) {
                return buildJsonResponse([]);
            }

            return buildJsonResponse({});
        });

        document.getElementById('login-username').value = 'reader@example.com';
        document.getElementById('login-password').value = 'secret-pass';

        fireEvent.submit(document.getElementById('login-form'));

        await waitFor(() => {
            expect(window.localStorage.getItem('authToken')).toBe('token-123');
        });

        const [, requestOptions] = global.fetch.mock.calls.find(
            ([url, options]) => String(url).includes('/api/v1/token') && String(options?.method || 'GET').toUpperCase() === 'POST'
        );

        expect(requestOptions.headers).toEqual(
            expect.objectContaining({ 'Content-Type': 'application/x-www-form-urlencoded' })
        );
        expect(requestOptions.body).toBeInstanceOf(URLSearchParams);
        expect(requestOptions.body.get('username')).toBe('reader@example.com');
        expect(requestOptions.body.get('password')).toBe('secret-pass');
        expect(document.getElementById('nav-login-signup').style.display).toBe('none');
        expect(document.getElementById('nav-create-story').style.display).toBe('inline-block');
        expect(document.getElementById('story-creation-section').style.display).toBe('block');
        await waitFor(() => {
            expect(document.getElementById('nav-admin-panel').style.display).toBe('inline-block');
        });
    });

    test('failed malformed login response leaves auth state untouched and shows fallback error', async () => {
        global.fetch.mockImplementation(async (url, options = {}) => {
            const value = String(url);
            const method = String(options.method || 'GET').toUpperCase();

            if (value.includes('/api/v1/token') && method === 'POST') {
                return {
                    ok: false,
                    status: 401,
                    json: async () => {
                        throw new Error('bad json');
                    },
                    headers: { get: () => 'application/json' },
                };
            }

            return buildJsonResponse({});
        });

        document.getElementById('login-username').value = 'reader@example.com';
        document.getElementById('login-password').value = 'wrong-pass';

        fireEvent.submit(document.getElementById('login-form'));

        await waitFor(() => {
            expect(document.getElementById('api-message').textContent).toBe('Login failed');
        });

        expect(window.localStorage.getItem('authToken')).toBeNull();
        expect(document.getElementById('nav-login-signup').style.display).not.toBe('none');
        expect(document.getElementById('auth-section').style.display).toBe('block');
    });

    test('signup success posts JSON payload then returns to login view', async () => {
        fireEvent.click(document.getElementById('show-signup-link'));

        document.getElementById('signup-username').value = 'new-reader';
        document.getElementById('signup-email').value = 'new@example.com';
        document.getElementById('signup-password').value = 'secret-pass';
        document.getElementById('signup-password-confirm').value = 'secret-pass';

        fireEvent.submit(document.getElementById('signup-form'));

        await waitFor(() => {
            expect(document.getElementById('api-message').textContent).toBe('Signup successful! Please login.');
        });

        const [, requestOptions] = global.fetch.mock.calls.find(
            ([url, options]) => String(url).includes('/api/v1/users/') && String(options?.method || 'GET').toUpperCase() === 'POST'
        );
        expect(JSON.parse(requestOptions.body)).toEqual({
            username: 'new-reader',
            email: 'new@example.com',
            password: 'secret-pass',
        });
        expect(document.getElementById('signup-form').style.display).toBe('none');
        expect(document.getElementById('login-form').style.display).toBe('block');
        expect(document.getElementById('signup-username').value).toBe('');
    });

    test('signup password mismatch is blocked before request and keeps signup form visible', async () => {
        fireEvent.click(document.getElementById('show-signup-link'));

        document.getElementById('signup-username').value = 'new-reader';
        document.getElementById('signup-email').value = 'new@example.com';
        document.getElementById('signup-password').value = 'secret-pass';
        document.getElementById('signup-password-confirm').value = 'different-pass';

        fireEvent.submit(document.getElementById('signup-form'));

        await waitFor(() => {
            expect(document.getElementById('api-message').textContent).toBe('Passwords do not match. Please re-enter.');
        });

        expect(
            global.fetch.mock.calls.some(
                ([url, options]) => String(url).includes('/api/v1/users/') && String(options?.method || 'GET').toUpperCase() === 'POST'
            )
        ).toBe(false);
        expect(document.getElementById('signup-form').style.display).toBe('block');
        expect(document.getElementById('login-form').style.display).toBe('none');
    });
});