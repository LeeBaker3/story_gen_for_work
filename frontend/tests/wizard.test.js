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
          <button type="button" class="wizard-step" data-step="0" aria-current="step">Basics</button>
          <button type="button" class="wizard-step" data-step="1" aria-disabled="true">Characters</button>
          <button type="button" class="wizard-step" data-step="2" aria-disabled="true">Options</button>
          <button type="button" class="wizard-step" data-step="3" aria-disabled="true">Review</button>
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
            <select id="story-default-text-position"><option value="">Select...</option></select>
            <select id="story-default-font-family"><option value="">Select...</option></select>
            <input id="story-default-font-size" type="number" value="28" />
            <input id="story-default-font-color" type="color" value="#ffffff" />
            <input id="story-default-text-box-opacity" type="range" min="0" max="1" step="0.1" value="0.6" />
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
        <div id="generation-progress-area" style="display:none;">
          <p id="generation-status-message"></p>
          <div id="generation-progress-bar"></div>
        </div>
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
      if (u.includes('/api/v1/dynamic-lists/text_positions')) {
        return { ok: true, status: 200, json: async () => [{ item_value: 'top', item_label: 'Top' }, { item_value: 'bottom', item_label: 'Bottom' }], headers: { get: () => 'application/json' } };
      }
      if (u.includes('/api/v1/dynamic-lists/font_families')) {
        return { ok: true, status: 200, json: async () => [{ item_value: 'storybook', item_label: 'Storybook' }, { item_value: 'classic', item_label: 'Classic' }], headers: { get: () => 'application/json' } };
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
    const textPositionSel = document.getElementById('story-default-text-position');
    const fontFamilySel = document.getElementById('story-default-font-family');
    if (genreSel) genreSel.innerHTML += '<option value="Fantasy">Fantasy</option>';
    if (imgStyleSel) imgStyleSel.innerHTML += '<option value="Cartoon">Cartoon</option>';
    if (ratioSel) ratioSel.innerHTML += '<option value="One image per page">One image per page</option>';
    if (densitySel) densitySel.innerHTML += '<option value="Concise (~30-50 words)">Concise (~30-50 words)</option>';
    if (textPositionSel && !textPositionSel.querySelector('option[value="top"]')) {
      textPositionSel.innerHTML += '<option value="top">Top</option><option value="bottom">Bottom</option>';
    }
    if (fontFamilySel && !fontFamilySel.querySelector('option[value="classic"]')) {
      fontFamilySel.innerHTML += '<option value="storybook">Storybook</option><option value="classic">Classic</option>';
    }
    // Set values for validations
    document.getElementById('story-genre').value = 'Fantasy';
    document.getElementById('story-outline').value = 'An outline';
    document.getElementById('story-image-style').value = 'Cartoon';
    document.getElementById('story-word-to-picture-ratio').value = 'One image per page';
    document.getElementById('story-text-density').value = 'Concise (~30-50 words)';
  });

  test('layout dropdowns load from dynamic lists', () => {
    const textPositionSel = document.getElementById('story-default-text-position');
    const fontFamilySel = document.getElementById('story-default-font-family');

    expect(textPositionSel.querySelector('option[value="top"]')).not.toBeNull();
    expect(textPositionSel.value).toBe('bottom');
    expect(fontFamilySel.querySelector('option[value="classic"]')).not.toBeNull();
    expect(fontFamilySel.value).toBe('storybook');
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

  test('step pills expose current and disabled state as steps become reachable', () => {
    const steps = Array.from(document.querySelectorAll('#wizard-steps .wizard-step'));
    const next = document.getElementById('wizard-next');

    expect(steps[0].getAttribute('aria-current')).toBe('step');
    expect(steps[1].hasAttribute('aria-current')).toBe(false);
    expect(steps[1].getAttribute('aria-disabled')).toBe('true');
    expect(steps[2].getAttribute('aria-disabled')).toBe('true');

    fireEvent.click(next);

    expect(steps[0].hasAttribute('aria-current')).toBe(false);
    expect(steps[0].hasAttribute('aria-disabled')).toBe(false);
    expect(steps[1].getAttribute('aria-current')).toBe('step');
    expect(steps[1].hasAttribute('aria-disabled')).toBe(false);
    expect(steps[2].getAttribute('aria-disabled')).toBe('true');
  });

  test('future step pills do not activate until they are reachable', () => {
    const steps = Array.from(document.querySelectorAll('#wizard-steps .wizard-step'));

    fireEvent.click(steps[2]);
    expect(document.getElementById('step-0-basics').style.display).not.toBe('none');
    expect(steps[0].getAttribute('aria-current')).toBe('step');

    fireEvent.click(document.getElementById('wizard-next'));
    fireEvent.click(steps[0]);

    expect(document.getElementById('step-0-basics').style.display).toBe('block');
    expect(steps[0].getAttribute('aria-current')).toBe('step');
  });

  test('added character row can be removed', () => {
    const addButton = document.getElementById('add-character-button');

    fireEvent.click(addButton);

    expect(document.getElementById('char-name-2')).not.toBeNull();

    const removeButton = document.querySelector('.remove-character-button');
    expect(removeButton).not.toBeNull();

    fireEvent.click(removeButton);

    expect(document.getElementById('char-name-2')).toBeNull();
    expect(document.querySelector('.remove-character-button')).toBeNull();
  });

  test('generate request includes wizard editor settings', async () => {
    document.getElementById('story-default-text-position').value = 'top';
    document.getElementById('story-default-font-family').value = 'classic';
    document.getElementById('story-default-font-size').value = '34';
    document.getElementById('story-default-font-color').value = '#112233';
    document.getElementById('story-default-text-box-opacity').value = '0.4';

    const next = document.getElementById('wizard-next');
    fireEvent.click(next);
    fireEvent.click(next);
    fireEvent.click(next);

    const fetchMock = global.fetch;
    fetchMock.mockImplementation(async (url, options = {}) => {
      const u = String(url);
      if (u.includes('/api/v1/stories/') && options.method === 'POST') {
        return {
          ok: true,
          status: 200,
          json: async () => ({ id: 'task-1', status: 'queued' }),
          headers: { get: () => 'application/json' },
        };
      }
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
      if (u.includes('/api/v1/dynamic-lists/text_positions')) {
        return { ok: true, status: 200, json: async () => [{ item_value: 'top', item_label: 'Top' }, { item_value: 'bottom', item_label: 'Bottom' }], headers: { get: () => 'application/json' } };
      }
      if (u.includes('/api/v1/dynamic-lists/font_families')) {
        return { ok: true, status: 200, json: async () => [{ item_value: 'storybook', item_label: 'Storybook' }, { item_value: 'classic', item_label: 'Classic' }], headers: { get: () => 'application/json' } };
      }
      if (u.includes('/api/v1/dynamic-lists/genders')) {
        return { ok: true, status: 200, json: async () => [{ item_value: 'female', item_label: 'Female' }], headers: { get: () => 'application/json' } };
      }
      if (u.includes('/api/v1/stories/generation-status/task-1')) {
        return {
          ok: true,
          status: 200,
          json: async () => ({ status: 'failed', last_error: 'stop polling in test' }),
          headers: { get: () => 'application/json' },
        };
      }
      return { ok: true, status: 200, json: async () => ({}), headers: { get: () => 'application/json' } };
    });

    fireEvent.click(document.getElementById('generate-story-button'));
    await new Promise(r => setTimeout(r, 0));

    const storyRequest = fetchMock.mock.calls.find(([url, options]) => String(url).includes('/api/v1/stories/') && options?.method === 'POST');
    expect(storyRequest).toBeTruthy();

    const [, requestOptions] = storyRequest;
    const payload = JSON.parse(requestOptions.body);
    expect(payload.editor_settings).toEqual({
      text_position: 'top',
      font_family: 'classic',
      font_size: 34,
      font_color: '#112233',
      text_box_opacity: 0.4,
    });
  });
});
