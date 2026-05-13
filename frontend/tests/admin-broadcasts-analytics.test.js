import { fireEvent, waitFor } from '@testing-library/dom';
import { jest } from '@jest/globals';

function setupDOM() {
    document.body.innerHTML = `
        <div id="admin-message-area"></div>
        <div id="snackbar" style="display:none"></div>
        <div id="toast-container"></div>
        <aside id="admin-sidebar"><ul>
            <li><a href="#" data-section="admin-broadcasts">Broadcasts</a></li>
            <li><a href="#" data-section="admin-analytics">Analytics</a></li>
        </ul></aside>
        <section id="admin-view-panel"></section>
    `;
}

function createResponse(body, init = {}) {
    return {
        ok: (init.status || 200) >= 200 && (init.status || 200) < 300,
        status: init.status || 200,
        json: async () => {
            try {
                return JSON.parse(body);
            } catch {
                return {};
            }
        },
        text: async () => body,
        headers: {
            get: (key) => (init.headers && init.headers[key]) || 'application/json',
        },
    };
}

function installApiMock({
    broadcasts = [],
    analytics = null,
    failBroadcasts = false,
    failAnalytics = false,
}) {
    global.Response = createResponse;
    let broadcastState = [...broadcasts];

    window.fetch = jest.fn(async (url, options = {}) => {
        if (url.endsWith('/api/v1/users/me/')) {
            return new Response(JSON.stringify({ id: 1, username: 'admin', role: 'admin' }), { status: 200 });
        }

        if (url.endsWith('/api/v1/admin/broadcasts') && (!options.method || options.method === 'GET')) {
            if (failBroadcasts) {
                return new Response(JSON.stringify({ detail: 'broadcast failure' }), { status: 500 });
            }
            return new Response(JSON.stringify(broadcastState), { status: 200 });
        }

        if (url.endsWith('/api/v1/admin/broadcasts') && options.method === 'POST') {
            const payload = JSON.parse(options.body || '{}');
            const created = {
                id: 1,
                title: payload.title,
                message: payload.message,
                target_scope: 'all_active_users',
                status: 'sent',
                recipient_count: 3,
                created_by_user_id: 1,
                created_at: '2026-05-06T12:00:00Z',
                sent_at: '2026-05-06T12:00:00Z',
            };
            broadcastState = [created, ...broadcastState];
            return new Response(JSON.stringify(created), { status: 201 });
        }

        if (url.endsWith('/api/v1/admin/analytics')) {
            if (failAnalytics) {
                return new Response(JSON.stringify({ detail: 'analytics failure' }), { status: 500 });
            }
            return new Response(JSON.stringify(analytics || {}), { status: 200 });
        }

        return new Response(JSON.stringify({ detail: 'not found' }), { status: 404 });
    });
}

async function loadAdminScript() {
    await import('../admin_script.js');
    document.dispatchEvent(new Event('DOMContentLoaded'));
}

beforeEach(() => {
    jest.resetModules();
    setupDOM();
    window.localStorage.clear();
    window.localStorage.setItem('authToken', 'test-token');
});

afterEach(() => {
    jest.resetAllMocks();
});

test('broadcasts section shows empty state and can send a broadcast', async () => {
    installApiMock({ broadcasts: [] });
    await loadAdminScript();

    fireEvent.click(document.querySelector('[data-section="admin-broadcasts"]'));

    await waitFor(() => {
        expect(document.getElementById('admin-broadcasts-list').textContent).toContain('No broadcasts sent yet.');
    });

    fireEvent.input(document.getElementById('admin-broadcast-title'), {
        target: { value: 'Maintenance window' },
    });
    fireEvent.input(document.getElementById('admin-broadcast-message'), {
        target: { value: 'The editor will be read-only for 10 minutes.' },
    });
    fireEvent.submit(document.getElementById('admin-broadcast-form'));

    await waitFor(() => {
        expect(document.getElementById('admin-broadcasts-list').textContent).toContain('Maintenance window');
    });

    expect(document.getElementById('admin-message-area').textContent).toContain('Broadcast sent to 3 active users.');
});

test('analytics section renders usage summary cards', async () => {
    installApiMock({
        analytics: {
            users_registered_last_7d: 2,
            stories_created_last_7d: 5,
            stories_generated_last_7d: 3,
            characters_created_last_7d: 4,
            active_story_authors_last_7d: 2,
            generation_success_rate_last_7d: 0.75,
            broadcasts_sent_last_30d: 1,
            broadcast_recipients_last_30d: 12,
        },
    });
    await loadAdminScript();

    fireEvent.click(document.querySelector('[data-section="admin-analytics"]'));

    await waitFor(() => {
        expect(document.getElementById('admin-analytics-content').textContent).toContain('Stories Created (7d)');
    });

    const content = document.getElementById('admin-analytics-content').textContent;
    expect(content).toContain('5');
    expect(content).toContain('75.0%');
    expect(content).toContain('Broadcast Recipients (30d)');
});

test('broadcast and analytics sections show failure states clearly', async () => {
    const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => { });
    installApiMock({ failBroadcasts: true, failAnalytics: true });
    await loadAdminScript();

    fireEvent.click(document.querySelector('[data-section="admin-broadcasts"]'));

    await waitFor(() => {
        expect(document.getElementById('admin-broadcasts-list').textContent).toContain('Failed to load broadcasts');
    });

    fireEvent.click(document.querySelector('[data-section="admin-analytics"]'));

    await waitFor(() => {
        expect(document.getElementById('admin-analytics-error').textContent).toContain('Failed to load analytics');
    });

    consoleErrorSpy.mockRestore();
});