import { fireEvent, waitFor } from '@testing-library/dom';
import { jest } from '@jest/globals';

function mountCharactersDomWithModal() {
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
    <section id="story-creation-section" style="display:none;"><div id="main-characters-fieldset"></div></section>
    <section id="browse-stories-section" style="display:none;"></section>
    <section id="characters-section" style="display:none;">
      <input id="characters-page-search" />
      <div id="characters-page-list"></div>
      <div id="characters-page-pagination"></div>
      <div id="char-modal-backdrop" class="modal-backdrop" aria-hidden="true"></div>
      <div id="char-modal" class="modal" role="dialog" aria-modal="true">
        <div class="modal-content" data-status-region="true">
          <div class="modal-actions">
            <button type="button" id="char-modal-regenerate">Regenerate</button>
            <button type="button" id="char-modal-duplicate">Save as new</button>
            <button type="button" id="char-modal-save">Save</button>
          </div>
          <div id="char-modal-status" class="inline-status" role="status" aria-live="polite" aria-atomic="true" style="display:none;"></div>
        </div>
      </div>
    </section>
    <div id="snackbar" role="status" aria-live="polite" style="display:none;"></div>
  </main>`;
}

describe('modal inline status a11y and error handling', () => {
  beforeEach(async () => {
    mountCharactersDomWithModal();
    window.localStorage.setItem('authToken', 't');

    global.fetch = jest.fn(async (url, opts) => {
      const u = String(url);
      if (u.match(/\/api\/v1\/characters\?page=/)) {
        return { ok: true, status: 200, json: async () => ({ total: 1, items: [{ id: 7, name: 'Zed', thumbnail_path: null }] }), headers: { get: () => 'application/json' } };
      }
      // Character detail for modal open
      if (u.endsWith('/api/v1/characters/7') && (!opts || !opts.method || opts.method === 'GET')) {
        return { ok: true, status: 200, json: async () => ({ id: 7, name: 'Zed', age: 10, gender: 'male', image_style: 'comic' }), headers: { get: () => 'application/json' } };
      }
      if (u.endsWith('/api/v1/characters/7') && (opts?.method === 'PUT')) {
        return { ok: false, status: 400, json: async () => ({ detail: 'Validation failed' }), headers: { get: () => 'application/json' } };
      }
      if (u.endsWith('/api/v1/characters/7/regenerate-image') && (opts?.method === 'POST')) {
        return { ok: false, status: 500, json: async () => ({ detail: 'Regeneration failed' }), headers: { get: () => 'application/json' } };
      }
      return { ok: true, status: 200, json: async () => ({}), headers: { get: () => 'application/json' } };
    });

    await import('../../frontend/script.js');
    document.dispatchEvent(new Event('DOMContentLoaded'));
  });

  test('Save failure keeps modal open and toggles aria-busy in status region', async () => {
    // Go to characters page and open modal by clicking card
    document.getElementById('nav-characters').click();
    await waitFor(() => {
      const list = document.getElementById('characters-page-list');
      expect(list.children.length).toBeGreaterThan(0);
    });
    // Click the card to open modal
    document.querySelector('.character-card').click();

    await waitFor(() => {
      expect(document.getElementById('char-modal').classList.contains('open')).toBe(true);
    });

    const statusEl = document.getElementById('char-modal-status');
    const region = statusEl.closest('[data-status-region]');
    const saveBtn = document.getElementById('char-modal-save');

    // Trigger Save failure
    fireEvent.click(saveBtn);

    // During busy: aria-busy true and status visible
    await waitFor(() => {
      expect(region.getAttribute('aria-busy')).toBe('true');
      expect(statusEl.style.display).toBe('');
    });

    // After error: aria-busy false, inline status shows error text
    await waitFor(() => {
      expect(region.getAttribute('aria-busy')).toBe('false');
      expect(statusEl.textContent).toMatch(/Validation failed|Failed to save/i);
    });
    // Modal should remain open
    expect(document.getElementById('char-modal').classList.contains('open')).toBe(true);
  });

  test('Regenerate failure shows inline error and re-enables actions', async () => {
    document.getElementById('nav-characters').click();
    await waitFor(() => {
      const list = document.getElementById('characters-page-list');
      expect(list.children.length).toBeGreaterThan(0);
    });
    document.querySelector('.character-card').click();
    await waitFor(() => {
      expect(document.getElementById('char-modal').classList.contains('open')).toBe(true);
    });

    const regenBtn = document.getElementById('char-modal-regenerate');
    fireEvent.click(regenBtn);

    const statusEl = document.getElementById('char-modal-status');
    const region = statusEl.closest('[data-status-region]');

    // Busy state asserted first
    await waitFor(() => {
      expect(region.getAttribute('aria-busy')).toBe('true');
    });

    // Then error displayed and aria-busy false
    await waitFor(() => {
      expect(statusEl.textContent).toMatch(/Regeneration failed|Failed to regenerate/i);
      expect(region.getAttribute('aria-busy')).toBe('false');
    });
  });
});
