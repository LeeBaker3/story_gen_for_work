import { fireEvent, waitFor } from '@testing-library/dom';
import { jest } from '@jest/globals';

function mountCharactersDom() {
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
      <section id="story-creation-section" style="display:none;"></section>
      <section id="story-preview-section" style="display:none;"></section>
      <section id="browse-stories-section" style="display:none;"></section>
      <section id="characters-section">
        <input id="characters-page-search" />
        <button id="characters-page-sync">Sync</button>
        <button id="characters-page-import">Import</button>
        <div id="characters-page-list"></div>
        <div id="characters-page-pagination"></div>
        <div id="char-modal-backdrop" class="modal-backdrop" aria-hidden="true"></div>
        <div id="char-modal" class="modal" role="dialog">
          <div class="modal-content" data-status-region="true">
            <div class="modal-header">
              <h3 id="char-modal-title"></h3>
              <button type="button" id="char-modal-close">Close</button>
            </div>
            <img id="char-modal-image" />
            <div class="modal-actions">
              <button type="button" id="char-modal-regenerate">Regenerate</button>
              <button type="button" id="char-modal-duplicate">Save as new</button>
              <button type="button" id="char-modal-save">Save</button>
            </div>
            <div id="char-modal-status" class="inline-status" style="display:none;"></div>
            <!-- modal form fields used by collectModalPayload -->
            <input id="modal-char-name" />
            <input id="modal-char-age" type="number" />
            <select id="modal-char-gender"></select>
            <textarea id="modal-char-desc"></textarea>
            <textarea id="modal-char-clothing"></textarea>
            <textarea id="modal-char-traits"></textarea>
            <select id="modal-char-style"></select>
          </div>
        </div>
      </section>
      <div id="snackbar" style="display:none;"></div>
    </main>`;
}

describe('characters CRUD via modal', () => {
    beforeEach(async () => {
        mountCharactersDom();
        window.localStorage.setItem('authToken', 't');
        // Default fetch mocks; individual tests may override certain routes
        global.fetch = jest.fn(async (url, opts) => {
            const u = String(url);
            // Dynamic lists for modal populates
            if (u.endsWith('/api/v1/dynamic-lists/genders/active-items')) {
                return { ok: true, status: 200, json: async () => [{ item_value: 'female', item_label: 'Female' }], headers: { get: () => 'application/json' } };
            }
            if (u.endsWith('/api/v1/dynamic-lists/image_styles/active-items')) {
                return { ok: true, status: 200, json: async () => [{ item_value: 'Cartoon', item_label: 'Cartoon' }], headers: { get: () => 'application/json' } };
            }
            // Characters list page
            if (u.match(/\/api\/v1\/characters\/?\?page=/)) {
                return { ok: true, status: 200, json: async () => ({ total: 1, items: [{ id: 1, name: 'Testy', thumbnail_path: null }] }), headers: { get: () => 'application/json' } };
            }
            // Character detail
            if (u.endsWith('/api/v1/characters/1') && (!opts || !opts.method || opts.method === 'GET')) {
                return { ok: true, status: 200, json: async () => ({ id: 1, name: 'Testy', gender: 'female' }), headers: { get: () => 'application/json' } };
            }
            // Fallback generic ok
            return { ok: true, status: 200, json: async () => ({}), headers: { get: () => 'application/json' } };
        });
        await import('../../frontend/script.js');
        document.dispatchEvent(new Event('DOMContentLoaded'));
    });

    test('Save updates character and shows success inline status', async () => {
        const modal = document.getElementById('char-modal');
        const backdrop = document.getElementById('char-modal-backdrop');
        modal.setAttribute('data-id', '1');
        // prefill some values that collectModalPayload will read
        document.getElementById('modal-char-name').value = 'Updated Name';
        document.getElementById('modal-char-age').value = '9';
        // open modal
        backdrop.classList.add('open');
        modal.classList.add('open');

        // Spy on fetch calls to capture PUT
        const originalFetch = global.fetch;
        global.fetch = jest.fn(async (url, opts) => {
            const u = String(url);
            if (u.endsWith('/api/v1/characters/1') && opts?.method === 'PUT') {
                // minimal ok
                return { ok: true, status: 200, json: async () => ({ id: 1 }), headers: { get: () => 'application/json' } };
            }
            // After save, list is refreshed
            if (u.match(/\/api\/v1\/characters\/?\?page=/)) {
                return { ok: true, status: 200, json: async () => ({ total: 1, items: [{ id: 1, name: 'Updated Name', thumbnail_path: null }] }), headers: { get: () => 'application/json' } };
            }
            return originalFetch(url, opts);
        });

        const saveBtn = document.getElementById('char-modal-save');
        const statusEl = document.getElementById('char-modal-status');
        fireEvent.click(saveBtn);

        await waitFor(() => {
            expect(statusEl.style.display).not.toBe('none');
            expect(statusEl.className).toContain('inline-status--info');
        });
        // Success
        await waitFor(() => {
            expect(statusEl.className).toContain('inline-status--success');
            expect(statusEl.textContent).toMatch(/updated/i);
        });
        // Buttons should be enabled after
        const actionButtons = Array.from(document.querySelectorAll('.modal-actions button'));
        expect(actionButtons.every(b => b.disabled === false)).toBe(true);
    });

    test('Duplicate creates new character and shows success inline status', async () => {
        const modal = document.getElementById('char-modal');
        const backdrop = document.getElementById('char-modal-backdrop');
        modal.setAttribute('data-id', '1');
        document.getElementById('modal-char-name').value = 'Copy Name';
        backdrop.classList.add('open');
        modal.classList.add('open');

        const originalFetch = global.fetch;
        let postedBody;
        global.fetch = jest.fn(async (url, opts) => {
            const u = String(url);
            if (u.endsWith('/api/v1/characters/') && opts?.method === 'POST') {
                postedBody = JSON.parse(opts.body);
                return { ok: true, status: 201, json: async () => ({ id: 2 }), headers: { get: () => 'application/json' } };
            }
            if (u.match(/\/api\/v1\/characters\/?\?page=/)) {
                return { ok: true, status: 200, json: async () => ({ total: 2, items: [{ id: 1, name: 'Testy' }, { id: 2, name: 'Copy Name' }] }), headers: { get: () => 'application/json' } };
            }
            return originalFetch(url, opts);
        });

        const dupBtn = document.getElementById('char-modal-duplicate');
        const statusEl = document.getElementById('char-modal-status');
        fireEvent.click(dupBtn);

        await waitFor(() => {
            expect(statusEl.style.display).not.toBe('none');
            expect(statusEl.className).toContain('inline-status--info');
        });
        await waitFor(() => {
            expect(statusEl.className).toContain('inline-status--success');
            expect(statusEl.textContent).toMatch(/created/i);
        });
        expect(postedBody).toBeTruthy();
        expect(postedBody.generate_image).toBe(false);
        expect(postedBody.name).toBe('Copy Name');
    });
});

describe('characters list delete action', () => {
    beforeEach(async () => {
        mountCharactersDom();
        window.localStorage.setItem('authToken', 't');
        // mock list and deletion endpoints
        global.fetch = jest.fn(async (url, opts) => {
            const u = String(url);
            if (u.match(/\/api\/v1\/characters\/?\?page=/)) {
                return { ok: true, status: 200, json: async () => ({ total: 1, items: [{ id: 1, name: 'ToDelete', thumbnail_path: null }] }), headers: { get: () => 'application/json' } };
            }
            if (u.endsWith('/api/v1/characters/1') && opts?.method === 'DELETE') {
                return { ok: true, status: 204, json: async () => ({}), headers: { get: () => 'application/json' } };
            }
            return { ok: true, status: 200, json: async () => ({}), headers: { get: () => 'application/json' } };
        });
        await import('../../frontend/script.js');
        document.dispatchEvent(new Event('DOMContentLoaded'));
    });

    test('delete confirms, calls API, refreshes list, and shows snackbar', async () => {
        // Show characters page which triggers fetchCharactersPage
        const navChars = document.getElementById('nav-characters');
        navChars.click();
        // Wait for list to render
        await waitFor(() => {
            const list = document.getElementById('characters-page-list');
            expect(list.textContent).toMatch(/ToDelete/);
        });

        // confirm() needs to return true
        const confirmSpy = jest.spyOn(window, 'confirm').mockImplementation(() => true);
        // Click delete button inside the card
        const delBtn = document.querySelector('button[data-action="delete"]');
        fireEvent.click(delBtn);

        // After deletion flow, snackbar should show success message
        const snackbar = document.getElementById('snackbar');
        await waitFor(() => {
            expect(snackbar.style.display).toBe('block');
            expect(snackbar.textContent).toMatch(/deleted/i);
        });
        confirmSpy.mockRestore();
    });
});
