import { fireEvent, waitFor } from '@testing-library/dom';
import { jest } from '@jest/globals';

function setupDOM() {
    document.body.innerHTML = `
    <div id="admin-message-area"></div>
    <div id="snackbar" style="display:none"></div>
    <aside id="admin-sidebar"><ul>
      <li><a href="#" data-section="system-monitoring">Monitoring</a></li>
    </ul></aside>
    <section id="admin-view-panel"></section>
  `;
}

function installApiMock({
    userRole = 'admin',
    logFiles = ['app.log'],
    logText = 'INFO startup\nERROR first failure\nWARN retrying',
}) {
    global.Response = function (body, init = {}) {
        return {
            ok: (init.status || 200) >= 200 && (init.status || 200) < 300,
            status: init.status || 200,
            json: async () => {
                try {
                    return JSON.parse(body);
                } catch {
                    return {};
                }
            },
            text: async () => body,
            headers: {
                get: (key) => (init.headers && init.headers[key]) || 'application/json',
            },
        };
    };

    window.fetch = jest.fn(async (url) => {
        if (url.endsWith('/api/v1/users/me/')) {
            return new Response(
                JSON.stringify({ id: 1, username: 'admin', role: userRole }),
                { status: 200 }
            );
        }

        if (url.endsWith('/api/v1/admin/monitoring/stats')) {
            return new Response(
                JSON.stringify({
                    server_time_utc: '2026-04-29T00:00:00Z',
                    uptime_seconds: 120,
                    platform: 'test',
                    python_version: '3.13',
                    load_average: [0.1, 0.2, 0.3],
                    disk_used_gb: 1,
                    disk_total_gb: 10,
                    disk_percent: 10,
                    logs_dir: '/tmp/logs',
                    log_files_count: logFiles.length,
                }),
                { status: 200 }
            );
        }

        if (url.endsWith('/api/v1/admin/monitoring/logs/')) {
            return new Response(JSON.stringify(logFiles), { status: 200 });
        }

        if (url.includes('/api/v1/admin/monitoring/logs/app.log?lines=')) {
            return new Response(logText, {
                status: 200,
                headers: { 'Content-Type': 'text/plain' },
            });
        }

        return new Response(JSON.stringify({ detail: 'not found' }), { status: 404 });
    });
}

async function loadAdminScript() {
    await import('../admin_script.js');
    document.dispatchEvent(new Event('DOMContentLoaded'));
}

function clickMonitoringNav() {
    fireEvent.click(document.querySelector('[data-section="system-monitoring"]'));
}

beforeEach(() => {
    jest.resetModules();
    setupDOM();
    window.localStorage.clear();
    window.localStorage.setItem('authToken', 'test-token');
});

afterEach(() => {
    jest.resetAllMocks();
});

test('log filtering always reuses the fetched raw content and clear restores it', async () => {
    installApiMock({});
    await loadAdminScript();
    clickMonitoringNav();

    await waitFor(() => {
        expect(document.getElementById('log-content').textContent).toContain(
            'ERROR first failure'
        );
    });

    const filterInput = document.getElementById('log-filter-input');
    const applyButton = document.getElementById('apply-filter-button');
    const clearButton = document.getElementById('clear-filter-button');
    const logContent = document.getElementById('log-content');

    filterInput.value = 'error';
    fireEvent.click(applyButton);

    await waitFor(() => {
        expect(logContent.textContent).toBe('ERROR first failure');
    });

    filterInput.value = 'warn';
    fireEvent.click(applyButton);

    await waitFor(() => {
        expect(logContent.textContent).toBe('WARN retrying');
    });

    fireEvent.click(clearButton);

    await waitFor(() => {
        expect(logContent.textContent).toBe(
            'INFO startup\nERROR first failure\nWARN retrying'
        );
    });
});