import { fireEvent, waitFor } from '@testing-library/dom';
import { jest } from '@jest/globals';

function setupDOM() {
  document.body.innerHTML = `
    <div id="admin-message-area"></div>
    <div id="snackbar" style="display:none"></div>
    <aside id="admin-sidebar"><ul>
      <li><a href="#" data-section="dynamic-content">Dynamic Content</a></li>
    </ul></aside>
    <section id="admin-view-panel"></section>
  `;
}

beforeEach(() => {
  setupDOM();
  window.localStorage.setItem('authToken', 'test-token');
  window.__adminDynamicXssTriggered = 0;
});

afterEach(() => {
  jest.resetAllMocks();
});

function installApiMock() {
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
        get: () => (init.headers && init.headers['Content-Type']) || 'application/json'
      }
    };
  };

  window.fetch = jest.fn(async (url) => {
    if (url.endsWith('/api/v1/users/me/')) {
      return new Response(JSON.stringify({ id: 1, username: 'admin', role: 'admin' }), { status: 200 });
    }
    if (url.endsWith('/api/v1/admin/dynamic-lists/')) {
      return new Response(JSON.stringify([
        { list_name: 'genres', list_label: 'Genres', description: 'Story genres' }
      ]), { status: 200 });
    }
    if (url.endsWith('/api/v1/admin/dynamic-lists/genres/items')) {
      return new Response(JSON.stringify([
        {
          id: 5,
          list_name: 'genres',
          item_value: '<img src=x data-admin-dynamic-xss="value">',
          item_label: 'Label',
          is_active: true,
          sort_order: 1,
          additional_config: null
        }
      ]), { status: 200 });
    }
    if (url.endsWith('/api/v1/admin/dynamic-lists/items/5')) {
      return new Response(JSON.stringify({
        id: 5,
        list_name: 'genres',
        item_value: '<img src=x data-admin-dynamic-xss="value">',
        item_label: '" autofocus onfocus="window.__adminDynamicXssTriggered=1',
        is_active: true,
        sort_order: 1,
        additional_config: null
      }), { status: 200 });
    }
    if (url.endsWith('/api/v1/admin/dynamic-lists/items/5/in-use')) {
      return new Response(JSON.stringify({ is_in_use: false, details: [] }), { status: 200 });
    }
    return new Response(JSON.stringify({ detail: 'not found' }), { status: 404 });
  });
}

async function loadAdminScript() {
  jest.resetModules();
  await import('../admin_script.js');
  document.dispatchEvent(new Event('DOMContentLoaded'));
}

test('dynamic list item modal escapes stored values before injecting innerHTML', async () => {
  installApiMock();

  await loadAdminScript();
  fireEvent.click(document.querySelector('[data-section="dynamic-content"]'));

  await waitFor(() => {
    expect(document.getElementById('select-list-for-items')).toBeTruthy();
  });

  await waitFor(() => {
    expect(document.querySelector('#select-list-for-items option[value="genres"]')).toBeTruthy();
  });

  fireEvent.click(document.querySelector('[data-tab="manage-items"]'));
  fireEvent.change(document.getElementById('select-list-for-items'), {
    target: { value: 'genres' }
  });

  await waitFor(() => {
    expect(document.querySelector('.edit-dynamic-list-item-btn')).toBeTruthy();
  });

  fireEvent.click(document.querySelector('.edit-dynamic-list-item-btn'));

  await waitFor(() => {
    expect(document.getElementById('dynamicListItemForm')).toBeTruthy();
  });

  const itemValueInput = document.getElementById('item_value');
  const itemLabelInput = document.getElementById('item_label');

  expect(document.querySelector('#dynamicListItemModal [data-admin-dynamic-xss="value"]')).toBeNull();
  expect(itemValueInput.value).toBe('<img src=x data-admin-dynamic-xss="value">');
  expect(itemLabelInput.value).toBe('" autofocus onfocus="window.__adminDynamicXssTriggered=1');
  expect(itemLabelInput.getAttribute('autofocus')).toBeNull();
  expect(itemLabelInput.getAttribute('onfocus')).toBeNull();

  fireEvent.focus(itemLabelInput);
  expect(window.__adminDynamicXssTriggered).toBe(0);
});

test('dynamic list modal exposes dialog semantics and restores focus after escape', async () => {
  installApiMock();

  await loadAdminScript();
  fireEvent.click(document.querySelector('[data-section="dynamic-content"]'));

  await waitFor(() => {
    expect(document.getElementById('add-new-list-btn')).toBeTruthy();
  });

  const triggerButton = document.getElementById('add-new-list-btn');
  fireEvent.click(triggerButton);

  await waitFor(() => {
    expect(document.getElementById('dynamicListModal')).toBeTruthy();
  });

  const dialog = document.getElementById('dynamicListModal');
  const title = dialog.querySelector('h2');
  const listNameInput = document.getElementById('dl_list_name');

  expect(dialog.getAttribute('role')).toBe('dialog');
  expect(dialog.getAttribute('aria-modal')).toBe('true');
  expect(dialog.getAttribute('aria-labelledby')).toBe(title.id);
  expect(document.activeElement).toBe(listNameInput);

  fireEvent.keyDown(dialog, { key: 'Escape' });

  await waitFor(() => {
    expect(document.getElementById('dynamicListModal')).toBeNull();
  });
  expect(document.activeElement).toBe(triggerButton);
});