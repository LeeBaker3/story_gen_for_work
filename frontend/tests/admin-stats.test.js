/**
 * Admin Stats UI tests
 * Verifies rendering, refresh behavior, and error handling.
 */
import { fireEvent, waitFor } from '@testing-library/dom';
import { jest } from '@jest/globals';

// Minimal DOM scaffolding replicating admin.html essentials
function setupDOM() {
  document.body.innerHTML = `
    <div id="admin-message-area"></div>
    <div id="snackbar" style="display:none"></div>
    <aside id="admin-sidebar"><ul><li><a href="#" data-section="admin-stats">Admin Stats</a></li></ul></aside>
    <section id="admin-view-panel"></section>
  `;
}

// Mock localStorage token for admin role checks
beforeEach(() => {
  setupDOM();
  window.localStorage.setItem('authToken', 'test-token');
});

afterEach(() => {
  jest.resetAllMocks();
});

// Provide a simple apiRequest mock harness hooked before admin_script loads
function installApiMock({ statsResponse, userRole = 'admin', failStats = false }) {
  // Provide a minimal Response polyfill for jsdom environment
  global.Response = function (body, init = {}) {
    return {
      ok: (init.status || 200) >= 200 && (init.status || 200) < 300,
      status: init.status || 200,
      json: async () => { try { return JSON.parse(body); } catch { return {}; } },
      text: async () => body,
      headers: { get: () => (init.headers && init.headers['Content-Type']) || 'application/json' }
    };
  };

  window.fetch = jest.fn(async (url, opts) => {
    if (url.endsWith('/api/v1/users/me/')) {
      return new Response(JSON.stringify({ id: 1, username: 'admin', role: userRole }), { status: 200 });
    }
    if (url.endsWith('/api/v1/admin/stats')) {
      if (failStats) {
        return new Response(JSON.stringify({ detail: 'failure' }), { status: 500 });
      }
      return new Response(JSON.stringify(statsResponse), { status: 200 });
    }
    return new Response(JSON.stringify({ detail: 'not found' }), { status: 404 });
  });
}

// Dynamically import the admin script after setting up mocks
async function loadAdminScript() {
  await import('../admin_script.js');
  // Trigger the DOMContentLoaded hook that the admin script relies on
  document.dispatchEvent(new Event('DOMContentLoaded'));
}

const baseStats = {
  total_users: 5,
  active_users: 4,
  total_stories: 10,
  generated_stories: 7,
  draft_stories: 3,
  total_characters: 18,
  tasks_last_24h: 6,
  tasks_in_progress: 1,
  tasks_failed_last_24h: 2,
  tasks_completed_last_24h: 3,
  avg_task_duration_seconds_last_24h: 12.34,
  success_rate_last_24h: 0.6,
  avg_attempts_last_24h: 1.67,
};

function clickAdminStatsNav() {
  const link = document.querySelector('[data-section="admin-stats"]');
  fireEvent.click(link);
}

test('renders admin stats cards with expected values', async () => {
  installApiMock({ statsResponse: baseStats });
  await loadAdminScript();
  clickAdminStatsNav();

  await waitFor(() => {
    const el = document.querySelector('#admin-stats-content .admin-card');
    expect(el).toBeTruthy();
  });

  const content = document.getElementById('admin-stats-content').textContent;
  expect(content).toContain('10 total');
  expect(content).toContain('Users');
  expect(content).toContain('Success Rate');
  expect(content).toContain('60.0%');
  expect(content).toContain('Avg Attempts');
  expect(content).toContain('1.67');
});

test('refresh button triggers fetch again', async () => {
  installApiMock({ statsResponse: baseStats });
  await loadAdminScript();
  clickAdminStatsNav();

  await waitFor(() => expect(document.getElementById('admin-stats-content')).toBeTruthy());

  // Adjust mock to simulate changed numbers on second call
  const newStats = { ...baseStats, total_users: 6, success_rate_last_24h: 0.5 };
  window.fetch.mockImplementationOnce(async (url) => {
    if (url.endsWith('/api/v1/users/me/')) {
      return new Response(JSON.stringify({ id: 1, username: 'admin', role: 'admin' }), { status: 200 });
    }
    if (url.endsWith('/api/v1/admin/stats')) {
      return new Response(JSON.stringify(newStats), { status: 200 });
    }
    return new Response('Not Found', { status: 404 });
  });

  const refreshBtn = document.getElementById('refresh-admin-stats-btn');
  fireEvent.click(refreshBtn);

  await waitFor(() => {
    expect(document.getElementById('admin-stats-content').textContent).toContain('6 total / 4 active');
  });
});

test('handles stats fetch failure gracefully', async () => {
  installApiMock({ statsResponse: baseStats, failStats: true });
  await loadAdminScript();
  clickAdminStatsNav();

  await waitFor(() => {
    const err = document.getElementById('admin-stats-error');
    expect(err).toBeTruthy();
    expect(err.style.display).toBe('block');
  });
});

