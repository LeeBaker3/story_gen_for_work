/**
 * Admin Content Moderation UI tests
 * Covers:
 *  - Initial fetch & render of moderation stories table
 *  - Hide/unhide toggle PATCH call and UI rollback on failure
 *  - Delete story flow (confirm + DELETE + refetch)
 *  - Filter parameter construction
 */
import { fireEvent, waitFor } from '@testing-library/dom';
import { jest } from '@jest/globals';

function setupDOM() {
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
  setupDOM();
  window.localStorage.setItem('authToken', 'test-token');
});

afterEach(() => {
  jest.resetAllMocks();
});

// Helper: install fetch mock for moderation interactions
function installApiMock({ stories = [], userRole = 'admin', hideFail = false, deleteFail = false }) {
  // Lightweight Response polyfill
  global.Response = function (body, init = {}) {
    return {
      ok: (init.status || 200) >= 200 && (init.status || 200) < 300,
      status: init.status || 200,
      json: async () => { try { return JSON.parse(body); } catch { return {}; } },
      text: async () => body,
      headers: { get: (k) => (init.headers && init.headers[k]) || 'application/json' }
    };
  };

  const initialStories = stories.map(s => ({
    id: s.id,
    title: s.title || `Story ${s.id}`,
    owner_id: s.owner_id ?? 1,
    is_draft: !!s.is_draft,
    is_hidden: !!s.is_hidden,
    is_deleted: !!s.is_deleted,
    created_at: s.created_at || new Date().toISOString(),
  }));

  let currentStories = [...initialStories];

  window.fetch = jest.fn(async (url, opts = {}) => {
    if (url.endsWith('/api/v1/users/me/')) {
      return new Response(JSON.stringify({ id: 999, username: 'admin', role: userRole }), { status: 200 });
    }

    if (url.includes('/api/v1/admin/moderation/stories') && (!opts.method || opts.method === 'GET')) {
      // Return current list reflecting any modifications
      const list = currentStories.filter(s => true); // clone
      return new Response(JSON.stringify(list), { status: 200 });
    }

    const hideMatch = url.match(/\/api\/v1\/admin\/moderation\/stories\/(\d+)\/hide$/);
    if (hideMatch && opts.method === 'PATCH') {
      const sid = parseInt(hideMatch[1]);
      if (hideFail) {
        return new Response(JSON.stringify({ detail: 'hide failed' }), { status: 500 });
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
        return new Response(JSON.stringify({ detail: 'delete failed' }), { status: 500 });
      }
      currentStories = currentStories.filter(s => s.id !== sid);
      return new Response('', { status: 204 });
    }

    return new Response(JSON.stringify({ detail: 'not found' }), { status: 404 });
  });

  return { getStories: () => currentStories };
}

async function loadAdminScript() {
  await import('../admin_script.js');
  document.dispatchEvent(new Event('DOMContentLoaded'));
}

function clickModerationNav() {
  const link = document.querySelector('[data-section="content-moderation"]');
  fireEvent.click(link);
}

test('renders moderation stories table with rows', async () => {
  installApiMock({ stories: [ { id: 1, title: 'Alpha', is_draft: false }, { id: 2, title: 'Draft S', is_draft: true } ] });
  await loadAdminScript();
  clickModerationNav();

  await waitFor(() => {
    const table = document.querySelector('#moderation-table-container table');
    expect(table).toBeTruthy();
  });

  const rows = document.querySelectorAll('#moderation-table-container tbody tr');
  expect(rows.length).toBe(2);
  const text = document.getElementById('moderation-table-container').textContent;
  expect(text).toContain('Alpha');
  expect(text).toContain('Draft');
});

test('hide toggle updates on success and rolls back on failure', async () => {
  installApiMock({ stories: [ { id: 5, title: 'HideMe', is_hidden: false } ] });
  await loadAdminScript();
  clickModerationNav();

  await waitFor(() => expect(document.querySelector('.story-hide-toggle')).toBeTruthy());
  const toggle = document.querySelector('.story-hide-toggle');

  // Successful hide
  fireEvent.click(toggle);
  await waitFor(() => {
    expect(toggle.checked).toBe(true);
  });

  // Re-import script with failing hide to test rollback (simulate failure now)
  jest.resetModules();
  installApiMock({ stories: [ { id: 6, title: 'WillFail', is_hidden: false } ], hideFail: true });
  await loadAdminScript();
  clickModerationNav();
  await waitFor(() => expect(document.querySelector('.story-hide-toggle')).toBeTruthy());
  const failingToggle = document.querySelector('.story-hide-toggle');
  fireEvent.click(failingToggle); // attempt to hide
  await waitFor(() => {
    // rollback: should be unchecked after failure
    expect(failingToggle.checked).toBe(false);
  });
});

test('delete story removes row after confirmation', async () => {
  window.confirm = jest.fn(() => true); // auto-confirm
  installApiMock({ stories: [ { id: 11, title: 'ToDelete' }, { id: 12, title: 'Stay' } ] });
  await loadAdminScript();
  clickModerationNav();
  await waitFor(() => expect(document.querySelector('.story-delete-btn')).toBeTruthy());

  const deleteBtn = document.querySelector('.story-delete-btn[data-story-id="11"]');
  fireEvent.click(deleteBtn);

  await waitFor(() => {
    const rows = Array.from(document.querySelectorAll('#moderation-table-container tbody tr'));
    // Story 11 row gone (table re-rendered after refetch)
    const ids = rows.map(r => parseInt(r.dataset.storyId));
    expect(ids).not.toContain(11);
    expect(ids).toContain(12);
  });
});

test('filter params are appended correctly for user, status, hidden, deleted', async () => {
  const fetchSpyState = installApiMock({ stories: [] });
  await loadAdminScript();
  clickModerationNav();
  await waitFor(() => expect(document.getElementById('moderation-table-container')).toBeTruthy());

  // Fill filters
  const userInput = document.getElementById('mod-filter-user');
  const statusSelect = document.getElementById('mod-filter-status');
  const includeHidden = document.getElementById('mod-include-hidden');
  const includeDeleted = document.getElementById('mod-include-deleted');
  const applyBtn = document.getElementById('mod-apply-filters');

  userInput.value = '42';
  statusSelect.value = 'generated';
  includeHidden.checked = true;
  includeDeleted.checked = true;

  fireEvent.click(applyBtn);

  // Look for last fetch call containing expected params
  const calls = window.fetch.mock.calls.map(c => c[0]);
  const moderationGets = calls.filter(u => typeof u === 'string' && u.includes('/api/v1/admin/moderation/stories?'));
  // The second one after applying filters should include all params
  const lastUrl = moderationGets[moderationGets.length - 1];
  expect(lastUrl).toContain('user_id=42');
  expect(lastUrl).toContain('status_filter=generated');
  expect(lastUrl).toContain('include_hidden=true');
  expect(lastUrl).toContain('include_deleted=true');
});
