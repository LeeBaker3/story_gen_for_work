/**
 * Extended Admin Moderation UI Tests
 * Focus areas:
 *  - Filter persistence across reload (in-memory re-application scenario)
 *  - Delete failure does not remove row
 *  - Hide failure leaves checkbox state unchanged (redundant/defensive)
 *  - Empty results message appears
 */
import { fireEvent, waitFor } from '@testing-library/dom';
import { jest } from '@jest/globals';

function baseDOM() {
    document.body.innerHTML = `
    <div id="admin-message-area"></div>
    <div id="snackbar" style="display:none"></div>
    <aside id="admin-sidebar"><ul>
      <li><a href="#" data-section="content-moderation">Moderation</a></li>
    </ul></aside>
    <section id="admin-view-panel"></section>
  `;
}

beforeEach(() => {
    baseDOM();
    window.localStorage.setItem('authToken', 'test-token');
});

afterEach(() => {
    jest.resetAllMocks();
});

function installModerationMock({ stories = [], userRole = 'admin', hideFail = false, deleteFail = false }) {
    global.Response = function (body, init = {}) {
        return {
            ok: (init.status || 200) >= 200 && (init.status || 200) < 300,
            status: init.status || 200,
            json: async () => { try { return JSON.parse(body); } catch { return {}; } },
            text: async () => body,
            headers: { get: (k) => (init.headers && init.headers[k]) || 'application/json' }
        };
    };

    let currentStories = stories.map(s => ({
        id: s.id,
        title: s.title || `Story ${s.id}`,
        owner_id: s.owner_id ?? 1,
        is_draft: !!s.is_draft,
        is_hidden: !!s.is_hidden,
        is_deleted: !!s.is_deleted,
        created_at: s.created_at || new Date().toISOString(),
    }));

    window.fetch = jest.fn(async (url, opts = {}) => {
        if (url.endsWith('/api/v1/users/me/')) {
            return new Response(JSON.stringify({ id: 99, role: userRole, username: 'admin' }), { status: 200 });
        }

        if (url.includes('/api/v1/admin/moderation/stories') && (!opts.method || opts.method === 'GET')) {
            return new Response(JSON.stringify(currentStories), { status: 200 });
        }

        const hideMatch = url.match(/\/api\/v1\/admin\/moderation\/stories\/(\d+)\/hide$/);
        if (hideMatch && opts.method === 'PATCH') {
            const sid = parseInt(hideMatch[1]);
            if (hideFail) {
                return new Response(JSON.stringify({ detail: 'hide fail' }), { status: 500 });
            }
            const body = JSON.parse(opts.body || '{}');
            currentStories = currentStories.map(s => s.id === sid ? { ...s, is_hidden: !!body.is_hidden } : s);
            const updated = currentStories.find(s => s.id === sid);
            return new Response(JSON.stringify(updated), { status: 200 });
        }

        const deleteMatch = url.match(/\/api\/v1\/admin\/moderation\/stories\/(\d+)$/);
        if (deleteMatch && opts.method === 'DELETE') {
            const sid = parseInt(deleteMatch[1]);
            if (deleteFail) {
                return new Response(JSON.stringify({ detail: 'delete fail' }), { status: 500 });
            }
            currentStories = currentStories.filter(s => s.id !== sid);
            return new Response('', { status: 204 });
        }

        return new Response(JSON.stringify({ detail: 'not found' }), { status: 404 });
    });

    return { getStories: () => currentStories };
}

async function loadScript() {
    await import('../admin_script.js');
    document.dispatchEvent(new Event('DOMContentLoaded'));
}

function openModeration() {
    fireEvent.click(document.querySelector('[data-section="content-moderation"]'));
}

// 1. Ensure empty state message appears
test('shows empty state when no stories returned', async () => {
    installModerationMock({ stories: [] });
    await loadScript();
    openModeration();
    await waitFor(() => {
        expect(document.getElementById('moderation-table-container').textContent).toMatch(/No stories found/i);
    });
});

// 2. Delete failure does not remove row
test('delete failure leaves row intact', async () => {
    window.confirm = jest.fn(() => true);
    installModerationMock({ stories: [{ id: 301, title: 'PersistFail' }], deleteFail: true });
    await loadScript();
    openModeration();
    await waitFor(() => expect(document.querySelector('.story-delete-btn')).toBeTruthy());
    fireEvent.click(document.querySelector('.story-delete-btn'));
    // row should still exist after failure
    await waitFor(() => {
        const row = document.querySelector('tr[data-story-id="301"]');
        expect(row).toBeTruthy();
    });
});

// 3. Hide failure leaves checkbox rolled back (defensive)
test('hide failure reverts checkbox to original state', async () => {
    installModerationMock({ stories: [{ id: 501, title: 'HideFail', is_hidden: false }], hideFail: true });
    await loadScript();
    openModeration();
    await waitFor(() => expect(document.querySelector('.story-hide-toggle')).toBeTruthy());
    const toggle = document.querySelector('.story-hide-toggle');
    expect(toggle.checked).toBe(false);
    fireEvent.click(toggle); // attempt to set true
    await waitFor(() => expect(toggle.checked).toBe(false)); // rolled back
});

// 4. Filter application triggers correct query params (redundant coverage of ordering + defaults) 
test('filter persistence simulation (reapply after reload)', async () => {
    const mock = installModerationMock({ stories: [{ id: 901, title: 'FilterPersist' }] });
    await loadScript();
    openModeration();
    await waitFor(() => expect(document.querySelector('.story-hide-toggle')).toBeTruthy());

    // Set filters
    const userInput = document.getElementById('mod-filter-user');
    const statusSelect = document.getElementById('mod-filter-status');
    const includeHidden = document.getElementById('mod-include-hidden');
    userInput.value = '77';
    statusSelect.value = 'draft';
    includeHidden.checked = true;
    fireEvent.click(document.getElementById('mod-apply-filters'));

    // Capture the URL used
    const calls1 = window.fetch.mock.calls.map(c => c[0]);
    const last1 = calls1.filter(u => typeof u === 'string' && u.includes('/api/v1/admin/moderation/stories?')).pop();
    expect(last1).toContain('user_id=77');
    expect(last1).toContain('status_filter=draft');
    expect(last1).toContain('include_hidden=true');

    // Simulate reload (re-import script) - ephemeral persistence; we simply assert filters start blank per current implementation.
    jest.resetModules();
    baseDOM();
    window.localStorage.setItem('authToken', 'test-token');
    installModerationMock({ stories: mock.getStories() });
    await loadScript();
    openModeration();
    await waitFor(() => expect(document.querySelector('.story-hide-toggle')).toBeTruthy());
    // Current implementation does not persist filters: ensure inputs are blank/unchecked
    expect(document.getElementById('mod-filter-user').value).toBe('');
    expect(document.getElementById('mod-filter-status').value).toBe('');
    expect(document.getElementById('mod-include-hidden').checked).toBe(false);
});
