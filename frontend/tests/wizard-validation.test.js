import { fireEvent, waitFor } from '@testing-library/dom';
import { jest } from '@jest/globals';

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
          <div class="wizard-step" data-step="0">Basics</div>
          <div class="wizard-step" data-step="1">Characters</div>
          <div class="wizard-step" data-step="2">Options</div>
          <div class="wizard-step" data-step="3">Review</div>
        </div>
        <form id="story-creation-form">
          <div id="step-0-basics" class="wizard-step-panel">
            <input type="text" id="story-title" />
            <select id="story-genre"><option value="">Select…</option><option value="Fantasy">Fantasy</option></select>
            <textarea id="story-outline"></textarea>
          </div>
          <div id="step-1-characters" class="wizard-step-panel" style="display:none;">
            <fieldset id="main-characters-fieldset">
              <input class="char-name" id="char-name-1" value="" />
              <select id="char-gender-1"><option value="">Select…</option><option value="female">Female</option></select>
            </fieldset>
            <button type="button" id="add-character-button">Add Another Character</button>
          </div>
          <div id="step-2-options" class="wizard-step-panel" style="display:none;">
            <input id="story-num-pages" type="number" value="" />
            <select id="story-image-style"><option value="">Select…</option><option value="Cartoon">Cartoon</option></select>
            <select id="story-word-to-picture-ratio"><option value="">Select…</option><option value="One image per page">One image per page</option></select>
            <select id="story-text-density"><option value="">Select…</option><option value="Concise (~30-50 words)">Concise (~30-50 words)</option></select>
          </div>
          <div id="step-3-review" class="wizard-step-panel" style="display:none;"><div id="review-container"></div></div>
          <div class="wizard-nav">
            <button type="button" id="wizard-prev">Back</button>
            <button type="button" id="wizard-next">Next</button>
            <button type="submit" id="generate-story-button" style="display:none;">Generate Story</button>
          </div>
        </form>
      </section>
      <section id="story-preview-section" style="display:none;"></section>
      <section id="browse-stories-section" style="display:none;"></section>
      <section id="characters-section" style="display:none;"></section>
      <div id="snackbar" style="display:none;"></div>
      <section id="message-area"><p id="api-message"></p></section>
    </main>`;
}

describe('wizard required-field validation', () => {
    beforeEach(async () => {
        window.localStorage.setItem('authToken', 't');
        mountWizardDom();
        // Mock dynamic lists requests that may occur on init
        global.fetch = jest.fn(async (url) => {
            const u = String(url);
            if (u.includes('/api/v1/dynamic-lists/genres')) {
                return { ok: true, status: 200, json: async () => [{ item_value: 'Fantasy', item_label: 'Fantasy' }], headers: { get: () => 'application/json' } };
            }
            if (u.includes('/api/v1/dynamic-lists/image_styles')) {
                return { ok: true, status: 200, json: async () => [{ item_value: 'Cartoon', item_label: 'Cartoon' }], headers: { get: () => 'application/json' } };
            }
            if (u.includes('/api/v1/dynamic-lists/word_to_picture_ratio')) {
                return { ok: true, status: 200, json: async () => [{ item_value: 'One image per page', item_label: 'One image per page' }], headers: { get: () => 'application/json' } };
            }
            if (u.includes('/api/v1/dynamic-lists/text_density')) {
                return { ok: true, status: 200, json: async () => [{ item_value: 'Concise (~30-50 words)', item_label: 'Concise (~30-50 words)' }], headers: { get: () => 'application/json' } };
            }
            if (u.includes('/api/v1/dynamic-lists/genders')) {
                return { ok: true, status: 200, json: async () => [{ item_value: 'female', item_label: 'Female' }], headers: { get: () => 'application/json' } };
            }
            return { ok: true, status: 200, json: async () => ({}), headers: { get: () => 'application/json' } };
        });
        await import('../../frontend/script.js');
        document.dispatchEvent(new Event('DOMContentLoaded'));
        // Ensure we are on the creation section
        document.getElementById('nav-create-story').click();
        // Allow populateAllDropdowns async tasks to settle
        await new Promise(r => setTimeout(r, 0));
        await waitFor(() => {
            expect(document.getElementById('step-0-basics').style.display).toBe('block');
        });
    });

    test('step 0: missing genre/outline blocks Next and shows warning', () => {
        const next = document.getElementById('wizard-next');
        // Ensure fields are empty/missing
        document.getElementById('story-genre').value = '';
        document.getElementById('story-outline').value = '';

        fireEvent.click(next);

        // Should remain on step 0
        expect(document.getElementById('step-1-characters').style.display).toBe('none');
        // Warning shown
        const snackbar = document.getElementById('snackbar');
        expect(snackbar.style.display).toBe('block');
        expect(snackbar.textContent).toMatch(/please select a genre/i);
    });

    test('step 1: no character names blocks Next', () => {
        const next = document.getElementById('wizard-next');
        // Make step 0 valid, then go to step 1
        document.getElementById('story-genre').value = 'Fantasy';
        document.getElementById('story-outline').value = 'Outline';
        fireEvent.click(next); // to step 1
        expect(document.getElementById('step-1-characters').style.display).toBe('block');

        // Ensure name empty
        document.getElementById('char-name-1').value = '';
        fireEvent.click(next);

        // Should remain on step 1
        expect(document.getElementById('step-2-options').style.display).toBe('none');
        const snackbar = document.getElementById('snackbar');
        expect(snackbar.style.display).toBe('block');
        expect(snackbar.textContent).toMatch(/add at least one character name/i);
    });

    test('step 2: missing options block Next', () => {
        const next = document.getElementById('wizard-next');
        // Step 0 valid
        document.getElementById('story-genre').value = 'Fantasy';
        document.getElementById('story-outline').value = 'Outline';
        fireEvent.click(next); // -> step 1
        // Provide a character name
        document.getElementById('char-name-1').value = 'Alice';
        fireEvent.click(next); // -> step 2
        expect(document.getElementById('step-2-options').style.display).toBe('block');

        // Clear required options
        document.getElementById('story-num-pages').value = '';
        document.getElementById('story-image-style').value = '';
        document.getElementById('story-word-to-picture-ratio').value = '';
        document.getElementById('story-text-density').value = '';

        fireEvent.click(next);
        // Should remain on step 2
        expect(document.getElementById('step-3-review').style.display).toBe('none');
        const snackbar = document.getElementById('snackbar');
        expect(snackbar.style.display).toBe('block');
        expect(snackbar.textContent).toMatch(/please complete options/i);
    });
});
