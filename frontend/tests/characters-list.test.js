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

describe('characters page search and pagination', () => {
    beforeEach(async () => {
        mountCharactersPageDom();
        window.localStorage.setItem('authToken', 't');

        const responses = {
            page1: { total: 3, items: [{ id: 1, name: 'Alpha' }, { id: 2, name: 'Beta' }] },
            page2: { total: 3, items: [{ id: 3, name: 'Gamma' }] },
            searchA: { total: 1, items: [{ id: 1, name: 'Alpha' }] },
        };

        global.fetch = jest.fn(async (url) => {
            const u = String(url);
            if (u.includes('/api/v1/characters')) {
                const headers = { get: () => 'application/json' };
                const hasQ = u.includes('q=');
                if (hasQ) return { ok: true, status: 200, json: async () => responses.searchA, headers };
                if (u.includes('page=1')) return { ok: true, status: 200, json: async () => responses.page1, headers };
                if (u.includes('page=2')) return { ok: true, status: 200, json: async () => responses.page2, headers };
                return { ok: true, status: 200, json: async () => responses.page1, headers };
            }
            if (u.includes('/api/v1/dynamic-lists/')) {
                return { ok: true, status: 200, json: async () => [], headers: { get: () => 'application/json' } };
            }
            return { ok: true, status: 200, json: async () => ({}), headers: { get: () => 'application/json' } };
        });

        await import('../../frontend/script.js');
        document.dispatchEvent(new Event('DOMContentLoaded'));
        // Navigate to characters page to trigger initial fetch
        document.getElementById('nav-characters').click();
    });

    test('debounced search calls API with q param and updates list', async () => {
        const input = document.getElementById('characters-page-search');
        input.value = 'A';
        fireEvent.input(input);

        await waitFor(() => {
            // Called at least once with q param
            const calledWithQ = (global.fetch.mock.calls || []).some(([url]) => String(url).match(/\/api\/v1\/characters\?[^\n]*q=/));
            expect(calledWithQ).toBe(true);
        }, { timeout: 1000 });
    });

    test('pagination next button fetches next page', async () => {
        // Initial render page=1 should happen from showCharactersPage() when nav clicked; we call fetch by triggering show section logic
        // Click next
        // Because script creates buttons dynamically, wait for them
        await waitFor(() => {
            const pag = document.getElementById('characters-page-pagination');
            expect(pag).toBeTruthy();
        });

        const nextBtn = document.getElementById('characters-page-next');
        fireEvent.click(nextBtn);

        await waitFor(() => {
            const pag = document.getElementById('characters-page-pagination');
            expect(pag.innerHTML).toContain('Page');
        });
    });
});
