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
      <section id="story-preview-section" style="display:none;"></section>
      <div id="snackbar" style="display:none;"></div>
    </main>`;
}

describe('polling timeout and failure scenarios', () => {
  beforeEach(() => {
    mountDom();
    window.localStorage.setItem('authToken', 't');
  });

  test('times out and reports error after exceeding maxDuration', async () => {
    let callCount = 0;
    global.fetch = jest.fn(async (url) => {
      // Always return in_progress so it never completes
      if (String(url).includes('/generation-status/')) {
        callCount++;
        return { ok: true, status: 200, json: async () => ({ id: 'task-1', status: 'in_progress', progress: 5, current_step: 'initializing' }), headers: { get: () => 'application/json' } };
      }
      return { ok: true, status: 200, json: async () => ({}), headers: { get: () => 'application/json' } };
    });

    await import('../../frontend/script.js');
    document.dispatchEvent(new Event('DOMContentLoaded'));

    const { pollForStatus, setPollingConfig } = window.__TEST_API__ || {};
    expect(typeof pollForStatus).toBe('function');
    expect(typeof setPollingConfig).toBe('function');

    // Aggressive test settings: very short intervals & duration
    setPollingConfig({ baseIntervalMs: 10, maxIntervalMs: 20, maxDurationMs: 50 });

    pollForStatus('task-1');

    await waitFor(() => {
      const snackbar = document.getElementById('snackbar');
      expect(snackbar.style.display).toBe('block');
      expect(snackbar.textContent).toMatch(/timed out/i);
    });
    // Ensure we polled more than once
    expect(callCount).toBeGreaterThan(1);
  });

  test('stops after failure response and shows error', async () => {
    let callCount = 0;
    global.fetch = jest.fn(async (url) => {
      if (String(url).includes('/generation-status/')) {
        callCount++;
        if (callCount === 1) {
          // first call succeed
          return { ok: true, status: 200, json: async () => ({ id: 'task-2', status: 'in_progress', progress: 10, current_step: 'initializing' }), headers: { get: () => 'application/json' } };
        }
        // simulate failure (network style) by throwing
        throw new Error('Network down');
      }
      return { ok: true, status: 200, json: async () => ({}), headers: { get: () => 'application/json' } };
    });

    await import('../../frontend/script.js');
    document.dispatchEvent(new Event('DOMContentLoaded'));
    const { pollForStatus, setPollingConfig } = window.__TEST_API__ || {};
    setPollingConfig({ baseIntervalMs: 5, maxIntervalMs: 10, maxDurationMs: 200 });

    pollForStatus('task-2');

    await waitFor(() => {
      const snackbar = document.getElementById('snackbar');
      expect(snackbar.style.display).toBe('block');
      expect(snackbar.textContent).toMatch(/error occurred/i);
    });

    // After failure we should not accumulate large call counts
    expect(callCount).toBe(2);
  });
});
