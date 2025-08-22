import { fireEvent, waitFor } from '@testing-library/dom';
import { jest } from '@jest/globals';

function mountCharactersPageDom() {
  document.body.innerHTML = `
  <header>
    <nav>
      <div class="nav-buttons">
        <button id="nav-login-signup" class="nav-button">Login / Sign Up</button>
        <button id="nav-create-story" class="nav-button" style="display:none;">Create New Story</button>
        <button id="nav-browse-stories" class="nav-button" style="display:none;">My Stories</button>
        <button id="nav-characters" class="nav-button">Characters</button>
        <a id="nav-admin-panel" href="#" class="nav-button" style="display:none;">Admin Panel</a>
        <button id="nav-logout" class="nav-button" style="display:none;">Logout</button>
      </div>
    </nav>
  </header>
  <main>
    <section id="auth-section" style="display:none;"></section>
    <section id="story-creation-section" style="display:none;">
      <div id="main-characters-fieldset"></div>
    </section>
    <section id="story-preview-section" style="display:none;"></section>
    <section id="browse-stories-section" style="display:none;"></section>
    <section id="characters-section" style="display:none;">
      <input id="characters-page-search" />
      <div id="characters-page-list"></div>
      <div id="characters-page-pagination"></div>
      <div id="char-modal-backdrop" class="modal-backdrop" aria-hidden="true"></div>
      <div id="char-modal" class="modal" role="dialog">
        <div class="modal-content" data-status-region="true">
          <div class="modal-actions">
            <button type="button" id="char-modal-regenerate"></button>
            <button type="button" id="char-modal-duplicate"></button>
            <button type="button" id="char-modal-save"></button>
          </div>
          <div id="char-modal-status" class="inline-status" role="status" aria-live="polite" aria-atomic="true" style="display:none;"></div>
        </div>
      </div>
    </section>
    <div id="snackbar" role="status" aria-live="polite" style="display:none;"></div>
  </main>`;
}

describe('characters page resilience and a11y', () => {
  beforeEach(async () => {
    mountCharactersPageDom();
    window.localStorage.setItem('authToken', 't');

    // Fetch mock: list succeeds, delete fails with 500
    global.fetch = jest.fn(async (url, opts) => {
      const u = String(url);
      if (u.includes('/api/v1/dynamic-lists/')) {
        return { ok: true, status: 200, json: async () => [], headers: { get: () => 'application/json' } };
      }
      if (u.match(/\/api\/v1\/characters\??\?/)) {
        // Not expected format; fall through
      }
      if (u.match(/\/api\/v1\/characters\??\?page=/)) {
        // characters page list
        return {
          ok: true,
          status: 200,
          json: async () => ({ total: 10, items: [{ id: 1, name: 'Alpha', thumbnail_path: null }] }),
          headers: { get: () => 'application/json' },
        };
      }
      if (u.match(/\/api\/v1\/characters\/1$/) && (opts?.method === 'DELETE')) {
        return {
          ok: false,
          status: 500,
          json: async () => ({ detail: 'Server error deleting character' }),
          headers: { get: () => 'application/json' },
        };
      }
      // Default OK for any other calls
      return { ok: true, status: 200, json: async () => ({}), headers: { get: () => 'application/json' } };
    });

    await import('../../frontend/script.js');
    document.dispatchEvent(new Event('DOMContentLoaded'));
  });

  test('delete failure shows snackbar error and does not refresh list', async () => {
    // Navigate to characters page and wait initial list
    document.getElementById('nav-characters').click();
    await waitFor(() => {
      const list = document.getElementById('characters-page-list');
      expect(list.children.length).toBeGreaterThan(0);
    });

    const callsBefore = (global.fetch.mock.calls || []).length;

    // Click Delete button for item 1
    const deleteBtn = document.querySelector('button[data-action="delete"][data-id="1"]');
    // confirm() is used in code; stub it to return true
    const origConfirm = window.confirm;
    window.confirm = () => true;
    fireEvent.click(deleteBtn);
    window.confirm = origConfirm;

    // Expect an additional fetch call (DELETE), but no subsequent list refresh (since failure)
    await waitFor(() => {
      const after = (global.fetch.mock.calls || []).length;
      expect(after).toBe(callsBefore + 1);
    });

    // Snackbar should be visible with error message and have proper a11y attributes
    const snackbar = document.getElementById('snackbar');
    await waitFor(() => {
      expect(snackbar.style.display).toBe('block');
      expect(snackbar.textContent).toMatch(/Server error deleting character/i);
    });
    expect(snackbar.getAttribute('role')).toBe('status');
    expect(snackbar.getAttribute('aria-live')).toBe('polite');
  });
});

describe('wizard character library: load failure shows inline error', () => {
  function mountWizardDom() {
    document.body.innerHTML = `
    <header>
      <nav>
        <div class="nav-buttons">
          <button id="nav-login-signup" class="nav-button">Login / Sign Up</button>
          <button id="nav-create-story" class="nav-button" style="display:none;">Create New Story</button>
          <button id="nav-browse-stories" class="nav-button" style="display:none;">My Stories</button>
          <button id="nav-characters" class="nav-button" style="display:none;">Characters</button>
          <a id="nav-admin-panel" href="#" class="nav-button" style="display:none;">Admin Panel</a>
          <button id="nav-logout" class="nav-button" style="display:none;">Logout</button>
        </div>
      </nav>
    </header>
    <main>
      <section id="auth-section" style="display:none;"></section>
      <section id="story-creation-section" style="display:none;">
        <div id="wizard-steps">
          <div class="wizard-step" data-step="0"></div>
          <div class="wizard-step" data-step="1"></div>
          <div class="wizard-step" data-step="2"></div>
          <div class="wizard-step" data-step="3"></div>
        </div>
        <button id="wizard-prev" type="button">Prev</button>
        <button id="wizard-next" type="button">Next</button>
        <section id="step-0-basics" style="display:block;">
          <select id="story-genre"><option value="fantasy">Fantasy</option></select>
          <textarea id="story-outline">Outline</textarea>
        </section>
        <section id="step-1-characters" style="display:none;">
          <div id="character-library-panel" style="display:none;">
            <input id="character-search" />
            <div id="character-list"></div>
            <div id="character-pagination"></div>
          </div>
          <div id="main-characters-fieldset"></div>
        </section>
        <section id="step-2-options" style="display:none;"></section>
        <section id="step-3-review" style="display:none;"></section>
      </section>
      <div id="snackbar" role="status" aria-live="polite" style="display:none;"></div>
    </main>`;
  }

  beforeEach(async () => {
    mountWizardDom();
    window.localStorage.setItem('authToken', 't');

    global.fetch = jest.fn(async (url) => {
      const u = String(url);
      if (u.includes('/api/v1/dynamic-lists/')) {
  return { ok: true, status: 200, json: async () => ([{ item_value: 'fantasy', item_label: 'Fantasy' }]), headers: { get: () => 'application/json' } };
      }
      if (u.match(/\/api\/v1\/characters\/?\?/)) {
        // Library list load fails
        return { ok: false, status: 500, json: async () => ({ detail: 'Library load failed' }), headers: { get: () => 'application/json' } };
      }
      return { ok: true, status: 200, json: async () => ({}), headers: { get: () => 'application/json' } };
    });

    await import('../../frontend/script.js');
    document.dispatchEvent(new Event('DOMContentLoaded'));
  });

  test('shows inline error message when library load fails', async () => {
    // Enter create flow and go to step 1
  document.getElementById('nav-create-story').click();
  // Fill minimal valid fields to pass step-0 validation
  document.getElementById('story-genre').value = 'fantasy';
  document.getElementById('story-outline').value = 'Outline text';
  document.getElementById('wizard-next').click();

    await waitFor(() => {
  const list = document.getElementById('character-list');
  expect(list).toBeTruthy();
  expect(list.textContent).toMatch(/Failed to load characters/i);
    });
  });
});
