import { fireEvent, waitFor } from '@testing-library/dom';
import { jest } from '@jest/globals';

let saveEditorResponse;
let pageActionResponse;

function createDeferred() {
    let resolve;
    let reject;
    const promise = new Promise((res, rej) => {
        resolve = res;
        reject = rej;
    });

    return { promise, resolve, reject };
}

function createSavedStory(body) {
    const baseStory = createStoryFixture();
    const payloadPages = Array.isArray(body.pages) && body.pages.length > 0
        ? body.pages
        : baseStory.pages;

    return {
        id: 321,
        title: body.title ?? baseStory.title,
        cover_subtitle: body.cover_subtitle ?? '',
        cover_author: body.cover_author ?? '',
        genre: 'Fantasy',
        story_outline: 'Outline',
        main_characters: [],
        num_pages: Math.max(payloadPages.length - 1, 0),
        tone: null,
        setting: null,
        image_style: 'Default',
        word_to_picture_ratio: 'One image per page',
        text_density: 'Concise (~30-50 words)',
        editor_settings: body.editor_settings ?? baseStory.editor_settings,
        pages: payloadPages.map((page, index) => {
            const basePage = baseStory.pages.find((item) => item.id === page.id) || {};
            const resolvedText = page.text ?? (index === 0 ? (body.title ?? baseStory.title) : (basePage.text || ''));
            const resolvedImagePath = page.image_path ?? basePage.image_path ?? null;
            return {
                id: page.id ?? 200 + index,
                story_id: 321,
                page_number: page.page_number ?? index,
                text: resolvedText,
                image_description: page.image_description ?? basePage.image_description ?? null,
                image_path: resolvedImagePath,
                editor_state: {
                    original_text: page.editor_state?.original_text ?? basePage.editor_state?.original_text ?? resolvedText,
                    original_image_path: page.editor_state?.original_image_path ?? basePage.editor_state?.original_image_path ?? resolvedImagePath,
                    ...(page.editor_state || {}),
                },
                created_at: '2026-04-27T12:00:00Z',
                updated_at: '2026-04-27T12:00:00Z',
            };
        }),
        created_at: '2026-04-27T12:00:00Z',
        updated_at: '2026-04-27T12:00:00Z',
        owner_id: 1,
        is_draft: false,
        generated_at: '2026-04-27T12:00:00Z',
        is_hidden: false,
        is_deleted: false,
    };
}

function createEditorPutResponse(body) {
    return {
        ok: true,
        status: 200,
        json: async () => createSavedStory(body),
        headers: { get: () => 'application/json' },
    };
}

function createStoryFixture() {
    return {
        id: 321,
        title: 'Original Title',
        cover_subtitle: '',
        cover_author: '',
        genre: 'Fantasy',
        story_outline: 'Outline',
        main_characters: [],
        num_pages: 2,
        tone: null,
        setting: null,
        image_style: 'Default',
        word_to_picture_ratio: 'One image per page',
        text_density: 'Concise (~30-50 words)',
        editor_settings: {
            font_family: 'storybook',
            font_size: 28,
            font_color: '#ffffff',
            text_position: 'bottom',
            text_alignment: 'center',
            text_box_opacity: 0.6,
            layout_mode: 'full-page-overlay',
            readability_treatment: '',
        },
        pages: [
            {
                id: 11,
                story_id: 321,
                page_number: 0,
                text: 'Original Title',
                image_description: 'Cover art',
                image_path: 'images/user_1/story_321/cover.png',
                editor_state: {
                    original_text: 'Original Title',
                    original_image_path: 'images/user_1/story_321/cover.png',
                },
                created_at: '2026-04-27T12:00:00Z',
                updated_at: '2026-04-27T12:00:00Z',
            },
            {
                id: 12,
                story_id: 321,
                page_number: 1,
                text: 'Page one text',
                image_description: 'Dragon scene',
                image_path: 'images/user_1/story_321/page1.png',
                editor_state: {
                    original_text: 'Page one text',
                    original_image_path: 'images/user_1/story_321/page1.png',
                },
                created_at: '2026-04-27T12:00:00Z',
                updated_at: '2026-04-27T12:00:00Z',
            },
        ],
        created_at: '2026-04-27T12:00:00Z',
        updated_at: '2026-04-27T12:00:00Z',
        owner_id: 1,
        is_draft: false,
        generated_at: '2026-04-27T12:00:00Z',
        is_hidden: false,
        is_deleted: false,
    };
}

function createDraftFixture() {
    return {
        ...createStoryFixture(),
        id: 654,
        title: 'Draft Story',
        is_draft: true,
    };
}

function mountEditorDom() {
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
        <h2>Login</h2>
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
                <form id="story-creation-form">
                    <input id="story-title" type="text" />
                    <select id="story-genre"><option value="">Select...</option><option value="Fantasy">Fantasy</option></select>
                    <textarea id="story-outline"></textarea>
                    <input id="story-num-pages" type="number" value="2" />
                    <input id="story-tone" type="text" />
                    <input id="story-setting" type="text" />
                    <select id="story-writing-style"><option value="">Select...</option><option value="Classic">Classic</option></select>
                    <select id="story-word-to-picture-ratio"><option value="">Select...</option><option value="One image per page">One image per page</option></select>
                    <select id="story-text-density"><option value="">Select...</option><option value="Concise (~30-50 words)">Concise (~30-50 words)</option></select>
                    <select id="story-image-style"><option value="">Select...</option><option value="Default">Default</option></select>
                    <select id="story-page-format"><option value="letter">US Letter</option></select>
                    <select id="story-layout-mode"><option value="full-page-overlay">Full-page overlay</option><option value="horizontal-split">Horizontal split</option><option value="vertical-split">Vertical split</option></select>
                    <select id="story-default-text-position-v"><option value="bottom">Bottom</option></select>
                    <select id="story-default-text-position-h"><option value="center">Centre</option></select>
                    <select id="story-default-font-family"><option value="storybook">Storybook</option></select>
                    <input id="story-default-font-size" type="number" value="28" />
                    <input id="story-default-font-color" type="color" value="#ffffff" />
                    <input id="story-default-text-box-opacity" type="range" min="0" max="1" step="0.05" value="0.6" />
                </form>
                <fieldset id="main-characters-fieldset">
                    <div class="character-entry">
                        <input id="char-name-1" class="char-name" value="" />
                        <button type="button" class="character-details-toggle" id="char-details-toggle-1" data-target="char-details-1" aria-controls="char-details-1" aria-expanded="false">Show Details</button>
                        <div id="char-details-1" class="character-details-fields" style="display:none;">
                            <input id="char-age-1" class="char-age" value="" />
                            <select id="char-gender-1"><option value="">Select...</option><option value="female">Female</option></select>
                            <textarea id="char-physical-appearance-1"></textarea>
                            <textarea id="char-clothing-style-1"></textarea>
                            <textarea id="char-key-traits-1"></textarea>
                        </div>
                    </div>
                </fieldset>
        <button type="button" id="add-character-button">Add Another Character</button>
        <button type="button" id="save-draft-button">Save Draft</button>
        <button type="button" id="generate-story-button">Generate Story</button>
        <div id="generation-progress-area" style="display:none;">
          <div id="generation-status-message"></div>
          <div id="generation-progress-bar"></div>
        </div>
        <div id="wizard-steps"></div>
        <div id="step-0-basics"></div>
        <div id="step-1-characters"></div>
        <div id="step-2-options"></div>
        <div id="step-3-review"></div>
        <button id="wizard-prev" type="button"></button>
        <button id="wizard-next" type="button"></button>
        <div id="review-container"></div>
      </section>
      <section id="story-preview-section" style="display:block;">
        <div id="story-preview-content"></div>
                <button id="preview-pdf-button" style="display:none;">Preview</button>
        <button id="export-pdf-button" style="display:none;">Export</button>
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
      <section id="browse-stories-section" style="display:none;"><div id="user-stories-list"></div></section>
      <section id="characters-section" style="display:none;"></section>
      <section id="message-area"><p id="api-message"></p></section>
      <div id="snackbar" style="display:none;"></div>
      <div id="toast-container"></div>
      <div id="spinner" style="display:none;"></div>
      <div id="adminPanelContainer" style="display:none;"><tbody id="adminUserTableBody"></tbody></div>
    </main>`;
}

describe('story editor MVP', () => {
    beforeEach(async () => {
        jest.useFakeTimers();
        window.localStorage.setItem('authToken', 'test-token');
        mountEditorDom();
        saveEditorResponse = (body) => createEditorPutResponse(body);
        pageActionResponse = null;

        if (!window.URL.createObjectURL) {
            window.URL.createObjectURL = jest.fn();
        }
        if (!window.URL.revokeObjectURL) {
            window.URL.revokeObjectURL = jest.fn();
        }
        jest.spyOn(window.URL, 'createObjectURL').mockImplementation(() => 'blob:story-page-image');
        jest.spyOn(window.URL, 'revokeObjectURL').mockImplementation(() => { });

        global.fetch = jest.fn(async (url, options = {}) => {
            const value = String(url);
            const method = String(options.method || 'GET').toUpperCase();

            if (value.includes('/api/v1/users/me/')) {
                return {
                    ok: true,
                    status: 200,
                    json: async () => ({ id: 1, username: 'user@example.com', role: 'user' }),
                    headers: { get: () => 'application/json' },
                };
            }

            if (value.includes('/api/v1/stories/321/editor') && method === 'PUT') {
                const body = JSON.parse(options.body);
                return saveEditorResponse(body);
            }

            if (value.match(/\/api\/v1\/stories\/321(?:\?|$)/) && method === 'GET') {
                return {
                    ok: true,
                    status: 200,
                    json: async () => createStoryFixture(),
                    headers: { get: () => 'application/json' },
                };
            }

            if (value.includes('/stories/drafts/654') && method === 'GET') {
                return {
                    ok: true,
                    status: 200,
                    json: async () => createDraftFixture(),
                    headers: { get: () => 'application/json' },
                };
            }

            if (value.includes('/api/v1/stories/321/pages/') && method === 'POST') {
                if (pageActionResponse) {
                    return pageActionResponse(value, options);
                }

                const story = createStoryFixture();
                const pageId = value.includes('/pages/11/') ? 11 : 12;
                return {
                    ok: true,
                    status: 200,
                    json: async () => story.pages.find((page) => page.id === pageId),
                    headers: { get: () => 'application/json' },
                };
            }

            if (value.match(/\/api\/v1\/stories\/321\/pages\/\d+\/image$/) && method === 'GET') {
                return {
                    ok: true,
                    status: 200,
                    blob: async () => new Blob(['image-bytes'], { type: 'image/png' }),
                    headers: { get: (name) => name === 'content-type' ? 'image/png' : null },
                };
            }

            if (value.includes('/api/v1/stories/321/pdf')) {
                return {
                    ok: true,
                    status: 200,
                    blob: async () => new Blob(['pdf-bytes'], { type: 'application/pdf' }),
                    headers: {
                        get: (name) => {
                            if (name === 'content-disposition') {
                                return value.includes('disposition=inline')
                                    ? 'inline; filename=Original Title.pdf'
                                    : 'attachment; filename=Original Title.pdf';
                            }
                            if (name === 'content-type') {
                                return 'application/pdf';
                            }
                            return null;
                        },
                    },
                };
            }

            return {
                ok: true,
                status: 200,
                json: async () => ([]),
                headers: { get: () => 'application/json' },
            };
        });

        await import('../../frontend/script.js');
        document.dispatchEvent(new Event('DOMContentLoaded'));
    });

    afterEach(() => {
        jest.useRealTimers();
        jest.restoreAllMocks();
    });

    test('renders story editor and saves title/page changes', async () => {
        const story = createStoryFixture();

        window.__TEST_API__.displayStory(story);

        await waitFor(() => {
            const renderedImages = document.querySelectorAll('.story-editor-page-image');
            expect(renderedImages.length).toBe(2);
            renderedImages.forEach((image) => {
                expect(image.getAttribute('src')).toBe('blob:story-page-image');
            });
        });

        expect(global.fetch).toHaveBeenCalledWith(
            expect.stringContaining('/api/v1/stories/321/pages/11/image'),
            expect.objectContaining({
                method: 'GET',
                headers: expect.objectContaining({ Authorization: 'Bearer test-token' }),
            }),
        );

        const titleInput = document.getElementById('story-editor-title');
        const subtitleInput = document.getElementById('story-editor-cover-subtitle');
        const authorInput = document.getElementById('story-editor-cover-author');
        expect(titleInput).not.toBeNull();
        expect(document.querySelectorAll('.story-editor-page-card').length).toBe(2);

        fireEvent.input(titleInput, { target: { value: 'Edited Title' } });
        fireEvent.input(subtitleInput, { target: { value: 'A hopeful subtitle' } });
        fireEvent.input(authorInput, { target: { value: 'Test Author' } });
        const pageTextareas = document.querySelectorAll('[data-page-field="text"]');
        fireEvent.input(pageTextareas[1], { target: { value: 'Edited page body' } });

        await jest.advanceTimersByTimeAsync(900);

        await waitFor(() => {
            expect(global.fetch).toHaveBeenCalledWith(
                expect.stringContaining('/api/v1/stories/321/editor'),
                expect.objectContaining({ method: 'PUT' }),
            );
        });

        const saveButton = document.getElementById('story-editor-save-button');
        fireEvent.click(saveButton);

        await waitFor(() => {
            const saveCalls = global.fetch.mock.calls.filter(
                ([url, options]) => String(url).includes('/api/v1/stories/321/editor') && String(options?.method || 'GET').toUpperCase() === 'PUT'
            );
            expect(saveCalls.length).toBeGreaterThanOrEqual(2);
        });

        const latestSaveCall = global.fetch.mock.calls.filter(
            ([url, options]) => String(url).includes('/api/v1/stories/321/editor') && String(options?.method || 'GET').toUpperCase() === 'PUT'
        ).at(-1);
        const latestPayload = JSON.parse(latestSaveCall[1].body);
        expect(latestPayload.cover_subtitle).toBe('A hopeful subtitle');
        expect(latestPayload.cover_author).toBe('Test Author');
        expect(document.querySelector('.story-editor-cover-subtitle').textContent).toBe('A hopeful subtitle');
        expect(document.querySelector('.story-editor-cover-author').textContent).toBe('By Test Author');

        expect(document.getElementById('export-pdf-button').style.display).toBe('inline-block');
        expect(document.getElementById('preview-pdf-button').style.display).toBe('inline-block');
    });

    test('opens a PDF preview modal and allows downloading the previewed file', async () => {
        window.__TEST_API__.displayStory(createStoryFixture(), { mode: 'preview' });

        await waitFor(() => {
            expect(document.getElementById('preview-pdf-button').style.display).toBe('inline-block');
        });

        const appendSpy = jest.spyOn(document.body, 'appendChild');
        const removeSpy = jest.spyOn(document.body, 'removeChild');
        const anchorClickSpy = jest
            .spyOn(HTMLAnchorElement.prototype, 'click')
            .mockImplementation(() => { });

        fireEvent.click(document.getElementById('preview-pdf-button'));

        await waitFor(() => {
            expect(global.fetch).toHaveBeenCalledWith(
                expect.stringContaining('/api/v1/stories/321/pdf?disposition=inline'),
                expect.objectContaining({
                    method: 'GET',
                    headers: expect.objectContaining({ Authorization: 'Bearer test-token' }),
                }),
            );
            expect(document.getElementById('pdf-preview-modal').classList.contains('open')).toBe(true);
            expect(document.getElementById('pdf-preview-frame').getAttribute('src')).toBe('blob:story-page-image');
            expect(document.getElementById('pdf-preview-download').disabled).toBe(false);
        });

        fireEvent.click(document.getElementById('pdf-preview-download'));

        expect(appendSpy).toHaveBeenCalled();
        expect(removeSpy).toHaveBeenCalled();
        expect(anchorClickSpy).toHaveBeenCalled();
        expect(document.getElementById('api-message').textContent).toMatch(/pdf downloaded from preview/i);
    });

    test('shows a clear error state when PDF preview generation fails', async () => {
        const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => { });
        window.__TEST_API__.displayStory(createStoryFixture(), { mode: 'preview' });

        const defaultFetch = global.fetch.getMockImplementation();
        global.fetch.mockImplementation((url, options = {}) => {
            if (String(url).includes('/api/v1/stories/321/pdf')) {
                return Promise.resolve({
                    ok: false,
                    status: 500,
                    statusText: 'Server Error',
                    json: async () => ({ detail: 'Failed to generate PDF' }),
                    text: async () => 'Failed to generate PDF',
                    headers: { get: () => 'application/json' },
                });
            }
            return defaultFetch(url, options);
        });

        fireEvent.click(document.getElementById('preview-pdf-button'));

        await waitFor(() => {
            expect(document.getElementById('pdf-preview-error').hidden).toBe(false);
            expect(document.getElementById('pdf-preview-error').textContent).toMatch(/error previewing pdf/i);
            expect(document.getElementById('pdf-preview-download').disabled).toBe(true);
            expect(document.getElementById('api-message').textContent).toMatch(/error previewing pdf/i);
        });

        expect(consoleErrorSpy).toHaveBeenCalledWith(
            '[PDFPreview] Error preparing PDF preview:',
            expect.any(Error),
        );
    });

    test('shows persisted cover subtitle and author in preview mode', async () => {
        const story = createStoryFixture();
        story.cover_subtitle = 'A saved preview subtitle';
        story.cover_author = 'Preview Author';

        window.__TEST_API__.displayStory(story, { mode: 'preview' });

        await waitFor(() => {
            expect(document.querySelector('.story-editor-page-card--preview')).not.toBeNull();
        });

        expect(document.querySelector('.story-editor-cover-subtitle').textContent).toBe('A saved preview subtitle');
        expect(document.querySelector('.story-editor-cover-author').textContent).toBe('By Preview Author');
    });

    test('finalized stories open in preview first and can toggle into and out of edit mode', async () => {
        await window.__TEST_API__.viewOrEditStory(321, false);

        await waitFor(() => {
            expect(document.getElementById('story-preview-edit-button')).not.toBeNull();
        });

        expect(document.getElementById('story-editor-title')).toBeNull();
        expect(document.querySelector('.story-editor-page-card--preview')).not.toBeNull();

        fireEvent.click(document.getElementById('story-preview-edit-button'));

        await waitFor(() => {
            expect(document.getElementById('story-editor-title')).not.toBeNull();
        });

        expect(document.getElementById('story-editor-preview-button')).not.toBeNull();

        fireEvent.click(document.getElementById('story-editor-preview-button'));

        await waitFor(() => {
            expect(document.getElementById('story-preview-edit-button')).not.toBeNull();
        });

        expect(document.getElementById('story-editor-title')).toBeNull();
    });

    test('draft stories still open directly in the edit flow', async () => {
        await window.__TEST_API__.viewOrEditStory(654, true);

        expect(document.getElementById('story-creation-section').style.display).toBe('block');
        expect(document.getElementById('story-preview-section').style.display).toBe('none');
        expect(document.getElementById('story-title').value).toBe('Draft Story');
        expect(document.getElementById('generate-story-button').textContent).toBe('Finalize & Generate Story');
    });

    test('announces save state through a live region and keeps unsaved status visible', async () => {
        window.__TEST_API__.displayStory(createStoryFixture());

        const saveStatus = document.getElementById('story-editor-save-status');
        expect(saveStatus.getAttribute('role')).toBe('status');
        expect(saveStatus.getAttribute('aria-live')).toBe('polite');
        expect(saveStatus.getAttribute('aria-atomic')).toBe('true');

        const titleInput = document.getElementById('story-editor-title');
        fireEvent.input(titleInput, { target: { value: 'Edited Title' } });

        expect(saveStatus.textContent).toBe('Unsaved changes');
        expect(saveStatus.dataset.state).toBe('unsaved');
        expect(document.getElementById('story-editor-retry-save-button').style.display).toBe('none');
    });

    test('supports bounded undo and redo across title, metadata, page text, and layout edits', async () => {
        window.__TEST_API__.displayStory(createStoryFixture());

        const titleInput = document.getElementById('story-editor-title');
        const subtitleInput = document.getElementById('story-editor-cover-subtitle');
        const authorInput = document.getElementById('story-editor-cover-author');
        const layoutSelect = document.getElementById('story-editor-layout-mode');
        const pageTextarea = document.querySelector('[data-page-field="text"][data-page-id="12"]');

        expect(document.getElementById('story-editor-undo-button').disabled).toBe(true);
        expect(document.getElementById('story-editor-redo-button').disabled).toBe(true);

        fireEvent.input(titleInput, { target: { value: 'History Title' } });
        fireEvent.input(subtitleInput, { target: { value: 'History Subtitle' } });
        fireEvent.input(authorInput, { target: { value: 'History Author' } });
        fireEvent.input(layoutSelect, { target: { value: 'vertical-split' } });
        fireEvent.input(pageTextarea, { target: { value: 'History page text' } });

        expect(document.getElementById('story-editor-undo-button').disabled).toBe(false);

        fireEvent.keyDown(pageTextarea, { key: 'z', ctrlKey: true });
        expect(document.querySelector('[data-page-field="text"][data-page-id="12"]').value).toBe('Page one text');

        fireEvent.click(document.getElementById('story-editor-undo-button'));
        expect(document.getElementById('story-editor-layout-mode').value).toBe('full-page-overlay');

        fireEvent.click(document.getElementById('story-editor-undo-button'));
        expect(document.getElementById('story-editor-cover-author').value).toBe('');

        fireEvent.click(document.getElementById('story-editor-undo-button'));
        expect(document.getElementById('story-editor-cover-subtitle').value).toBe('');

        fireEvent.click(document.getElementById('story-editor-undo-button'));
        expect(document.getElementById('story-editor-title').value).toBe('Original Title');
        expect(document.getElementById('story-editor-undo-button').disabled).toBe(true);

        fireEvent.keyDown(document.getElementById('story-editor-title'), {
            key: 'z',
            ctrlKey: true,
            shiftKey: true,
        });
        expect(document.getElementById('story-editor-title').value).toBe('History Title');

        fireEvent.click(document.getElementById('story-editor-redo-button'));
        expect(document.getElementById('story-editor-cover-subtitle').value).toBe('History Subtitle');

        fireEvent.click(document.getElementById('story-editor-redo-button'));
        expect(document.getElementById('story-editor-cover-author').value).toBe('History Author');

        fireEvent.keyDown(document.getElementById('story-editor-layout-mode'), {
            key: 'y',
            ctrlKey: true,
        });
        expect(document.getElementById('story-editor-layout-mode').value).toBe('vertical-split');

        fireEvent.click(document.getElementById('story-editor-redo-button'));
        expect(document.querySelector('[data-page-field="text"][data-page-id="12"]').value).toBe('History page text');
        expect(document.getElementById('story-editor-redo-button').disabled).toBe(true);
    });

    test('bounds story editor history to the most recent 50 changes', async () => {
        window.__TEST_API__.displayStory(createStoryFixture());

        for (let index = 1; index <= 55; index += 1) {
            fireEvent.input(document.getElementById('story-editor-title'), {
                target: { value: `Title ${index}` },
            });
        }

        for (let index = 0; index < 50; index += 1) {
            fireEvent.click(document.getElementById('story-editor-undo-button'));
        }

        expect(document.getElementById('story-editor-title').value).toBe('Title 5');
        expect(document.getElementById('story-editor-undo-button').disabled).toBe(true);
    });

    test('keeps autosave coherent after undo reverts a pending title edit', async () => {
        window.__TEST_API__.displayStory(createStoryFixture());

        fireEvent.input(document.getElementById('story-editor-title'), {
            target: { value: 'Autosave edit' },
        });
        fireEvent.click(document.getElementById('story-editor-undo-button'));

        await jest.advanceTimersByTimeAsync(900);

        await waitFor(() => {
            const saveCalls = global.fetch.mock.calls.filter(
                ([url, options]) => String(url).includes('/api/v1/stories/321/editor') && String(options?.method || 'GET').toUpperCase() === 'PUT'
            );
            expect(saveCalls.length).toBeGreaterThan(0);
        });

        const latestSaveCall = [...global.fetch.mock.calls]
            .reverse()
            .find(([url, options]) => String(url).includes('/api/v1/stories/321/editor') && String(options?.method || 'GET').toUpperCase() === 'PUT');
        const payload = JSON.parse(latestSaveCall[1].body);

        expect(payload.title).toBe('Original Title');

        await waitFor(() => {
            expect(document.getElementById('story-editor-save-status').dataset.state).toBe('saved');
        });
    });

    test('keeps failed save state visible and offers retry affordance', async () => {
        const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => { });
        let saveAttempts = 0;
        saveEditorResponse = (body) => {
            saveAttempts += 1;
            if (saveAttempts === 1) {
                return {
                    ok: false,
                    status: 500,
                    json: async () => ({ detail: 'Save exploded' }),
                    headers: { get: () => 'application/json' },
                    text: async () => 'Save exploded',
                };
            }

            return createEditorPutResponse(body);
        };

        window.__TEST_API__.displayStory(createStoryFixture());

        const titleInput = document.getElementById('story-editor-title');
        fireEvent.input(titleInput, { target: { value: 'Needs retry' } });

        await jest.advanceTimersByTimeAsync(900);

        await waitFor(() => {
            const saveStatus = document.getElementById('story-editor-save-status');
            expect(saveStatus.textContent).toBe('Save failed. Retry to keep editing.');
            expect(saveStatus.dataset.state).toBe('failed');
        });

        const retryButton = document.getElementById('story-editor-retry-save-button');
        expect(retryButton.style.display).toBe('inline-flex');

        fireEvent.click(retryButton);

        await waitFor(() => {
            const saveStatus = document.getElementById('story-editor-save-status');
            expect(saveStatus.textContent).toMatch(/^Saved /);
        });

        expect(saveAttempts).toBe(2);
        expect(document.getElementById('story-editor-retry-save-button').style.display).toBe('none');
        expect(consoleErrorSpy).toHaveBeenCalled();
    });

    test('replays a queued save after a second edit lands during an in-flight save', async () => {
        const firstSave = createDeferred();
        let pendingFirstPayload = null;

        saveEditorResponse = (body) => {
            if (!pendingFirstPayload) {
                pendingFirstPayload = body;
                return firstSave.promise;
            }

            return createEditorPutResponse(body);
        };

        window.__TEST_API__.displayStory(createStoryFixture());

        const titleInput = document.getElementById('story-editor-title');
        const pageTextareas = document.querySelectorAll('[data-page-field="text"]');

        fireEvent.input(titleInput, { target: { value: 'First queued edit' } });

        await jest.advanceTimersByTimeAsync(900);

        await waitFor(() => {
            const saveCalls = global.fetch.mock.calls.filter(
                ([url, options]) => String(url).includes('/api/v1/stories/321/editor') && String(options?.method || 'GET').toUpperCase() === 'PUT'
            );
            expect(saveCalls).toHaveLength(1);
        });

        fireEvent.input(pageTextareas[1], {
            target: { value: 'Second edit queued behind the first save' },
        });

        await jest.advanceTimersByTimeAsync(900);

        const saveCallsWhilePending = global.fetch.mock.calls.filter(
            ([url, options]) => String(url).includes('/api/v1/stories/321/editor') && String(options?.method || 'GET').toUpperCase() === 'PUT'
        );
        expect(saveCallsWhilePending).toHaveLength(1);

        firstSave.resolve(createEditorPutResponse(pendingFirstPayload));

        await waitFor(() => {
            const saveCalls = global.fetch.mock.calls.filter(
                ([url, options]) => String(url).includes('/api/v1/stories/321/editor') && String(options?.method || 'GET').toUpperCase() === 'PUT'
            );
            expect(saveCalls).toHaveLength(2);
        });

        const replayCall = global.fetch.mock.calls.filter(
            ([url, options]) => String(url).includes('/api/v1/stories/321/editor') && String(options?.method || 'GET').toUpperCase() === 'PUT'
        )[1];
        const replayPayload = JSON.parse(replayCall[1].body);

        expect(replayPayload.title).toBe('First queued edit');
        expect(replayPayload.pages).toEqual(
            expect.arrayContaining([
                expect.objectContaining({
                    id: 12,
                    text: 'Second edit queued behind the first save',
                }),
            ])
        );

        await waitFor(() => {
            const saveStatus = document.getElementById('story-editor-save-status');
            expect(saveStatus.dataset.state).toBe('saved');
        });
    });

    test('returns to unsaved and remains editable after a save failure', async () => {
        const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => { });
        let saveAttempts = 0;
        saveEditorResponse = (body) => {
            saveAttempts += 1;
            if (saveAttempts === 1) {
                return {
                    ok: false,
                    status: 500,
                    json: async () => ({ detail: 'Save exploded' }),
                    headers: { get: () => 'application/json' },
                    text: async () => 'Save exploded',
                };
            }

            return createEditorPutResponse(body);
        };

        window.__TEST_API__.displayStory(createStoryFixture());

        const titleInput = document.getElementById('story-editor-title');
        fireEvent.input(titleInput, { target: { value: 'Broken save' } });

        await jest.advanceTimersByTimeAsync(900);

        await waitFor(() => {
            const saveStatus = document.getElementById('story-editor-save-status');
            expect(saveStatus.dataset.state).toBe('failed');
        });

        expect(titleInput.disabled).toBe(false);
        expect(document.getElementById('story-editor-retry-save-button').style.display).toBe('inline-flex');

        fireEvent.input(titleInput, { target: { value: 'Still editable after failure' } });

        const saveStatus = document.getElementById('story-editor-save-status');
        expect(titleInput.value).toBe('Still editable after failure');
        expect(saveStatus.textContent).toBe('Unsaved changes');
        expect(saveStatus.dataset.state).toBe('unsaved');
        expect(document.getElementById('story-editor-retry-save-button').style.display).toBe('none');
        expect(consoleErrorSpy).toHaveBeenCalled();
    });

    test('shows an error message when regenerate image fails', async () => {
        const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => { });
        pageActionResponse = () => ({
            ok: false,
            status: 500,
            json: async () => ({ detail: 'Regenerate exploded' }),
            headers: { get: () => 'application/json' },
            text: async () => 'Regenerate exploded',
        });

        window.__TEST_API__.displayStory(createStoryFixture());

        const regenerateButton = document.querySelector('[data-action="regen-image"][data-page-id="12"]');
        fireEvent.click(regenerateButton);

        await waitFor(() => {
            expect(document.getElementById('api-message').textContent).toBe('Regenerate exploded');
        });

        expect(document.getElementById('spinner').style.display).toBe('none');
        expect(consoleErrorSpy).toHaveBeenCalled();
    });

    test('updates content page preview geometry when switching between top-left and bottom-left', async () => {
        const story = createStoryFixture();
        story.editor_settings.text_position = 'middle-center';

        window.__TEST_API__.displayStory(story);

        const pagePreview = document.querySelector('.story-editor-page-preview[data-page-id="12"]');
        const textCard = pagePreview.querySelector('.story-editor-text-card');
        const verticalSelect = document.querySelector('[data-page-field="text_position_v"][data-page-id="12"]');
        const horizontalSelect = document.querySelector('[data-page-field="text_position_h"][data-page-id="12"]');

        fireEvent.input(horizontalSelect, { target: { value: 'left' } });
        fireEvent.input(verticalSelect, { target: { value: 'top' } });

        expect(textCard.style.left).toBe('5.882%');
        expect(textCard.style.width).toBe('48.000%');
        expect(textCard.style.height).toBe('22.000%');
        expect(textCard.style.top).toBe('4.545%');
        expect(textCard.style.bottom).toBe('');

        fireEvent.input(verticalSelect, { target: { value: 'bottom' } });

        expect(textCard.style.left).toBe('5.882%');
        expect(textCard.style.top).toBe('');
        expect(textCard.style.bottom).toBe('4.545%');
    });

    test('applies story-level layout mode presets to preview and save payloads', async () => {
        const story = createStoryFixture();
        delete story.editor_settings.layout_mode;

        window.__TEST_API__.displayStory(story);

        const layoutSelect = document.getElementById('story-editor-layout-mode');
        const pageStage = document.querySelector('.story-editor-page-preview[data-page-id="12"] .story-editor-page-stage');

        expect(layoutSelect.value).toBe('full-page-overlay');
        expect(pageStage.dataset.layoutMode).toBe('full-page-overlay');

        fireEvent.input(layoutSelect, { target: { value: 'vertical-split' } });

        expect(pageStage.dataset.layoutMode).toBe('vertical-split');
        expect(pageStage.style.gridTemplateColumns).toBe('1.12fr 0.88fr');

        await jest.advanceTimersByTimeAsync(900);

        await waitFor(() => {
            const saveCalls = global.fetch.mock.calls.filter(
                ([url, options]) => String(url).includes('/api/v1/stories/321/editor') && String(options?.method || 'GET').toUpperCase() === 'PUT'
            );
            expect(saveCalls.length).toBeGreaterThan(0);
        });

        const latestSaveCall = [...global.fetch.mock.calls]
            .reverse()
            .find(([url, options]) => String(url).includes('/api/v1/stories/321/editor') && String(options?.method || 'GET').toUpperCase() === 'PUT');
        const payload = JSON.parse(latestSaveCall[1].body);

        expect(payload.editor_settings.layout_mode).toBe('vertical-split');
    });

    test('applies and saves a per-page text box opacity override', async () => {
        const story = createStoryFixture();

        window.__TEST_API__.displayStory(story);

        const pagePreview = document.querySelector('.story-editor-page-preview[data-page-id="12"]');
        const textCard = pagePreview.querySelector('.story-editor-text-card');
        const opacityInput = document.querySelector('[data-page-field="text_box_opacity"][data-page-id="12"]');
        const opacityValue = document.querySelector('[data-page-opacity-value="12"]');

        expect(opacityInput).not.toBeNull();
        expect(opacityValue.textContent).toBe('60%');
        expect(textCard.style.backgroundColor).toBe('rgba(0, 0, 0, 0.6)');

        fireEvent.input(opacityInput, { target: { value: '0.3' } });

        expect(opacityValue.textContent).toBe('30%');
        expect(textCard.style.backgroundColor).toBe('rgba(0, 0, 0, 0.3)');

        await jest.advanceTimersByTimeAsync(900);

        await waitFor(() => {
            const saveCalls = global.fetch.mock.calls.filter(
                ([url, options]) => String(url).includes('/api/v1/stories/321/editor') && String(options?.method || 'GET').toUpperCase() === 'PUT'
            );
            expect(saveCalls.length).toBeGreaterThan(0);
        });

        const latestSaveCall = [...global.fetch.mock.calls]
            .reverse()
            .find(([url, options]) => String(url).includes('/api/v1/stories/321/editor') && String(options?.method || 'GET').toUpperCase() === 'PUT');
        const payload = JSON.parse(latestSaveCall[1].body);
        expect(payload.pages).toEqual(
            expect.arrayContaining([
                expect.objectContaining({
                    id: 12,
                    editor_state: expect.objectContaining({
                        text_box_opacity: 0.3,
                    }),
                }),
            ])
        );
    });

    test('applies explicit text alignment, readability treatment, and curated colour swatches', async () => {
        const story = createStoryFixture();

        window.__TEST_API__.displayStory(story);

        const storyAlignmentSelect = document.getElementById('story-editor-text-alignment');
        const readabilitySelect = document.getElementById('story-editor-readability-treatment');
        const pageAlignmentSelect = document.querySelector('[data-page-field="text_alignment"][data-page-id="12"]');
        const storyPreviewCard = document.querySelector('.story-editor-page-preview[data-page-id="12"] .story-editor-text-card');

        fireEvent.input(storyAlignmentSelect, { target: { value: 'right' } });
        fireEvent.input(readabilitySelect, { target: { value: 'High-contrast box' } });
        fireEvent.input(pageAlignmentSelect, { target: { value: 'left' } });
        fireEvent.click(document.querySelector('[data-color-swatch-target="story-editor-font-color"][data-color-value="#1f2937"]'));

        expect(storyPreviewCard.style.textAlign).toBe('left');
        expect(storyPreviewCard.dataset.readabilityTreatment).toBe('High-contrast box');
        expect(document.getElementById('story-editor-font-color').value.toLowerCase()).toBe('#1f2937');

        await jest.advanceTimersByTimeAsync(900);

        await waitFor(() => {
            const saveCalls = global.fetch.mock.calls.filter(
                ([url, options]) => String(url).includes('/api/v1/stories/321/editor') && String(options?.method || 'GET').toUpperCase() === 'PUT'
            );
            expect(saveCalls.length).toBeGreaterThan(0);
        });

        const latestSaveCall = [...global.fetch.mock.calls]
            .reverse()
            .find(([url, options]) => String(url).includes('/api/v1/stories/321/editor') && String(options?.method || 'GET').toUpperCase() === 'PUT');
        const payload = JSON.parse(latestSaveCall[1].body);

        expect(payload.editor_settings.text_alignment).toBe('right');
        expect(payload.editor_settings.readability_treatment).toBe('High-contrast box');
        expect(payload.editor_settings.font_color.toLowerCase()).toBe('#1f2937');
        expect(payload.pages).toEqual(
            expect.arrayContaining([
                expect.objectContaining({
                    id: 12,
                    editor_state: expect.objectContaining({
                        text_alignment: 'left',
                    }),
                }),
            ]),
        );
    });

    test('updates low-contrast and overflow warnings as typography changes', async () => {
        const story = createStoryFixture();

        window.__TEST_API__.displayStory(story);

        const storyColorInput = document.getElementById('story-editor-font-color');
        const readabilitySelect = document.getElementById('story-editor-readability-treatment');
        const opacityInput = document.getElementById('story-editor-text-opacity');
        const pageFontSizeInput = document.querySelector('[data-page-field="font_size"][data-page-id="12"]');
        const pageTextInput = document.querySelector('[data-page-field="text"][data-page-id="12"]');
        const warningsContainer = document.querySelector('.story-editor-page-warnings[data-page-id="12"]');

        fireEvent.input(storyColorInput, { target: { value: '#ffffff' } });
        fireEvent.input(opacityInput, { target: { value: '0.1' } });
        fireEvent.input(pageFontSizeInput, { target: { value: '56' } });
        fireEvent.input(pageTextInput, {
            target: {
                value: 'This is a deliberately long page of text that should exceed the available text box space when the font is very large. '.repeat(8),
            },
        });

        expect(warningsContainer.textContent).toContain('Low contrast warning');
        expect(warningsContainer.textContent).toContain('Text overflow warning');

        fireEvent.input(readabilitySelect, { target: { value: 'High-contrast box' } });
        fireEvent.input(storyColorInput, { target: { value: '#ffffff' } });
        fireEvent.input(pageFontSizeInput, { target: { value: '20' } });
        fireEvent.input(pageTextInput, { target: { value: 'A short readable line.' } });

        await waitFor(() => {
            expect(warningsContainer.textContent).toBe('');
        });
    });

    test('supports structural page mutations and saves an authoritative page sequence', async () => {
        const story = createStoryFixture();
        story.pages.push({
            id: 13,
            story_id: 321,
            page_number: 2,
            text: 'Page two text',
            image_description: 'Castle scene',
            image_path: 'images/user_1/story_321/page2.png',
            editor_state: {
                original_text: 'Page two text',
                original_image_path: 'images/user_1/story_321/page2.png',
            },
            created_at: '2026-04-27T12:00:00Z',
            updated_at: '2026-04-27T12:00:00Z',
        });

        window.__TEST_API__.displayStory(story);

        fireEvent.click(document.querySelector('[data-action="move-up"][data-page-id="13"]'));
        expect(document.querySelectorAll('[data-page-field="text"]')[1].value).toBe('Page two text');

        fireEvent.click(document.querySelector('[data-action="add-page"][data-page-id="13"]'));
        let textareas = [...document.querySelectorAll('[data-page-field="text"]')];
        let addedTextarea = textareas.find((input) => input.value === '');
        expect(addedTextarea).toBeTruthy();
        fireEvent.input(addedTextarea, { target: { value: 'Inserted bridge page' } });

        fireEvent.click(document.querySelector('[data-action="duplicate-page"][data-page-id="13"]'));
        expect(document.querySelectorAll('[data-page-field="text"]')).toHaveLength(5);

        const pageOneTextarea = document.querySelector('[data-page-field="text"][data-page-id="12"]');
        pageOneTextarea.setSelectionRange(4, 4);
        fireEvent.click(document.querySelector('[data-action="split-page"][data-page-id="12"]'));
        expect(document.querySelectorAll('[data-page-field="text"]')).toHaveLength(6);

        textareas = [...document.querySelectorAll('[data-page-field="text"]')];
        const insertedCard = textareas
            .find((input) => input.value === 'Inserted bridge page')
            .closest('.story-editor-page-card');
        fireEvent.click(insertedCard.querySelector('[data-action="merge-page"]'));
        expect(document.querySelectorAll('[data-page-field="text"]')).toHaveLength(5);
        expect([...document.querySelectorAll('[data-page-field="text"]')].some((input) => input.value.includes('Inserted bridge page\n\nPage'))).toBe(true);

        const duplicatedCard = [...document.querySelectorAll('.story-editor-page-card')]
            .find((card) => {
                const textarea = card.querySelector('[data-page-field="text"]');
                const pageId = Number(textarea?.dataset.pageId || '0');
                return pageId < 0 && textarea?.value === 'Page two text';
            });
        fireEvent.click(duplicatedCard.querySelector('[data-action="delete-page"]'));
        expect(document.querySelectorAll('[data-page-field="text"]')).toHaveLength(4);

        fireEvent.click(document.getElementById('story-editor-save-button'));

        await waitFor(() => {
            const saveCalls = global.fetch.mock.calls.filter(
                ([url, options]) => String(url).includes('/api/v1/stories/321/editor') && String(options?.method || 'GET').toUpperCase() === 'PUT'
            );
            expect(saveCalls.length).toBeGreaterThan(0);
        });

        const latestSaveCall = [...global.fetch.mock.calls]
            .reverse()
            .find(([url, options]) => String(url).includes('/api/v1/stories/321/editor') && String(options?.method || 'GET').toUpperCase() === 'PUT');
        const payload = JSON.parse(latestSaveCall[1].body);

        expect(payload.replace_pages).toBe(true);
        expect(payload.pages.map((page) => page.page_number)).toEqual([0, 1, 2, 3]);
        expect(payload.pages[1].text).toBe('Page two text');
        expect(payload.pages[2].text).toContain('Inserted bridge page');
        expect(payload.pages[3].text).toBe('one text');
        expect(document.querySelectorAll('.story-editor-page-card')).toHaveLength(4);
    });

    test('regenerates a single page text without replacing the rest of the story', async () => {
        pageActionResponse = (url) => {
            if (String(url).includes('/regenerate-text')) {
                return {
                    ok: true,
                    status: 200,
                    json: async () => ({
                        ...createStoryFixture().pages[1],
                        text: 'Freshly regenerated page text',
                        image_description: 'Updated prompt',
                    }),
                    headers: { get: () => 'application/json' },
                };
            }

            const story = createStoryFixture();
            return {
                ok: true,
                status: 200,
                json: async () => story.pages.find((page) => page.id === 12),
                headers: { get: () => 'application/json' },
            };
        };

        window.__TEST_API__.displayStory(createStoryFixture());

        fireEvent.click(document.querySelector('[data-action="regen-text"][data-page-id="12"]'));

        await waitFor(() => {
            expect(document.querySelector('[data-page-field="text"][data-page-id="12"]').value).toBe('Freshly regenerated page text');
        });

        expect(document.querySelector('.story-editor-page-preview[data-page-id="12"] .story-editor-text-card-content').textContent).toContain('Freshly regenerated page text');
        expect(global.fetch).toHaveBeenCalledWith(
            expect.stringContaining('/api/v1/stories/321/pages/12/regenerate-text'),
            expect.objectContaining({ method: 'POST' }),
        );
    });
});
