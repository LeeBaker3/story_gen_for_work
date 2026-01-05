import { fireEvent, waitFor } from '@testing-library/dom';
import { jest } from '@jest/globals';

function mountDom() {
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
    <section id="story-creation-section" style="display:none;"><div id="main-characters-fieldset"></div></section>
    <section id="story-preview-section" style="display:none;"></section>
    <section id="browse-stories-section" style="display:none;"></section>
    <section id="characters-section" style="display:block;">
      <button type="button" id="characters-page-new">New Character</button>
      <div id="characters-page-list"></div>
      <div id="characters-page-pagination"></div>
      <div id="char-modal-backdrop" class="modal-backdrop" aria-hidden="true"></div>
      <div id="char-modal" class="modal" role="dialog">
        <div class="modal-content" data-status-region="true">
          <div class="modal-header">
            <h3 id="char-modal-title"></h3>
            <button type="button" id="char-modal-close">Close</button>
          </div>
          <div class="modal-body">
            <div id="char-modal-wizard" style="display:none;">
              <div id="char-wizard-steps">
                <div class="wizard-step" data-step="0">Create</div>
                <div class="wizard-step" data-step="1">Upload</div>
                <div class="wizard-step" data-step="2">Describe</div>
                <div class="wizard-step" data-step="3">Generate</div>
              </div>
              <div id="char-wizard-panel-0"><input id="char-wizard-name" /></div>
              <div id="char-wizard-panel-1" style="display:none;">
                <input id="char-wizard-photo" type="file" />
                <img id="char-wizard-photo-preview" style="display:none;" />
              </div>
              <div id="char-wizard-panel-2" style="display:none;">
                <textarea id="char-wizard-desc"></textarea>
                <select id="char-wizard-style"><option value="Cartoon">Cartoon</option></select>
              </div>
              <div id="char-wizard-panel-3" style="display:none;">
                <img id="char-wizard-generated-image" style="display:none;" />
              </div>
              <button id="char-wizard-prev" type="button">Back</button>
              <button id="char-wizard-next" type="button">Next</button>
            </div>
            <div id="char-modal-edit-form"></div>
          </div>
          <div class="modal-actions"></div>
          <div id="char-modal-status" class="inline-status" style="display:none;"></div>
          <select id="modal-char-gender"></select>
          <select id="modal-char-style"></select>
        </div>
      </div>
    </section>
    <div id="snackbar" style="display:none;"></div>
  </main>`;
}

describe('new character wizard: create -> upload -> describe -> generate', () => {
    beforeEach(async () => {
        mountDom();
        window.localStorage.setItem('authToken', 't');

        // Polyfill object URL APIs used for local preview.
        global.URL.createObjectURL = jest.fn(() => 'blob:preview');
        global.URL.revokeObjectURL = jest.fn();

        global.fetch = jest.fn(async (url, opts) => {
            const u = String(url);
            // Style list population
            if (u.endsWith('/api/v1/dynamic-lists/image_styles/active-items')) {
                return {
                    ok: true,
                    status: 200,
                    json: async () => [{ item_value: 'Cartoon', item_label: 'Cartoon' }],
                    headers: { get: () => 'application/json' },
                };
            }
            if (u.endsWith('/api/v1/characters/') && opts?.method === 'POST') {
                return { ok: true, status: 201, json: async () => ({ id: 7, name: 'Alice' }), headers: { get: () => 'application/json' } };
            }
            if (u.includes('/api/v1/characters/7/photo') && opts?.method === 'POST') {
                // Should be FormData
                return { ok: true, status: 200, json: async () => ({ character_id: 7, size_bytes: 6, content_type: 'image/png' }), headers: { get: () => 'application/json' } };
            }
            if (u.endsWith('/api/v1/characters/7') && opts?.method === 'PUT') {
                return { ok: true, status: 200, json: async () => ({ id: 7 }), headers: { get: () => 'application/json' } };
            }
            if (u.includes('/api/v1/characters/7/generate-from-photo') && opts?.method === 'POST') {
                return {
                    ok: true,
                    status: 200,
                    json: async () => ({ id: 7, current_image: { file_path: 'images/user_1/characters/7/abc.png' } }),
                    headers: { get: () => 'application/json' },
                };
            }
            return { ok: true, status: 200, json: async () => ({}), headers: { get: () => 'application/json' } };
        });

        await import('../../frontend/script.js');
        document.dispatchEvent(new Event('DOMContentLoaded'));
    });

    test('walks through steps and shows generated image', async () => {
        // Open wizard
        fireEvent.click(document.getElementById('characters-page-new'));

        await waitFor(() => {
            expect(document.getElementById('char-modal-wizard').style.display).not.toBe('none');
        });

        // Step 1: create
        const nameInput = document.getElementById('char-wizard-name');
        nameInput.value = 'Alice';
        fireEvent.input(nameInput);
        fireEvent.click(document.getElementById('char-wizard-next'));

        await waitFor(() => {
            const calledCreate = (global.fetch.mock.calls || []).some(([url, opts]) => String(url).endsWith('/api/v1/characters/') && opts?.method === 'POST');
            expect(calledCreate).toBe(true);
        });

        // Ensure we are on the Upload step (Create may still be finishing async work).
        await waitFor(() => {
            const nextBtn = document.getElementById('char-wizard-next');
            expect(nextBtn.textContent.toLowerCase()).toContain('upload');
            expect(nextBtn.disabled).toBe(false);
        });

        // Step 2: upload photo
        const file = new File([new Uint8Array([1, 2, 3])], 'photo.png', { type: 'image/png' });
        const photoInput = document.getElementById('char-wizard-photo');
        // jsdom doesn't reliably update input.files via fireEvent.change; define it.
        Object.defineProperty(photoInput, 'files', { value: [file] });
        fireEvent.change(photoInput);

        fireEvent.click(document.getElementById('char-wizard-next'));

        await waitFor(() => {
            const call = (global.fetch.mock.calls || []).find(([url, opts]) => String(url).includes('/api/v1/characters/7/photo') && opts?.method === 'POST');
            expect(call).toBeTruthy();
            expect(call[1].body).toBeInstanceOf(FormData);
        });

        // Wait for the wizard to advance to Describe (step 2) before clicking Next again.
        await waitFor(() => {
            const activeStep = document.querySelector('#char-wizard-steps .wizard-step.active');
            expect(activeStep?.getAttribute('data-step')).toBe('2');
            const nextBtn = document.getElementById('char-wizard-next');
            expect(nextBtn.disabled).toBe(false);
            expect(nextBtn.textContent.toLowerCase()).toContain('next');
        });

        // Step 3: describe
        const desc = document.getElementById('char-wizard-desc');
        desc.value = 'A brave knight';
        fireEvent.input(desc);
        fireEvent.click(document.getElementById('char-wizard-next'));

        await waitFor(() => {
            const calledPut = (global.fetch.mock.calls || []).some(([url, opts]) => String(url).includes('/api/v1/characters/7') && opts?.method === 'PUT');
            expect(calledPut).toBe(true);
        });

        // Ensure we advanced to Generate step after saving.
        await waitFor(() => {
            const activeStep = document.querySelector('#char-wizard-steps .wizard-step.active');
            expect(activeStep?.getAttribute('data-step')).toBe('3');
            expect(document.getElementById('char-wizard-next').textContent.toLowerCase()).toContain('generate');
        });

        // Step 4: generate
        fireEvent.click(document.getElementById('char-wizard-next'));

        await waitFor(() => {
            const calledGen = (global.fetch.mock.calls || []).some(([url, opts]) => String(url).includes('/api/v1/characters/7/generate-from-photo') && opts?.method === 'POST');
            expect(calledGen).toBe(true);
        });

        const img = document.getElementById('char-wizard-generated-image');
        await waitFor(() => {
            expect(img.style.display).not.toBe('none');
          expect(img.getAttribute('src')).toContain('http://127.0.0.1:8000/static_content/images/user_1/characters/7/abc.png');
        });
    });
});
