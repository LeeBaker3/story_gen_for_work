import { fireEvent, waitFor } from '@testing-library/dom';
import { jest } from '@jest/globals';

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
                return {
                    ok: true,
                    status: 200,
                    json: async () => ({
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
                    }),
                    headers: { get: () => 'application/json' },
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
    });

    test('renders story editor and saves title/page changes', async () => {
        const story = {
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

        window.__TEST_API__.displayStory(story);

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
});
