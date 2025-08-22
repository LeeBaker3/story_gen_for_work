import { fireEvent } from '@testing-library/dom';
import { jest } from '@jest/globals';

// Helper to mount minimal DOM for wizard
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
            <select id="story-genre"><option value="">Select...</option><option value="Fantasy">Fantasy</option></select>
            <input type="text" id="story-tone" />
            <input type="text" id="story-setting" />
            <textarea id="story-outline"></textarea>
          </div>
          <div id="step-1-characters" class="wizard-step-panel" style="display:none;">
            <fieldset id="main-characters-fieldset">
              <input class="char-name" value="Alice" />
              <select id="char-gender-1"><option value="">Select…</option><option value="female">Female</option></select>
            </fieldset>
            <button type="button" id="add-character-button">Add Another Character</button>
          </div>
          <div id="step-2-options" class="wizard-step-panel" style="display:none;">
            <input id="story-num-pages" type="number" value="3" />
            <select id="story-image-style"><option value="">Select...</option><option value="Cartoon">Cartoon</option></select>
            <select id="story-word-to-picture-ratio"><option value="">Select...</option><option value="One image per page">One image per page</option></select>
            <select id="story-text-density"><option value="">Select...</option><option value="Concise (~30-50 words)">Concise (~30-50 words)</option></select>
          </div>
          <div id="step-3-review" class="wizard-step-panel" style="display:none;">
            <div id="review-container"></div>
          </div>
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
    </main>`;
}

describe('wizard navigation', () => {
    beforeEach(async () => {
        // Pretend user is logged in so script shows creation section
        window.localStorage.setItem('authToken', 'test');
        mountWizardDom();
        // Mock dynamic lists to allow selects to have valid options
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
        // Import the script which wires events
        await import('../../frontend/script.js');
        // Trigger DOMContentLoaded for the app to initialize
        document.dispatchEvent(new Event('DOMContentLoaded'));
        // Wait for dropdowns to populate, then set selections needed for validation
        await new Promise(r => setTimeout(r, 0));
        const genreSel = document.getElementById('story-genre');
        const imgStyleSel = document.getElementById('story-image-style');
        const ratioSel = document.getElementById('story-word-to-picture-ratio');
        const densitySel = document.getElementById('story-text-density');
        if (genreSel) genreSel.innerHTML += '<option value="Fantasy">Fantasy</option>';
        if (imgStyleSel) imgStyleSel.innerHTML += '<option value="Cartoon">Cartoon</option>';
        if (ratioSel) ratioSel.innerHTML += '<option value="One image per page">One image per page</option>';
        if (densitySel) densitySel.innerHTML += '<option value="Concise (~30-50 words)">Concise (~30-50 words)</option>';
        // Set values for validations
        document.getElementById('story-genre').value = 'Fantasy';
        document.getElementById('story-outline').value = 'An outline';
        document.getElementById('story-image-style').value = 'Cartoon';
        document.getElementById('story-word-to-picture-ratio').value = 'One image per page';
        document.getElementById('story-text-density').value = 'Concise (~30-50 words)';
    });

    test('Next advances through steps and shows Generate on Review', () => {
        const next = document.getElementById('wizard-next');
        const prev = document.getElementById('wizard-prev');
        const gen = document.getElementById('generate-story-button');

        // Step 0 visible initially (inline style may be empty string before first update)
        expect(document.getElementById('step-0-basics').style.display).not.toBe('none');
        fireEvent.click(next); // to step 1 (characters)
        expect(document.getElementById('step-1-characters').style.display).toBe('block');

        fireEvent.click(next); // to step 2
        expect(document.getElementById('step-2-options').style.display).toBe('block');

        fireEvent.click(next); // to step 3
        expect(document.getElementById('step-3-review').style.display).toBe('block');
        expect(gen.style.display).toBe('inline-block');

        fireEvent.click(prev);
        expect(document.getElementById('step-2-options').style.display).toBe('block');
    });
});
