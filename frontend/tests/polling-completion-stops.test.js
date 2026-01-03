import { waitFor } from '@testing-library/dom';
import { jest } from '@jest/globals';

function mountDom() {
    document.body.innerHTML = `
    <header>
      <nav><div class="nav-buttons">
        <button id="nav-login-signup" style="display:none;">Login / Sign Up</button>
        <button id="nav-create-story" style="display:none;">Create New Story</button>
        <button id="nav-browse-stories" style="display:none;">My Stories</button>
        <button id="nav-characters" style="display:none;">Characters</button>
        <a id="nav-admin-panel" href="#" style="display:none;">Admin Panel</a>
        <button id="nav-logout" style="display:none;">Logout</button>
      </div></nav>
    </header>
    <main>
      <section id="story-creation-section" style="display:block;">
        <div id="generation-progress-area" style="display:none;">
          <div id="generation-progress-bar"></div>
          <div id="generation-status-message"></div>
        </div>
      </section>
      <section id="story-preview-section" style="display:none;">
        <div id="story-preview-content"></div>
        <button id="export-pdf-button" style="display:none;"></button>
      </section>
      <div id="snackbar" style="display:none;"></div>
    </main>`;
}

describe('polling completion stops further requests', () => {
    beforeEach(() => {
        jest.useFakeTimers();
        mountDom();
        window.localStorage.setItem('authToken', 't');
    });

    afterEach(() => {
        jest.useRealTimers();
    });

    test('stops polling after completed status', async () => {
        let statusCalls = 0;

        global.fetch = jest.fn(async (url) => {
            const s = String(url);
            if (s.includes('/generation-status/')) {
                statusCalls++;
                return {
                    ok: true,
                    status: 200,
                    json: async () => ({
                        id: 'task-1',
                        story_id: 123,
                        status: statusCalls === 1 ? 'in_progress' : 'completed',
                        progress: statusCalls === 1 ? 10 : 100,
                        current_step: statusCalls === 1 ? 'initializing' : 'finalizing',
                    }),
                    headers: { get: () => 'application/json' },
                };
            }
            if (s.includes('/api/v1/stories/123')) {
                return {
                    ok: true,
                    status: 200,
                    json: async () => ({ id: 123, title: 'Done', pages: [] }),
                    headers: { get: () => 'application/json' },
                };
            }
            return {
                ok: true,
                status: 200,
                json: async () => ({}),
                headers: { get: () => 'application/json' },
            };
        });

        await import('../../frontend/script.js');
        document.dispatchEvent(new Event('DOMContentLoaded'));

        const { pollForStatus, setPollingConfig } = window.__TEST_API__ || {};
        expect(typeof pollForStatus).toBe('function');
        expect(typeof setPollingConfig).toBe('function');

        // Fast polling for the test
        setPollingConfig({ baseIntervalMs: 10, maxIntervalMs: 10, maxDurationMs: 500 });

        pollForStatus('task-1');

        // Run timers to allow second poll to happen
        await jest.advanceTimersByTimeAsync(50);

        await waitFor(() => {
            // Should have polled at least twice (in_progress then completed)
            expect(statusCalls).toBeGreaterThanOrEqual(2);
        });

        const callsAfterComplete = statusCalls;

        // Even if time advances, it should not keep polling after completion
        await jest.advanceTimersByTimeAsync(200);

        expect(statusCalls).toBe(callsAfterComplete);
    });
});
