import { fireEvent } from '@testing-library/dom';

function mountWizardWithModal() {
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
          <button type="button" class="wizard-step" data-step="0" aria-current="step">Basics</button>
          <button type="button" class="wizard-step" data-step="1" aria-disabled="true">Characters</button>
          <button type="button" class="wizard-step" data-step="2" aria-disabled="true">Options</button>
          <button type="button" class="wizard-step" data-step="3" aria-disabled="true">Review</button>
        </div>
        <form id="story-creation-form">
          <div id="step-0-basics" class="wizard-step-panel">
            <select id="story-genre"><option>Fantasy</option></select>
            <textarea id="story-outline">Outline</textarea>
          </div>
          <div id="step-1-characters" class="wizard-step-panel" style="display:none;"></div>
          <div id="step-2-options" class="wizard-step-panel" style="display:none;">
            <input id="story-num-pages" value="5" />
            <select id="story-image-style"><option>Cartoon</option></select>
            <select id="story-word-to-picture-ratio"><option>One image per page</option></select>
            <select id="story-text-density"><option>Concise (~30-50 words)</option></select>
          </div>
          <div id="step-3-review" class="wizard-step-panel" style="display:none;"></div>
          <div class="wizard-nav">
            <button type="button" id="wizard-prev">Back</button>
            <button type="button" id="wizard-next">Next</button>
            <button type="submit" id="generate-story-button" style="display:none;">Generate Story</button>
          </div>
        </form>
      </section>
      <section id="characters-section" style="display:none;">
        <div id="char-modal-backdrop" class="modal-backdrop"></div>
        <div id="char-modal" class="modal"><div class="modal-content"></div></div>
      </section>
      <div id="snackbar" style="display:none;"></div>
    </main>`;
}

describe('wizard step indicator clicks', () => {
    beforeEach(async () => {
        window.localStorage.setItem('authToken', 't');
        mountWizardWithModal();
        await import('../../frontend/script.js');
        document.dispatchEvent(new Event('DOMContentLoaded'));
    });

    test('clicking a reachable step pill navigates and closes any open character modal', () => {
      fireEvent.click(document.getElementById('wizard-next'));

        // Simulate opening modal
        const modal = document.getElementById('char-modal');
        const backdrop = document.getElementById('char-modal-backdrop');
        modal.classList.add('open');
        backdrop.classList.add('open');
        document.body.dataset.charModalState = 'open';

      // Click reachable step 0 pill
      const step0 = Array.from(document.querySelectorAll('#wizard-steps .wizard-step')).find(d => d.getAttribute('data-step') === '0');
      fireEvent.click(step0);

        expect(modal.classList.contains('open')).toBe(false);
        expect(backdrop.classList.contains('open')).toBe(false);
        expect(document.body.dataset.charModalState).toBeUndefined();
      expect(document.getElementById('step-0-basics').style.display).toBe('block');
    });
});
