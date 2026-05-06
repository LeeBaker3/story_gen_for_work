import { fireEvent, waitFor } from '@testing-library/dom';
import { afterEach, jest } from '@jest/globals';

import fs from 'node:fs';
import path from 'node:path';

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
    <section id="auth-section" style="display:none;">
      <form id="login-form"></form>
      <form id="signup-form" style="display:none;"></form>
      <form id="forgot-password-form" style="display:none;"></form>
      <form id="reset-password-form" style="display:none;"></form>
      <a id="show-signup-link" href="#">Show signup</a>
      <a id="show-login-link" href="#">Show login</a>
      <a id="show-forgot-password-link" href="#">Forgot password</a>
      <a id="show-reset-password-link" href="#">Reset password</a>
      <a id="forgot-password-back-to-login-link" href="#">Back to login</a>
      <a id="reset-password-back-to-login-link" href="#">Back to login</a>
      <a id="reset-password-request-link" href="#">Request reset</a>
    </section>
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
            <div class="dropdown-recovery">
              <div id="story-genre-recovery" class="inline-status inline-status--error dropdown-recovery-status" role="status" aria-live="polite" aria-atomic="true" style="display:none;"></div>
              <button type="button" id="story-genre-retry" class="action-button-secondary dropdown-recovery-retry" aria-controls="story-genre" style="display:none;">Retry loading genres</button>
            </div>
            <input type="text" id="story-tone" />
            <input type="text" id="story-setting" />
            <textarea id="story-outline"></textarea>
          </div>
          <div id="step-1-characters" class="wizard-step-panel" style="display:none;">
            <fieldset id="main-characters-fieldset">
              <div class="character-entry">
                <input id="char-name-1" class="char-name" value="Alice" />
                <button type="button" class="character-details-toggle" id="char-details-toggle-1" data-target="char-details-1" aria-controls="char-details-1" aria-expanded="false">Show Details</button>
                <div id="char-details-1" class="character-details-fields" style="display:none;">
                  <input id="char-age-1" class="char-age" value="" />
                  <select id="char-gender-1"><option value="">Select…</option><option value="female">Female</option></select>
                  <textarea id="char-physical-appearance-1"></textarea>
                  <textarea id="char-clothing-style-1"></textarea>
                  <textarea id="char-key-traits-1"></textarea>
                </div>
              </div>
            </fieldset>
            <button type="button" id="add-character-button">Add Another Character</button>
            <div id="character-library-panel" style="display:none;" aria-label="Character library">
              <input type="text" id="character-search" aria-label="Search characters" />
              <button type="button" id="character-sync-btn">Sync from stories</button>
              <button type="button" id="character-create-from-current-btn">Save form characters</button>
              <div id="character-list"></div>
              <div id="character-pagination"></div>
              <div id="character-detail-modal" style="display:none;"></div>
            </div>
          </div>
          <div id="step-2-options" class="wizard-step-panel" style="display:none;">
            <input id="story-num-pages" type="number" value="3" />
            <select id="story-writing-style"><option value="">Select...</option><option value="Playful">Playful</option></select>
            <select id="story-image-style"><option value="">Select...</option><option value="Cartoon">Cartoon</option></select>
            <div class="dropdown-recovery">
              <div id="story-image-style-recovery" class="inline-status inline-status--error dropdown-recovery-status" role="status" aria-live="polite" aria-atomic="true" style="display:none;"></div>
              <button type="button" id="story-image-style-retry" class="action-button-secondary dropdown-recovery-retry" aria-controls="story-image-style" style="display:none;">Retry loading image styles</button>
            </div>
            <select id="story-word-to-picture-ratio"><option value="">Select...</option><option value="One image per page">One image per page</option></select>
            <select id="story-text-density"><option value="">Select...</option><option value="Concise (~30-50 words)">Concise (~30-50 words)</option></select>
            <select id="story-page-format">
              <option value="letter">US Letter</option>
              <option value="a4">A4</option>
              <option value="portrait">Portrait</option>
              <option value="landscape">Landscape</option>
              <option value="square-storybook">Square Storybook</option>
            </select>
            <select id="story-layout-mode">
              <option value="full-page-overlay">Full-page overlay</option>
              <option value="horizontal-split">Horizontal split</option>
              <option value="vertical-split">Vertical split</option>
            </select>
            <select id="story-image-fit">
              <option value="">Default framing</option>
              <option value="Fill page">Fill page</option>
              <option value="Keep artwork contained">Keep artwork contained</option>
            </select>
            <select id="story-cover-title-placement">
              <option value="">Default title placement</option>
              <option value="Top">Top</option>
              <option value="Center">Center</option>
              <option value="Bottom">Bottom</option>
            </select>
            <select id="story-readability-treatment">
              <option value="">Default readability treatment</option>
              <option value="High-contrast box">High-contrast box</option>
              <option value="Soft shadow">Soft shadow</option>
              <option value="Subtle gradient band">Subtle gradient band</option>
            </select>
            <select id="story-default-text-position-v"></select>
            <select id="story-default-text-position-h"></select>
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
            <button type="button" id="save-draft-button">Save Draft</button>
            <button type="submit" id="generate-story-button" style="display:none;">Generate Story</button>
          </div>
        </form>
        <div id="generation-progress-area" style="display:none;">
          <p id="generation-status-message"></p>
          <div id="generation-progress-bar"></div>
        </div>
      </section>
      <section id="story-preview-section" style="display:none;">
        <div id="story-preview-content"></div>
        <button id="preview-pdf-button" style="display:none;">Preview PDF</button>
        <button id="export-pdf-button" style="display:none;">Export PDF</button>
      </section>
      <div id="pdf-preview-backdrop" class="modal-backdrop" aria-hidden="true"></div>
      <div id="pdf-preview-modal" class="modal" aria-hidden="true">
        <div class="modal-content">
          <button id="pdf-preview-close" type="button">Close</button>
          <p id="pdf-preview-status"></p>
          <div id="pdf-preview-frame-container" hidden>
            <iframe id="pdf-preview-frame" title="Story PDF preview"></iframe>
          </div>
          <div id="pdf-preview-error" hidden></div>
          <button id="pdf-preview-download" type="button" disabled>Download PDF</button>
        </div>
      </div>
      <section id="browse-stories-section" style="display:none;"></section>
      <section id="characters-section" style="display:none;"></section>
      <section id="message-area"><p id="api-message"></p></section>
      <div id="snackbar" style="display:none;"></div>
      <div id="toast-container"></div>
      <div id="spinner" style="display:none;"></div>
      <div id="adminPanelContainer" style="display:none;"><tbody id="adminUserTableBody"></tbody></div>
    </main>`;
}

function createGeneratedStoryFixture() {
  return {
    id: 321,
    title: 'Loop Adventure',
    genre: 'Fantasy',
    story_outline: 'Ava searches for a lantern.',
    main_characters: [{ name: 'Ava' }],
    num_pages: 2,
    tone: 'Warm',
    setting: 'Forest',
    image_style: 'Cartoon',
    writing_style: 'Playful',
    word_to_picture_ratio: 'One image per page',
    text_density: 'Concise (~30-50 words)',
    editor_settings: {
      page_format: 'square-storybook',
      layout_mode: 'vertical-split',
      image_fit: 'Keep artwork contained',
      cover_title_placement: 'Top',
      readability_treatment: 'High-contrast box',
      text_position: 'top-center',
      font_family: 'classic',
      font_size: 30,
      font_color: '#123456',
      text_box_opacity: 0.4,
    },
    pages: [
      {
        id: 11,
        story_id: 321,
        page_number: 0,
        text: 'Loop Adventure',
        image_description: 'A bright cover with Ava.',
        image_path: 'images/user_1/story_321/cover.png',
        editor_state: {
          original_text: 'Loop Adventure',
          original_image_path: 'images/user_1/story_321/cover.png',
        },
        created_at: '2026-05-01T12:00:00Z',
        updated_at: '2026-05-01T12:00:00Z',
      },
      {
        id: 12,
        story_id: 321,
        page_number: 1,
        text: 'Ava finds the hidden lantern.',
        image_description: 'Ava in a glowing forest.',
        image_path: 'images/user_1/story_321/page1.png',
        editor_state: {
          original_text: 'Ava finds the hidden lantern.',
          original_image_path: 'images/user_1/story_321/page1.png',
        },
        created_at: '2026-05-01T12:00:00Z',
        updated_at: '2026-05-01T12:00:00Z',
      },
    ],
    created_at: '2026-05-01T12:00:00Z',
    updated_at: '2026-05-01T12:00:00Z',
    owner_id: 1,
    is_draft: false,
    generated_at: '2026-05-01T12:00:00Z',
    is_hidden: false,
    is_deleted: false,
  };
}

describe('wizard navigation', () => {
  beforeEach(async () => {
    // Pretend user is logged in so script shows creation section
    window.localStorage.setItem('authToken', 'test');
    mountWizardDom();
    if (!window.URL.createObjectURL) {
      window.URL.createObjectURL = jest.fn();
    }
    if (!window.URL.revokeObjectURL) {
      window.URL.revokeObjectURL = jest.fn();
    }
    jest.spyOn(window.URL, 'createObjectURL').mockImplementation(() => 'blob:loop-asset');
    jest.spyOn(window.URL, 'revokeObjectURL').mockImplementation(() => { });
    jest.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => { });
    // Mock dynamic lists to allow selects to have valid options
    global.fetch = jest.fn(async (url) => {
      const u = String(url);
      if (u.includes('/api/v1/dynamic-lists/genres')) {
        return { ok: true, status: 200, json: async () => [{ item_value: 'Fantasy', item_label: 'Fantasy' }], headers: { get: () => 'application/json' } };
      }
      if (u.includes('/api/v1/dynamic-lists/image_styles')) {
        return { ok: true, status: 200, json: async () => [{ item_value: 'Cartoon', item_label: 'Cartoon' }], headers: { get: () => 'application/json' } };
      }
      if (u.includes('/api/v1/dynamic-lists/writing_styles')) {
        return { ok: true, status: 200, json: async () => [{ item_value: 'Playful', item_label: 'Playful' }], headers: { get: () => 'application/json' } };
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
      if (u.includes('/api/v1/characters/?')) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            items: [
              {
                id: 101,
                name: 'Library Fox',
                thumbnail_path: 'images/library-fox.png',
                description: 'Quick and curious',
              },
            ],
            total: 1,
          }),
          headers: { get: () => 'application/json' },
        };
      }
      if (u.includes('/api/v1/characters/101')) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            id: 101,
            name: 'Library Fox',
            age: 7,
            gender: 'female',
            description: 'Quick and curious',
            clothing_style: 'Travel cloak',
            key_traits: 'Brave',
          }),
          headers: { get: () => 'application/json' },
        };
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
    const writingStyleSel = document.getElementById('story-writing-style');
    const ratioSel = document.getElementById('story-word-to-picture-ratio');
    const densitySel = document.getElementById('story-text-density');
    const textPositionVSel = document.getElementById('story-default-text-position-v');
    const textPositionHSel = document.getElementById('story-default-text-position-h');
    const fontFamilySel = document.getElementById('story-default-font-family');
    if (genreSel) genreSel.innerHTML += '<option value="Fantasy">Fantasy</option>';
    if (imgStyleSel) imgStyleSel.innerHTML += '<option value="Cartoon">Cartoon</option>';
    if (writingStyleSel) writingStyleSel.innerHTML += '<option value="Playful">Playful</option>';
    if (ratioSel) ratioSel.innerHTML += '<option value="One image per page">One image per page</option>';
    if (densitySel) densitySel.innerHTML += '<option value="Concise (~30-50 words)">Concise (~30-50 words)</option>';
    if (textPositionVSel && !textPositionVSel.querySelector('option[value="top"]')) {
      textPositionVSel.innerHTML += '<option value="top">Top</option><option value="middle">Middle</option><option value="bottom">Bottom</option>';
    }
    if (textPositionHSel && !textPositionHSel.querySelector('option[value="left"]')) {
      textPositionHSel.innerHTML += '<option value="left">Left</option><option value="center">Centre</option><option value="right">Right</option>';
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

  afterEach(() => {
    jest.restoreAllMocks();
  });

  test('layout dropdowns load with split text position defaults', () => {
    const pageFormatSel = document.getElementById('story-page-format');
    const textPositionVSel = document.getElementById('story-default-text-position-v');
    const textPositionHSel = document.getElementById('story-default-text-position-h');
    const fontFamilySel = document.getElementById('story-default-font-family');

    expect(pageFormatSel.querySelector('option[value="square-storybook"]')).not.toBeNull();
    expect(pageFormatSel.value).toBe('letter');
    expect(textPositionVSel.querySelector('option[value="top"]')).not.toBeNull();
    expect(textPositionHSel.querySelector('option[value="center"]')).not.toBeNull();
    expect(textPositionVSel.value).toBe('bottom');
    expect(textPositionHSel.value).toBe('center');
    expect(fontFamilySel.querySelector('option[value="classic"]')).not.toBeNull();
    expect(fontFamilySel.value).toBe('storybook');
  });

  test('shipped wizard markup includes step guidance and required badges for required fields', () => {
    const htmlPath = path.resolve(process.cwd(), 'frontend/index.html');
    const html = fs.readFileSync(htmlPath, 'utf8');
    document.documentElement.innerHTML = html;

    const guidanceBlocks = document.querySelectorAll('.wizard-step-guidance');
    expect(guidanceBlocks).toHaveLength(4);
    expect(guidanceBlocks[0].textContent).toMatch(/complete the required fields to unlock the next step/i);
    expect(guidanceBlocks[1].textContent).toMatch(/only character names are required/i);
    expect(guidanceBlocks[2].textContent).toMatch(/page count, image style, word-to-picture ratio, and text density are required/i);
    expect(guidanceBlocks[3].textContent).toMatch(/review the story setup before generating/i);

    expect(document.querySelector('label[for="story-genre"] .required-badge')?.textContent).toBe('Required');
    expect(document.querySelector('label[for="story-outline"] .required-badge')?.textContent).toBe('Required');
    expect(document.querySelector('label[for="char-name-1"] .required-badge')?.textContent).toBe('Required');
    expect(document.querySelector('label[for="story-text-density"] .required-badge')?.textContent).toBe('Required');
    expect(document.getElementById('story-genre-recovery')).not.toBeNull();
    expect(document.getElementById('story-genre-retry')?.textContent).toMatch(/retry loading genres/i);
    expect(document.getElementById('story-image-style-recovery')).not.toBeNull();
    expect(document.getElementById('story-image-style-retry')?.textContent).toMatch(/retry loading image styles/i);

    expect(document.querySelector('label[for="story-title"]').textContent).toBe('Story Title');
    expect(document.querySelector('label[for="story-tone"]').textContent).toBe('Tone');
    expect(document.querySelector('label[for="story-writing-style"]').textContent).toBe('Writing Style');
    expect(document.querySelector('label[for="char-age-1"]').textContent).toBe('Age');
  });

  test('failed critical dropdowns disable, show inline recovery, and retry successfully', async () => {
    const fetchMock = global.fetch;
    const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => { });

    try {
      fetchMock.mockImplementation(async (url) => {
        const u = String(url);
        if (u.includes('/api/v1/dynamic-lists/genres')) {
          return {
            ok: false,
            status: 503,
            json: async () => ({ detail: 'genres unavailable' }),
            headers: { get: () => 'application/json' },
            text: async () => 'genres unavailable',
          };
        }
        if (u.includes('/api/v1/dynamic-lists/image_styles')) {
          return {
            ok: false,
            status: 503,
            json: async () => ({ detail: 'image styles unavailable' }),
            headers: { get: () => 'application/json' },
            text: async () => 'image styles unavailable',
          };
        }
        if (u.includes('/api/v1/dynamic-lists/writing_styles')) {
          return { ok: true, status: 200, json: async () => [{ item_value: 'Playful', item_label: 'Playful' }], headers: { get: () => 'application/json' } };
        }
        if (u.includes('/api/v1/dynamic-lists/word_to_picture_ratio')) {
          return { ok: true, status: 200, json: async () => [{ item_value: 'One image per page', item_label: 'One image per page' }], headers: { get: () => 'application/json' } };
        }
        if (u.includes('/api/v1/dynamic-lists/text_density')) {
          return { ok: true, status: 200, json: async () => [{ item_value: 'Concise (~30-50 words)', item_label: 'Concise (~30-50 words)' }], headers: { get: () => 'application/json' } };
        }
        if (u.includes('/api/v1/dynamic-lists/font_families')) {
          return { ok: true, status: 200, json: async () => [{ item_value: 'storybook', item_label: 'Storybook' }], headers: { get: () => 'application/json' } };
        }
        if (u.includes('/api/v1/dynamic-lists/genders')) {
          return { ok: true, status: 200, json: async () => [{ item_value: 'female', item_label: 'Female' }], headers: { get: () => 'application/json' } };
        }
        return { ok: true, status: 200, json: async () => ({}), headers: { get: () => 'application/json' } };
      });

      fireEvent.click(document.getElementById('nav-create-story'));
      await new Promise(r => setTimeout(r, 0));

      expect(document.getElementById('story-genre')).toBeDisabled();
      expect(document.getElementById('story-image-style')).toBeDisabled();
      expect(document.getElementById('story-genre-recovery').textContent).toMatch(/couldn't load genres/i);
      expect(document.getElementById('story-image-style-recovery').textContent).toMatch(/couldn't load image styles/i);
      expect(document.getElementById('story-genre-retry').style.display).toBe('inline-flex');
      expect(document.getElementById('story-image-style-retry').style.display).toBe('inline-flex');

      fetchMock.mockImplementation(async (url) => {
        const u = String(url);
        if (u.includes('/api/v1/dynamic-lists/genres')) {
          return { ok: true, status: 200, json: async () => [{ item_value: 'Fantasy', item_label: 'Fantasy' }], headers: { get: () => 'application/json' } };
        }
        if (u.includes('/api/v1/dynamic-lists/image_styles')) {
          return { ok: true, status: 200, json: async () => [{ item_value: 'Cartoon', item_label: 'Cartoon' }], headers: { get: () => 'application/json' } };
        }
        if (u.includes('/api/v1/dynamic-lists/writing_styles')) {
          return { ok: true, status: 200, json: async () => [{ item_value: 'Playful', item_label: 'Playful' }], headers: { get: () => 'application/json' } };
        }
        if (u.includes('/api/v1/dynamic-lists/word_to_picture_ratio')) {
          return { ok: true, status: 200, json: async () => [{ item_value: 'One image per page', item_label: 'One image per page' }], headers: { get: () => 'application/json' } };
        }
        if (u.includes('/api/v1/dynamic-lists/text_density')) {
          return { ok: true, status: 200, json: async () => [{ item_value: 'Concise (~30-50 words)', item_label: 'Concise (~30-50 words)' }], headers: { get: () => 'application/json' } };
        }
        if (u.includes('/api/v1/dynamic-lists/font_families')) {
          return { ok: true, status: 200, json: async () => [{ item_value: 'storybook', item_label: 'Storybook' }], headers: { get: () => 'application/json' } };
        }
        if (u.includes('/api/v1/dynamic-lists/genders')) {
          return { ok: true, status: 200, json: async () => [{ item_value: 'female', item_label: 'Female' }], headers: { get: () => 'application/json' } };
        }
        return { ok: true, status: 200, json: async () => ({}), headers: { get: () => 'application/json' } };
      });

      fireEvent.click(document.getElementById('story-genre-retry'));
      fireEvent.click(document.getElementById('story-image-style-retry'));
      await new Promise(r => setTimeout(r, 0));

      expect(document.getElementById('story-genre')).not.toBeDisabled();
      expect(document.getElementById('story-image-style')).not.toBeDisabled();
      expect(document.getElementById('story-genre-recovery').style.display).toBe('none');
      expect(document.getElementById('story-image-style-recovery').style.display).toBe('none');
      expect(document.getElementById('story-genre-retry').style.display).toBe('none');
      expect(document.getElementById('story-image-style-retry').style.display).toBe('none');
      expect(document.getElementById('story-genre').querySelector('option[value="Fantasy"]')).not.toBeNull();
      expect(document.getElementById('story-image-style').querySelector('option[value="Cartoon"]')).not.toBeNull();
    } finally {
      consoleErrorSpy.mockRestore();
    }
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
    expect(steps[0].disabled).toBe(false);
    expect(steps[1].hasAttribute('aria-current')).toBe(false);
    expect(steps[1].getAttribute('aria-disabled')).toBe('true');
    expect(steps[1].disabled).toBe(true);
    expect(steps[2].getAttribute('aria-disabled')).toBe('true');
    expect(steps[2].disabled).toBe(true);

    fireEvent.click(next);

    expect(steps[0].hasAttribute('aria-current')).toBe(false);
    expect(steps[0].hasAttribute('aria-disabled')).toBe(false);
    expect(steps[0].disabled).toBe(false);
    expect(steps[1].getAttribute('aria-current')).toBe('step');
    expect(steps[1].hasAttribute('aria-disabled')).toBe(false);
    expect(steps[1].disabled).toBe(false);
    expect(steps[2].hasAttribute('aria-disabled')).toBe(false);
    expect(steps[2].disabled).toBe(false);
    expect(steps[3].hasAttribute('aria-disabled')).toBe(false);
    expect(steps[3].disabled).toBe(false);
  });

  test('future step pills do not activate until they are reachable', () => {
    const steps = Array.from(document.querySelectorAll('#wizard-steps .wizard-step'));

    expect(steps[2].disabled).toBe(true);
    fireEvent.click(steps[2]);
    expect(document.getElementById('step-0-basics').style.display).not.toBe('none');
    expect(steps[0].getAttribute('aria-current')).toBe('step');

    fireEvent.click(document.getElementById('wizard-next'));
    steps[0].focus();
    expect(document.activeElement).toBe(steps[0]);
    fireEvent.click(steps[0]);

    expect(document.getElementById('step-0-basics').style.display).toBe('block');
    expect(steps[0].getAttribute('aria-current')).toBe('step');
  });

  test('template-loaded wizard enables later reachable steps while keeping Basics active', () => {
    const steps = Array.from(document.querySelectorAll('#wizard-steps .wizard-step'));

    fireEvent.click(document.getElementById('wizard-next'));
    fireEvent.click(document.getElementById('wizard-next'));

    window.__TEST_API__.populateCreateFormWithStoryData(createGeneratedStoryFixture(), false);

    expect(document.getElementById('step-0-basics').style.display).toBe('block');
    expect(steps[0].getAttribute('aria-current')).toBe('step');
    expect(document.getElementById('story-writing-style').value).toBe('Playful');
    expect(document.getElementById('story-layout-mode').value).toBe('vertical-split');
    expect(document.getElementById('story-image-fit').value).toBe('Keep artwork contained');
    expect(document.getElementById('story-cover-title-placement').value).toBe('Top');
    expect(document.getElementById('story-readability-treatment').value).toBe('High-contrast box');
    expect(steps[1].disabled).toBe(false);
    expect(steps[2].disabled).toBe(false);
    expect(steps[3].disabled).toBe(false);

    fireEvent.click(steps[3]);

    expect(document.getElementById('step-3-review').style.display).toBe('block');
    expect(steps[3].getAttribute('aria-current')).toBe('step');

    document.getElementById('story-outline').value = '';
    fireEvent.input(document.getElementById('story-outline'), {
      target: { value: '' },
    });

    expect(steps[1].disabled).toBe(true);
    expect(steps[2].disabled).toBe(true);
    expect(steps[3].disabled).toBe(true);
    expect(document.getElementById('step-0-basics').style.display).toBe('block');
    expect(steps[0].getAttribute('aria-current')).toBe('step');
  });

  test('added character row can be removed', () => {
    const addButton = document.getElementById('add-character-button');

    fireEvent.click(addButton);

    expect(document.getElementById('char-name-2')).not.toBeNull();
    expect(document.querySelector('label[for="char-name-2"] .required-badge')?.textContent).toBe('Required');
    expect(document.querySelector('label[for="char-age-2"]').textContent).toBe('Age');
    expect(document.querySelector('label[for="char-key-traits-2"]').textContent).toBe('Key Traits/Habits');

    const removeButton = document.querySelector('.remove-character-button');
    expect(removeButton).not.toBeNull();

    fireEvent.click(removeButton);

    expect(document.getElementById('char-name-2')).toBeNull();
    expect(document.querySelector('.remove-character-button')).toBeNull();
  });

  test('character detail disclosure exposes and updates aria state', () => {
    fireEvent.click(document.getElementById('wizard-next'));

    const toggle = document.getElementById('char-details-toggle-1');
    const details = document.getElementById('char-details-1');

    expect(toggle.getAttribute('aria-controls')).toBe('char-details-1');
    expect(toggle.getAttribute('aria-expanded')).toBe('false');
    expect(details.style.display).toBe('none');

    fireEvent.click(toggle);

    expect(toggle.getAttribute('aria-expanded')).toBe('true');
    expect(details.style.display).toBe('block');
    expect(toggle.textContent).toBe('Hide Details');

    fireEvent.click(toggle);

    expect(toggle.getAttribute('aria-expanded')).toBe('false');
    expect(details.style.display).toBe('none');
    expect(toggle.textContent).toBe('Show Details');
  });

  test('generate request includes wizard editor settings', async () => {
    document.getElementById('story-page-format').value = 'square-storybook';
    document.getElementById('story-layout-mode').value = 'horizontal-split';
    document.getElementById('story-default-text-position-v').value = 'top';
    document.getElementById('story-default-text-position-h').value = 'center';
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
      if (u.includes('/api/v1/dynamic-lists/writing_styles')) {
        return { ok: true, status: 200, json: async () => [{ item_value: 'Playful', item_label: 'Playful' }], headers: { get: () => 'application/json' } };
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
      page_format: 'square-storybook',
      layout_mode: 'horizontal-split',
      text_position: 'top-center',
      font_family: 'classic',
      font_size: 34,
      font_color: '#112233',
      text_box_opacity: 0.4,
    });
  });

  test('wizard submit completes polling, renders fetched editor, and exports pdf', async () => {
    jest.useFakeTimers();
    const story = createGeneratedStoryFixture();
    let statusCalls = 0;

    try {
      const fetchMock = global.fetch;
      fetchMock.mockImplementation(async (url, options = {}) => {
        const u = String(url);
        const method = String(options.method || 'GET').toUpperCase();

        if (u.includes('/api/v1/stories/') && method === 'POST') {
          return {
            ok: true,
            status: 202,
            json: async () => ({ id: 'task-97', story_id: 321, status: 'pending' }),
            headers: { get: () => 'application/json' },
          };
        }
        if (u.includes('/api/v1/stories/generation-status/task-97')) {
          statusCalls += 1;
          return {
            ok: true,
            status: 200,
            json: async () => ({
              id: 'task-97',
              story_id: 321,
              status: statusCalls === 1 ? 'in_progress' : 'completed',
              progress: statusCalls === 1 ? 65 : 100,
              current_step: statusCalls === 1 ? 'generating_page_images' : 'finalizing',
            }),
            headers: { get: () => 'application/json' },
          };
        }
        if (u.includes('/api/v1/stories/321/pages/11/image')) {
          return {
            ok: true,
            status: 200,
            blob: async () => new Blob(['cover-bytes'], { type: 'image/png' }),
            headers: { get: (name) => (name === 'content-type' ? 'image/png' : null) },
          };
        }
        if (u.includes('/api/v1/stories/321/pages/12/image')) {
          return {
            ok: true,
            status: 200,
            blob: async () => new Blob(['page-bytes'], { type: 'image/png' }),
            headers: { get: (name) => (name === 'content-type' ? 'image/png' : null) },
          };
        }
        if (u.includes('/api/v1/stories/321/pdf')) {
          return {
            ok: true,
            status: 200,
            blob: async () => new Blob(['pdf-bytes'], { type: 'application/pdf' }),
            headers: {
              get: (name) => {
                if (name === 'content-type') return 'application/pdf';
                if (name === 'content-disposition') return 'attachment; filename=Loop Adventure.pdf';
                return null;
              },
            },
          };
        }
        if (u.includes('/api/v1/stories/321') && method === 'GET') {
          return {
            ok: true,
            status: 200,
            json: async () => story,
            headers: { get: () => 'application/json' },
          };
        }
        if (u.includes('/api/v1/users/me')) {
          return {
            ok: true,
            status: 200,
            json: async () => ({ id: 1, username: 'user@example.com', role: 'user' }),
            headers: { get: () => 'application/json' },
          };
        }
        if (u.includes('/api/v1/dynamic-lists/genres')) {
          return { ok: true, status: 200, json: async () => [{ item_value: 'Fantasy', item_label: 'Fantasy' }], headers: { get: () => 'application/json' } };
        }
        if (u.includes('/api/v1/dynamic-lists/image_styles')) {
          return { ok: true, status: 200, json: async () => [{ item_value: 'Cartoon', item_label: 'Cartoon' }], headers: { get: () => 'application/json' } };
        }
        if (u.includes('/api/v1/dynamic-lists/writing_styles')) {
          return { ok: true, status: 200, json: async () => [{ item_value: 'Playful', item_label: 'Playful' }], headers: { get: () => 'application/json' } };
        }
        if (u.includes('/api/v1/dynamic-lists/word_to_picture_ratio')) {
          return { ok: true, status: 200, json: async () => [{ item_value: 'One image per page', item_label: 'One image per page' }], headers: { get: () => 'application/json' } };
        }
        if (u.includes('/api/v1/dynamic-lists/text_density')) {
          return { ok: true, status: 200, json: async () => [{ item_value: 'Concise (~30-50 words)', item_label: 'Concise (~30-50 words)' }], headers: { get: () => 'application/json' } };
        }
        if (u.includes('/api/v1/dynamic-lists/text_positions')) {
          return { ok: true, status: 200, json: async () => [{ item_value: 'top', item_label: 'Top' }, { item_value: 'center', item_label: 'Center' }], headers: { get: () => 'application/json' } };
        }
        if (u.includes('/api/v1/dynamic-lists/font_families')) {
          return { ok: true, status: 200, json: async () => [{ item_value: 'storybook', item_label: 'Storybook' }, { item_value: 'classic', item_label: 'Classic' }], headers: { get: () => 'application/json' } };
        }
        if (u.includes('/api/v1/dynamic-lists/genders')) {
          return { ok: true, status: 200, json: async () => [{ item_value: 'female', item_label: 'Female' }], headers: { get: () => 'application/json' } };
        }
        return { ok: true, status: 200, json: async () => ({}), headers: { get: () => 'application/json' } };
      });

      window.__TEST_API__.setPollingConfig({
        baseIntervalMs: 10,
        maxIntervalMs: 10,
        maxDurationMs: 200,
      });

      document.getElementById('story-title').value = 'Loop Request';
      document.getElementById('story-page-format').value = 'square-storybook';
      document.getElementById('story-default-text-position-v').value = 'top';
      document.getElementById('story-default-text-position-h').value = 'center';
      document.getElementById('story-default-font-family').value = 'classic';
      document.getElementById('story-default-font-size').value = '30';
      document.getElementById('story-default-font-color').value = '#123456';
      document.getElementById('story-default-text-box-opacity').value = '0.4';

      const next = document.getElementById('wizard-next');
      fireEvent.click(next);
      fireEvent.click(next);
      fireEvent.click(next);
      fireEvent.click(document.getElementById('generate-story-button'));

      await jest.advanceTimersByTimeAsync(50);

      await waitFor(() => {
        expect(statusCalls).toBeGreaterThanOrEqual(2);
        expect(document.getElementById('story-preview-section').style.display).toBe('block');
        expect(document.getElementById('story-editor-title').value).toBe('Loop Adventure');
      });

      expect(document.querySelectorAll('.story-editor-page-card')).toHaveLength(2);
      expect(document.querySelectorAll('.story-editor-page-image')).toHaveLength(2);
      expect(document.querySelector('[data-page-field="text"][data-page-id="12"]').value).toBe(
        'Ava finds the hidden lantern.'
      );
      expect(document.getElementById('export-pdf-button').style.display).toBe('inline-block');

      fireEvent.click(document.getElementById('export-pdf-button'));

      await waitFor(() => {
        expect(fetchMock).toHaveBeenCalledWith(
          expect.stringContaining('/api/v1/stories/321/pdf'),
          expect.objectContaining({
            method: 'GET',
            headers: expect.objectContaining({ Authorization: 'Bearer test' }),
          })
        );
      });

      await waitFor(() => {
        expect(window.URL.createObjectURL).toHaveBeenCalled();
        expect(document.getElementById('api-message').textContent).toMatch(/pdf exported successfully/i);
      });
    } finally {
      jest.useRealTimers();
    }
  });

  test('review step summarizes selected page format and new preferences', () => {
    document.getElementById('story-page-format').value = 'landscape';
    document.getElementById('story-writing-style').value = 'Playful';
    document.getElementById('story-image-fit').value = 'Fill page';
    document.getElementById('story-cover-title-placement').value = 'Bottom';
    document.getElementById('story-readability-treatment').value = 'Soft shadow';

    const next = document.getElementById('wizard-next');
    fireEvent.click(next);
    fireEvent.click(next);
    fireEvent.click(next);

    const review = document.getElementById('review-container');
    expect(review.textContent).toContain('Page format: Landscape');
    expect(review.textContent).toContain('Writing style: Playful');
    expect(review.textContent).toContain('Image framing: Fill page');
    expect(review.textContent).toContain('Cover title placement: Bottom');
    expect(review.textContent).toContain('Readability treatment: Soft shadow');
  });

  test('draft save failure preserves form state and sends editor settings payload', async () => {
    const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => { });

    try {
      document.getElementById('story-title').value = 'Draft Title';
      document.getElementById('story-genre').value = 'Fantasy';
      document.getElementById('story-outline').value = 'Draft outline';
      document.getElementById('story-tone').value = 'Warm';
      document.getElementById('story-setting').value = 'Forest';
      document.getElementById('story-writing-style').value = 'Playful';
      document.getElementById('story-num-pages').value = '7';
      document.getElementById('story-page-format').value = 'a4';
      document.getElementById('story-layout-mode').value = 'horizontal-split';
      document.getElementById('story-image-fit').value = 'Keep artwork contained';
      document.getElementById('story-cover-title-placement').value = 'Top';
      document.getElementById('story-readability-treatment').value = 'High-contrast box';
      document.getElementById('story-default-text-position-v').value = 'top';
      document.getElementById('story-default-text-position-h').value = 'right';
      document.getElementById('story-default-font-family').value = 'classic';
      document.getElementById('story-default-font-size').value = '32';
      document.getElementById('story-default-font-color').value = '#abcdef';
      document.getElementById('story-default-text-box-opacity').value = '0.3';

      const fetchMock = global.fetch;
      fetchMock.mockImplementation(async (url, options = {}) => {
        const u = String(url);
        if (u.includes('/stories/drafts/') && options.method === 'POST') {
          return {
            ok: false,
            status: 500,
            json: async () => ({ detail: 'Draft exploded' }),
            headers: { get: () => 'application/json' },
            text: async () => 'Draft exploded',
          };
        }
        if (u.includes('/api/v1/dynamic-lists/genres')) {
          return { ok: true, status: 200, json: async () => [{ item_value: 'Fantasy', item_label: 'Fantasy' }], headers: { get: () => 'application/json' } };
        }
        if (u.includes('/api/v1/dynamic-lists/image_styles')) {
          return { ok: true, status: 200, json: async () => [{ item_value: 'Cartoon', item_label: 'Cartoon' }], headers: { get: () => 'application/json' } };
        }
        if (u.includes('/api/v1/dynamic-lists/writing_styles')) {
          return { ok: true, status: 200, json: async () => [{ item_value: 'Playful', item_label: 'Playful' }], headers: { get: () => 'application/json' } };
        }
        if (u.includes('/api/v1/dynamic-lists/writing_styles')) {
          return { ok: true, status: 200, json: async () => [{ item_value: 'Playful', item_label: 'Playful' }], headers: { get: () => 'application/json' } };
        }
        if (u.includes('/api/v1/dynamic-lists/word_to_picture_ratio')) {
          return { ok: true, status: 200, json: async () => [{ item_value: 'One image per page', item_label: 'One image per page' }], headers: { get: () => 'application/json' } };
        }
        if (u.includes('/api/v1/dynamic-lists/text_density')) {
          return { ok: true, status: 200, json: async () => [{ item_value: 'Concise (~30-50 words)', item_label: 'Concise (~30-50 words)' }], headers: { get: () => 'application/json' } };
        }
        if (u.includes('/api/v1/dynamic-lists/font_families')) {
          return { ok: true, status: 200, json: async () => [{ item_value: 'storybook', item_label: 'Storybook' }, { item_value: 'classic', item_label: 'Classic' }], headers: { get: () => 'application/json' } };
        }
        if (u.includes('/api/v1/dynamic-lists/genders')) {
          return { ok: true, status: 200, json: async () => [{ item_value: 'female', item_label: 'Female' }], headers: { get: () => 'application/json' } };
        }
        return { ok: true, status: 200, json: async () => ({}), headers: { get: () => 'application/json' } };
      });

      fireEvent.click(document.getElementById('save-draft-button'));

      await waitFor(() => {
        const draftRequest = fetchMock.mock.calls.find(([url, options]) => String(url).includes('/stories/drafts/') && options?.method === 'POST');
        expect(draftRequest).toBeTruthy();
      });

      const [, requestOptions] = fetchMock.mock.calls.find(
        ([url, options]) => String(url).includes('/stories/drafts/') && options?.method === 'POST'
      );
      const payload = JSON.parse(requestOptions.body);

      expect(payload.editor_settings).toEqual({
        page_format: 'a4',
        layout_mode: 'horizontal-split',
        image_fit: 'Keep artwork contained',
        cover_title_placement: 'Top',
        readability_treatment: 'High-contrast box',
        text_position: 'top-right',
        font_family: 'classic',
        font_size: 32,
        font_color: '#abcdef',
        text_box_opacity: 0.3,
      });
      expect(payload.writing_style).toBe('Playful');
      await waitFor(() => {
        expect(document.getElementById('api-message').textContent).toMatch(/draft saving failed: draft exploded/i);
      });
      expect(document.getElementById('story-title').value).toBe('Draft Title');
      expect(document.getElementById('story-outline').value).toBe('Draft outline');
      expect(document.getElementById('story-genre').value).toBe('Fantasy');
    } finally {
      consoleErrorSpy.mockRestore();
    }
  });

  test('story start failure preserves form state and includes selected library character ids', async () => {
    const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => { });

    try {
      document.getElementById('story-title').value = 'Library Story';
      document.getElementById('story-genre').value = 'Fantasy';
      document.getElementById('story-outline').value = 'A fox saves the village';
      document.getElementById('story-num-pages').value = '6';
      document.getElementById('story-page-format').value = 'square-storybook';
      document.getElementById('story-layout-mode').value = 'vertical-split';
      document.getElementById('story-default-text-position-v').value = 'middle';
      document.getElementById('story-default-text-position-h').value = 'left';
      document.getElementById('story-default-font-family').value = 'classic';
      document.getElementById('story-default-font-size').value = '30';
      document.getElementById('story-default-font-color').value = '#334455';
      document.getElementById('story-default-text-box-opacity').value = '0.5';

      const fetchMock = global.fetch;
      fetchMock.mockImplementation(async (url, options = {}) => {
        const u = String(url);
        if (u.includes('/api/v1/stories/') && options.method === 'POST') {
          return {
            ok: false,
            status: 500,
            json: async () => ({ detail: 'Story start exploded' }),
            headers: { get: () => 'application/json' },
            text: async () => 'Story start exploded',
          };
        }
        if (u.includes('/api/v1/characters/?')) {
          return {
            ok: true,
            status: 200,
            json: async () => ({
              items: [
                {
                  id: 101,
                  name: 'Library Fox',
                  thumbnail_path: 'images/library-fox.png',
                  description: 'Quick and curious',
                },
              ],
              total: 1,
            }),
            headers: { get: () => 'application/json' },
          };
        }
        if (u.includes('/api/v1/characters/101')) {
          return {
            ok: true,
            status: 200,
            json: async () => ({
              id: 101,
              name: 'Library Fox',
              age: 7,
              gender: 'female',
              description: 'Quick and curious',
              clothing_style: 'Travel cloak',
              key_traits: 'Brave',
            }),
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
        if (u.includes('/api/v1/dynamic-lists/font_families')) {
          return { ok: true, status: 200, json: async () => [{ item_value: 'storybook', item_label: 'Storybook' }, { item_value: 'classic', item_label: 'Classic' }], headers: { get: () => 'application/json' } };
        }
        if (u.includes('/api/v1/dynamic-lists/genders')) {
          return { ok: true, status: 200, json: async () => [{ item_value: 'female', item_label: 'Female' }], headers: { get: () => 'application/json' } };
        }
        return { ok: true, status: 200, json: async () => ({}), headers: { get: () => 'application/json' } };
      });

      fireEvent.click(document.getElementById('wizard-next'));

      await waitFor(() => {
        expect(document.querySelector('.character-card[data-id="101"]')).not.toBeNull();
      });

      fireEvent.click(document.querySelector('.character-card[data-id="101"]'));

      await waitFor(() => {
        expect(document.getElementById('selected-characters-chipbar').textContent).toContain('#101');
      });

      fireEvent.click(document.getElementById('wizard-next'));
      fireEvent.click(document.getElementById('wizard-next'));
      fireEvent.click(document.getElementById('generate-story-button'));

      await waitFor(() => {
        const storyRequest = fetchMock.mock.calls.find(([url, options]) => String(url).includes('/api/v1/stories/') && options?.method === 'POST');
        expect(storyRequest).toBeTruthy();
      });

      const [, requestOptions] = fetchMock.mock.calls.find(
        ([url, options]) => String(url).includes('/api/v1/stories/') && options?.method === 'POST'
      );
      const payload = JSON.parse(requestOptions.body);

      expect(payload.character_ids).toEqual([101]);
      expect(payload.editor_settings).toEqual({
        page_format: 'square-storybook',
        layout_mode: 'vertical-split',
        text_position: 'middle-left',
        font_family: 'classic',
        font_size: 30,
        font_color: '#334455',
        text_box_opacity: 0.5,
      });
      await waitFor(() => {
        expect(document.getElementById('api-message').textContent).toMatch(/story start exploded/i);
      });
      expect(document.getElementById('story-title').value).toBe('Library Story');
      expect(document.getElementById('story-outline').value).toBe('A fox saves the village');
      expect(document.getElementById('selected-characters-chipbar').textContent).toContain('#101');
    } finally {
      consoleErrorSpy.mockRestore();
    }
  });
});
