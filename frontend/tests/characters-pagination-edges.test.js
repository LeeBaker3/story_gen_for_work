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
        <button id="export-pdf-button" style="display:none;">Export</button>
        <form id="story-creation-form"></form>
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
          <div class="modal-content" data-status-region="true">
            <button type="button" id="char-modal-close"></button>
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

describe('characters pagination edges', () => {
    beforeEach(async () => {
        mountCharactersPageDom();
        window.localStorage.setItem('authToken', 't');

        const page1 = { total: 1, items: [{ id: 1, name: 'Alpha' }] };

        global.fetch = jest.fn(async (url) => {
            const u = String(url);
            if (u.includes('/api/v1/characters')) {
                return { ok: true, status: 200, json: async () => page1, headers: { get: () => 'application/json' } };
            }
            if (u.includes('/api/v1/dynamic-lists/')) {
                return { ok: true, status: 200, json: async () => [], headers: { get: () => 'application/json' } };
            }
            return { ok: true, status: 200, json: async () => ({}), headers: { get: () => 'application/json' } };
        });

        await import('../../frontend/script.js');
        document.dispatchEvent(new Event('DOMContentLoaded'));
        // Navigate to characters page
        document.getElementById('nav-characters').click();
    });

    test('Prev disabled on first page, Next disabled on last page; clicks don\'t go out of range', async () => {
        await waitFor(() => {
            const pag = document.getElementById('characters-page-pagination');
            expect(pag).toBeTruthy();
            expect(pag.textContent).toMatch(/Page 1 of 1/);
        });

        const prevBtn = document.getElementById('characters-page-prev');
        const nextBtn = document.getElementById('characters-page-next');
        expect(prevBtn.disabled).toBe(true);
        expect(nextBtn.disabled).toBe(true);

        // Clicking should not trigger any additional fetch for out-of-range
        const callsBefore = (global.fetch.mock.calls || []).length;
        fireEvent.click(prevBtn);
        fireEvent.click(nextBtn);
        const callsAfter = (global.fetch.mock.calls || []).length;
        expect(callsAfter).toBe(callsBefore); // no new fetch from disabled buttons
    });
});
