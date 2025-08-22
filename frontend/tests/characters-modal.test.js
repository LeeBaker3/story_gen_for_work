import { fireEvent, screen, waitFor } from '@testing-library/dom';
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
            <select id="modal-char-gender"></select>
            <select id="modal-char-style"></select>
          </div>
        </div>
      </section>
      <div id="snackbar" style="display:none;"></div>
    </main>`;
}

describe('characters modal regenerate inline status', () => {
    beforeEach(async () => {
        mountCharactersDom();
        window.localStorage.setItem('authToken', 't');
        // Mock API responses used by modal flow
        let getDetailCount = 0;
        global.fetch = jest.fn(async (url, opts) => {
            const u = String(url);
            if (u.endsWith('/api/v1/dynamic-lists/genders/active-items')) {
                return { ok: true, status: 200, json: async () => [{ item_value: 'female', item_label: 'Female' }], headers: { get: () => 'application/json' } };
            }
            if (u.endsWith('/api/v1/dynamic-lists/image_styles/active-items')) {
                return { ok: true, status: 200, json: async () => [{ item_value: 'Cartoon', item_label: 'Cartoon' }], headers: { get: () => 'application/json' } };
            }
            if (u.match(/\/api\/v1\/characters\/?\?page=/)) {
                return { ok: true, status: 200, json: async () => ({ total: 1, items: [{ id: 1, name: 'Testy', thumbnail_path: null }] }), headers: { get: () => 'application/json' } };
            }
            if (u.endsWith('/api/v1/characters/1') && (!opts || opts.method === undefined)) {
                // GET detail
                getDetailCount += 1;
                return { ok: true, status: 200, json: async () => ({ id: 1, name: 'Testy', current_image: null }), headers: { get: () => 'application/json' } };
            }
            if (u.endsWith('/api/v1/characters/1/regenerate-image') && opts?.method === 'POST') {
                // Simulate slight delay
                await new Promise(r => setTimeout(r, 5));
                return { ok: true, status: 200, json: async () => ({}), headers: { get: () => 'application/json' } };
            }
            return { ok: true, status: 200, json: async () => ({}), headers: { get: () => 'application/json' } };
        });
        await import('../../frontend/script.js');
        document.dispatchEvent(new Event('DOMContentLoaded'));
    });

    test('shows busy status and disables buttons during regenerate', async () => {
        // Open modal directly using the exported function path via global (script attaches to window listeners only),
        // Instead, simulate clicking on a character card rendering sequence by invoking fetchCharactersPage indirectly:
        // We'll just manually set modal attrs and open it like the code does.
        const modal = document.getElementById('char-modal');
        const backdrop = document.getElementById('char-modal-backdrop');
        modal.setAttribute('data-id', '1');
        backdrop.classList.add('open');
        modal.classList.add('open');

        const regenBtn = document.getElementById('char-modal-regenerate');
        const statusEl = document.getElementById('char-modal-status');

        // Click regenerate
        fireEvent.click(regenBtn);

        // Busy state appears (display becomes visible from none)
        await waitFor(() => {
            expect(statusEl.style.display).not.toBe('none');
            expect(statusEl.className).toContain('inline-status--info');
        });

        // Buttons disabled while busy
        const actionButtons = Array.from(document.querySelectorAll('.modal-actions button'));
        expect(actionButtons.every(b => b.disabled)).toBe(true);

        // After request completes, re-enabled and success message
        await waitFor(() => {
            expect(actionButtons.every(b => b.disabled)).toBe(false);
            expect(statusEl.className).toContain('inline-status--success');
        });
    });
});
