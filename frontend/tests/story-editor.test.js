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
    return {
        id: 321,
        title: body.title,
        genre: 'Fantasy',
        story_outline: 'Outline',
        main_characters: [],
        num_pages: 2,
        tone: null,
        setting: null,
        image_style: 'Default',
        word_to_picture_ratio: 'One image per page',
        text_density: 'Concise (~30-50 words)',
        editor_settings: body.editor_settings,
        pages: [
            {
                id: 11,
                story_id: 321,
                page_number: 0,
                text: body.title,
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
                text: body.pages?.find((page) => page.id === 12)?.text || 'Page one text',
                image_description: 'Dragon scene',
                image_path: 'images/user_1/story_321/page1.png',
                editor_state: {
                    original_text: 'Page one text',
                    original_image_path: 'images/user_1/story_321/page1.png',
                    ...(body.pages?.find((page) => page.id === 12)?.editor_state || {}),
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
            text_box_opacity: 0.6,
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
      </section>
      <section id="story-creation-section" style="display:none;">
        <form id="story-creation-form"></form>
        <fieldset id="main-characters-fieldset"></fieldset>
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
        <button id="export-pdf-button" style="display:none;">Export</button>
      </section>
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
        jest.spyOn(window.URL, 'revokeObjectURL').mockImplementation(() => {});

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

            if (value.includes('/api/v1/stories/321/pages/11/image') || value.includes('/api/v1/stories/321/pages/12/image')) {
                return {
                    ok: true,
                    status: 200,
                    blob: async () => new Blob(['image-bytes'], { type: 'image/png' }),
                    headers: { get: (name) => name === 'content-type' ? 'image/png' : null },
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
        expect(titleInput).not.toBeNull();
        expect(document.querySelectorAll('.story-editor-page-card').length).toBe(2);

        fireEvent.input(titleInput, { target: { value: 'Edited Title' } });
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

        expect(document.getElementById('export-pdf-button').style.display).toBe('inline-block');
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

    test('keeps failed save state visible and offers retry affordance', async () => {
        const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
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
        const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
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
        const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
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
});
