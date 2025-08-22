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
        <button id="nav-characters" class="nav-button" style="display:none;">Characters</button>
        <a id="nav-admin-panel" href="#" class="nav-button" style="display:none;">Admin Panel</a>
        <button id="nav-logout" class="nav-button" style="display:none;">Logout</button>
      </div>
    </nav>
  </header>
  <main>
    <section id="auth-section" style="display:none;"></section>
    <section id="story-creation-section" style="display:none;">
      <!-- Provide fieldset to avoid critical console errors in script wiring -->
      <div id="main-characters-fieldset"></div>
    </section>
    <section id="story-preview-section" style="display:none;"></section>
    <section id="browse-stories-section" style="display:none;"></section>
    <section id="characters-section" style="display:block;">
      <input id="characters-page-search" />
      <div id="characters-page-list"></div>
      <div id="characters-page-pagination"></div>
      <div id="char-modal-backdrop" class="modal-backdrop" aria-hidden="true"></div>
      <div id="char-modal" class="modal" role="dialog">
        <div class="modal-content">
          <div class="modal-actions">
            <button type="button" id="char-modal-regenerate"></button>
            <button type="button" id="char-modal-duplicate"></button>
            <button type="button" id="char-modal-save"></button>
          </div>
          <div id="char-modal-status" class="inline-status" style="display:none;"></div>
        </div>
      </div>
    </section>
    <div id="snackbar" style="display:none;"></div>
  </main>`;
}

describe('characters page search debounce and focus', () => {
  beforeEach(async () => {
    mountCharactersPageDom();
    window.localStorage.setItem('authToken', 't');

    // Track characters endpoint calls and echo back params
    global.fetch = jest.fn(async (url) => {
      const u = String(url);
      if (u.includes('/api/v1/dynamic-lists/')) {
        return { ok: true, status: 200, json: async () => [], headers: { get: () => 'application/json' } };
      }
      if (u.match(/\/api\/v1\/characters\/?\?page=/)) {
        const qs = u.split('?')[1] || '';
        const params = new URLSearchParams(qs);
        const page = Number(params.get('page') || '1');
        const q = params.get('q') || '';
        // large total so pagination exists if needed
        return {
          ok: true,
          status: 200,
          json: async () => ({ total: 100, items: [{ id: page, name: q ? `Result ${q}` : `Item ${page}`, thumbnail_path: null }] }),
          headers: { get: () => 'application/json' },
        };
      }
      return { ok: true, status: 200, json: async () => ({}), headers: { get: () => 'application/json' } };
    });

    await import('../../frontend/script.js');
    document.dispatchEvent(new Event('DOMContentLoaded'));
    // Navigate to characters page to trigger initial load
    document.getElementById('nav-characters').click();
    // Wait initial render for pagination controls
    await waitFor(() => {
      expect(document.getElementById('characters-page-pagination')).toBeTruthy();
    });
  });

  test('debounced search triggers a single fetch and resets page to 1', async () => {
    jest.useFakeTimers();
    const search = document.getElementById('characters-page-search');

    // Move to page 3 first (to verify reset)
    const next = document.getElementById('characters-page-next');
    fireEvent.click(next);
    fireEvent.click(next);

    const callsBefore = (global.fetch.mock.calls || []).length;

    // Rapid inputs within debounce window
    search.value = 'a';
    fireEvent.input(search);
    jest.advanceTimersByTime(100);
    search.value = 'al';
    fireEvent.input(search);
    jest.advanceTimersByTime(100);
    search.value = 'alp';
    fireEvent.input(search);

    // Still within < 300ms since last input: no new fetch yet
    const interimCalls = (global.fetch.mock.calls || []).length;
    expect(interimCalls).toBe(callsBefore);

    // Let debounce fire
    jest.advanceTimersByTime(300);

    // One debounced fetch should have occurred
    await waitFor(() => {
      const after = (global.fetch.mock.calls || []).length;
      expect(after).toBe(callsBefore + 1);
    });

    // Validate last request has q=alp and page=1
    const lastCallUrl = String(global.fetch.mock.calls[global.fetch.mock.calls.length - 1][0]);
    expect(lastCallUrl).toMatch(/q=alp/);
    expect(lastCallUrl).toMatch(/page=1(?!\d)/);

    jest.useRealTimers();
  });

  test('search input retains focus after debounced refresh', async () => {
    jest.useFakeTimers();
    const search = document.getElementById('characters-page-search');
    search.focus();

    search.value = 'focus';
    fireEvent.input(search);
    jest.advanceTimersByTime(300);

    await waitFor(() => {
      expect(document.activeElement).toBe(search);
    });

    jest.useRealTimers();
  });
});
