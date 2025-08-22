import { fireEvent, waitFor } from '@testing-library/dom';
import { jest } from '@jest/globals';

function mountWizardDom() {
  document.body.innerHTML = `
  <header>
    <nav>
      <div class="nav-buttons">
        <button id="nav-login-signup" class="nav-button">Login / Sign Up</button>
        <button id="nav-create-story" class="nav-button">Create New Story</button>
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
        <select id="story-genre"><option value="">Select</option><option value="fantasy">Fantasy</option></select>
        <textarea id="story-outline"></textarea>
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

    <section id="story-preview-section" style="display:none;"></section>
    <section id="browse-stories-section" style="display:none;"></section>
    <section id="characters-section" style="display:none;"></section>
    <div id="snackbar" style="display:none;"></div>
  </main>`;
}

describe('wizard character library search debounce', () => {
  beforeEach(async () => {
    mountWizardDom();
    window.localStorage.setItem('authToken', 't');

    // Mock fetch for dynamic lists and characters
    global.fetch = jest.fn(async (url) => {
      const u = String(url);
      if (u.includes('/api/v1/dynamic-lists/')) {
        // Return simple arrays for any list
        return { ok: true, status: 200, json: async () => ([{ value: 'fantasy', label: 'Fantasy' }]), headers: { get: () => 'application/json' } };
      }
      if (u.match(/\/api\/v1\/characters\/?\?page=/)) {
        const qs = u.split('?')[1] || '';
        const params = new URLSearchParams(qs);
        const page = Number(params.get('page') || '1');
        const q = params.get('q') || '';
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
    // Enter the create story flow
    document.getElementById('nav-create-story').click();

    // Fill required basics so Next is allowed
    const genre = document.getElementById('story-genre');
    const outline = document.getElementById('story-outline');
    if (genre) genre.value = 'fantasy';
    if (outline) outline.value = 'An outline';

    // Move to step 1 (Characters) to initialize the library and perform initial load
    document.getElementById('wizard-next').click();

    await waitFor(() => {
      // Pagination should be rendered by initial load
      const pag = document.getElementById('character-pagination');
      expect(pag).toBeTruthy();
      expect(pag.textContent || '').toContain('Page 1');
    });
  });

  test('debounced library search triggers a single fetch and resets to page=1', async () => {
    jest.useFakeTimers();

    // Advance to page 3 first to verify reset on search
    const nextBtn = () => document.querySelector('#character-pagination #lib-next');
    fireEvent.click(nextBtn());
    fireEvent.click(nextBtn());

    const callsBefore = (global.fetch.mock.calls || []).length;

    const search = document.getElementById('character-search');
    search.value = 'r';
    fireEvent.input(search);
    jest.advanceTimersByTime(100);
    search.value = 'ro';
    fireEvent.input(search);
    jest.advanceTimersByTime(100);
    search.value = 'robin';
    fireEvent.input(search);

    // Still within debounce window; no new fetch expected yet
    expect((global.fetch.mock.calls || []).length).toBe(callsBefore);

    // Let debounce fire
    jest.advanceTimersByTime(300);

    await waitFor(() => {
      const after = (global.fetch.mock.calls || []).length;
      expect(after).toBe(callsBefore + 1);
    });

    const lastUrl = String(global.fetch.mock.calls[global.fetch.mock.calls.length - 1][0]);
    expect(lastUrl).toMatch(/q=robin/);
    expect(lastUrl).toMatch(/page=1(?!\d)/);

    jest.useRealTimers();
  });
});
