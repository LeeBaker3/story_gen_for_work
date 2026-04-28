/**
 * Admin User Management UI tests
 * Verifies user-supplied strings are escaped in table rows and edit modal.
 */
import { fireEvent, waitFor } from '@testing-library/dom';
import { jest } from '@jest/globals';

function setupDOM() {
  document.body.innerHTML = `
    <div id="admin-message-area"></div>
    <div id="snackbar" style="display:none"></div>
    <aside id="admin-sidebar"><ul>
      <li><a href="#" data-section="user-management">User Management</a></li>
    </ul></aside>
    <section id="admin-view-panel"></section>
  `;
}

beforeEach(() => {
  setupDOM();
  window.localStorage.setItem('authToken', 'test-token');
  window.__adminXssTriggered = 0;
});

afterEach(() => {
  jest.resetAllMocks();
});

function installApiMock({ users, userRole = 'admin' }) {
  global.Response = function (body, init = {}) {
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
        get: () => (init.headers && init.headers['Content-Type']) ||
          'application/json'
      }
    };
  };

  window.fetch = jest.fn(async (url) => {
    if (url.endsWith('/api/v1/users/me/')) {
      return new Response(
        JSON.stringify({ id: 999, username: 'admin', role: userRole }),
        { status: 200 }
      );
    }

    if (url.endsWith('/api/v1/admin/management/users/')) {
      return new Response(JSON.stringify(users), { status: 200 });
    }

    const singleUserMatch = url.match(/\/api\/v1\/admin\/management\/users\/(\d+)$/);
    if (singleUserMatch) {
      const userId = Number(singleUserMatch[1]);
      const user = users.find((entry) => entry.id === userId);
      if (user) {
        return new Response(JSON.stringify(user), { status: 200 });
      }
    }

    return new Response(JSON.stringify({ detail: 'not found' }), { status: 404 });
  });
}

async function loadAdminScript() {
  jest.resetModules();
  await import('../admin_script.js');
  document.dispatchEvent(new Event('DOMContentLoaded'));
}

function clickUserManagementNav() {
  const link = document.querySelector('[data-section="user-management"]');
  fireEvent.click(link);
}

test('escapes username and email when rendering the admin user table', async () => {
  installApiMock({
    users: [
      {
        id: 7,
        username: '<img src=x data-xss="username">',
        email: '" autofocus onfocus="window.__adminXssTriggered=1',
        role: 'user',
        is_active: true,
      }
    ]
  });

  await loadAdminScript();
  clickUserManagementNav();

  await waitFor(() => {
    expect(document.querySelector('#user-list-table-container table')).toBeTruthy();
  });

  const container = document.getElementById('user-list-table-container');
  expect(container.querySelector('img[data-xss="username"]')).toBeNull();
  expect(container.textContent).toContain('<img src=x data-xss="username">');
  expect(container.textContent).toContain('" autofocus onfocus="window.__adminXssTriggered=1');
});

test('escapes username and email in the edit user modal input values', async () => {
  installApiMock({
    users: [
      {
        id: 9,
        username: '<svg onload="window.__adminXssTriggered=1">',
        email: '" autofocus onfocus="window.__adminXssTriggered=1',
        role: 'user',
        is_active: true,
      }
    ]
  });

  await loadAdminScript();
  clickUserManagementNav();

  await waitFor(() => {
    expect(document.querySelector('.user-edit-details-btn')).toBeTruthy();
  });

  fireEvent.click(document.querySelector('.user-edit-details-btn'));

  await waitFor(() => {
    expect(document.getElementById('editUserDetailsForm')).toBeTruthy();
  });

  const usernameInput = document.getElementById('edit_username');
  const emailInput = document.getElementById('edit_email');

  expect(usernameInput.value).toBe('<svg onload="window.__adminXssTriggered=1">');
  expect(emailInput.value).toBe('" autofocus onfocus="window.__adminXssTriggered=1');
  expect(usernameInput.getAttribute('onload')).toBeNull();
  expect(emailInput.getAttribute('autofocus')).toBeNull();
  expect(emailInput.getAttribute('onfocus')).toBeNull();

  fireEvent.focus(emailInput);
  expect(window.__adminXssTriggered).toBe(0);
});