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

describe('account hub', () => {
    afterEach(() => {
        jest.restoreAllMocks();
    });

    test('renders entitlement balances and account help links from the existing shell', async () => {
        jest.resetModules();
        window.localStorage.clear();
        mountRealAppDom();

        const currentUser = {
            id: 42,
            username: 'reader',
            email: 'reader@example.com',
            role: 'user',
        };
        const entitlement = {
            access_state: 'trial',
            active_entitlement: true,
            renews_at: null,
            trial_expires_at: '2026-05-25T12:00:00Z',
            can_generate_stories: true,
            can_generate_images: true,
            story_credits: { total: 6, reserved: 0, consumed: 2, remaining: 4 },
            image_credits: { total: 18, reserved: 0, consumed: 5, remaining: 13 },
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
                return buildJsonResponse(entitlement);
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
            expect(document.getElementById('account-section').style.display).toBe('block');
            expect(document.getElementById('account-plan-status').textContent).toContain('Trial active until');
            expect(document.getElementById('account-story-credits').textContent).toBe('4 of 6');
            expect(document.getElementById('account-image-credits').textContent).toBe('13 of 18');
            expect(document.getElementById('account-status').textContent).toBe('Account details are up to date.');
        });

        expect(document.getElementById('account-identity').textContent).toBe(
            'Signed in as reader (reader@example.com).'
        );

        const accountLinks = Array.from(
            document.querySelectorAll('#account-section .account-help-list a')
        ).map((link) => [link.textContent.trim(), link.getAttribute('href')]);
        expect(accountLinks).toEqual([
            ['Support policy', '/legal/support-policy'],
            ['Refund policy', '/legal/refund-policy'],
            ['Privacy Operations', '/legal/privacy-operations'],
            ['Privacy Operations', '/legal/privacy-operations'],
            ['Support policy', '/legal/support-policy'],
        ]);
    });
});