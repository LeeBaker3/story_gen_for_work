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
        text: async () => JSON.stringify(payload),
        headers: { get: () => 'application/json' },
    };
}

describe('account hub entitlement errors', () => {
    afterEach(() => {
        jest.restoreAllMocks();
    });

    test('shows retryable fallback UI when entitlement loading fails', async () => {
        jest.resetModules();
        window.localStorage.clear();
        mountRealAppDom();

        let entitlementAttempts = 0;
        const currentUser = {
            id: 42,
            username: 'reader',
            email: 'reader@example.com',
            role: 'user',
        };

        global.fetch = jest.fn(async (url, options = {}) => {
            const value = String(url);
            const method = String(options.method || 'GET').toUpperCase();

            if (value.endsWith('/api/v1/users/me/') && method === 'GET') {
                return buildJsonResponse(currentUser);
            }

            if (value.endsWith('/api/v1/users/me') && method === 'GET') {
                return buildJsonResponse(currentUser);
            }

            if (value.endsWith('/api/v1/users/me/entitlement') && method === 'GET') {
                entitlementAttempts += 1;
                if (entitlementAttempts === 1) {
                    return buildJsonResponse({ detail: 'Temporary outage' }, 503);
                }
                return buildJsonResponse({
                    access_state: 'paid-active',
                    active_entitlement: true,
                    renews_at: '2026-06-18T12:00:00Z',
                    trial_expires_at: null,
                    can_generate_stories: true,
                    can_generate_images: true,
                    story_credits: { total: 20, reserved: 0, consumed: 4, remaining: 16 },
                    image_credits: { total: 40, reserved: 0, consumed: 8, remaining: 32 },
                });
            }

            if (value.includes('/api/v1/dynamic-lists/') || value.includes('/api/v1/stories/')) {
                return buildJsonResponse([]);
            }

            return buildJsonResponse({});
        });

        await import('../../frontend/script.js');
        document.dispatchEvent(new Event('DOMContentLoaded'));

        await waitFor(() => {
            expect(document.getElementById('nav-account').style.display).toBe('inline-block');
        });

        fireEvent.click(document.getElementById('nav-account'));

        await waitFor(() => {
            expect(document.getElementById('account-status').textContent).toContain("couldn't load your account details");
            expect(document.getElementById('account-retry-button').style.display).toBe('inline-block');
            expect(document.getElementById('account-story-credits').textContent).toBe('Unavailable');
        });

        expect(
            document.querySelector('#account-section a[href="/legal/privacy-operations"]')
        ).not.toBeNull();

        fireEvent.click(document.getElementById('account-retry-button'));

        await waitFor(() => {
            expect(document.getElementById('account-plan-status').textContent).toContain('Paid plan active until');
            expect(document.getElementById('account-story-credits').textContent).toBe('16 of 20');
            expect(document.getElementById('account-image-credits').textContent).toBe('32 of 40');
            expect(document.getElementById('account-status').textContent).toBe('Account details are up to date.');
        });
    });
});