import { fireEvent, waitFor } from '@testing-library/dom';
import { jest } from '@jest/globals';

function setupDOM() {
    document.body.innerHTML = `
    <div id="admin-message-area"></div>
    <div id="snackbar" style="display:none"></div>
    <div id="toast-container"></div>
    <aside id="admin-sidebar"><ul>
      <li><a href="#" data-section="app-config">Application Config</a></li>
    </ul></aside>
    <section id="admin-view-panel"></section>
  `;
}

function installApiMock() {
    let configState = {
        openai_key_present: true,
        openai_key_masked: 'sk-test******',
        run_env: 'test',
        client_initialized: true,
        image_client_initialized: false,
        editable_values: {
            openai_text_provider: 'ollama',
            openai_text_base_url: 'http://localhost:11434/v1',
            openai_image_provider: 'openai',
            openai_image_base_url: 'https://api.openai.com/v1',
            text_model: 'gpt-5.4-mini',
            image_model: 'gpt-image-2',
            enable_image_generation: true,
            use_openai_responses_api: false,
            openai_text_enable_fallback: false,
            enable_image_style_mapping: true,
        },
        editable_field_metadata: {
            openai_text_provider: { label: 'Text provider', input_type: 'text', help_text: 'provider', can_clear: false },
            openai_text_base_url: { label: 'Text base URL', input_type: 'url', help_text: 'url', can_clear: true },
            openai_image_provider: { label: 'Image provider', input_type: 'text', help_text: 'provider', can_clear: false },
            openai_image_base_url: { label: 'Image base URL', input_type: 'url', help_text: 'url', can_clear: true },
            text_model: { label: 'Text model', input_type: 'text', help_text: 'model', can_clear: false },
            image_model: { label: 'Image model', input_type: 'text', help_text: 'model', can_clear: false },
            enable_image_generation: { label: 'Enable image generation', input_type: 'checkbox', help_text: 'toggle', can_clear: false },
            use_openai_responses_api: { label: 'Use OpenAI Responses API', input_type: 'checkbox', help_text: 'toggle', can_clear: false },
            openai_text_enable_fallback: { label: 'Enable text fallback', input_type: 'checkbox', help_text: 'toggle', can_clear: false },
            enable_image_style_mapping: { label: 'Enable image style mapping', input_type: 'checkbox', help_text: 'toggle', can_clear: false },
        },
        config_update_notes: [
            'Only a safe non-secret subset is editable here.',
            'Sensitive values stay masked.',
        ],
        override_storage: {
            relative_path: 'private_data/admin_config_overrides.json',
            has_overrides: false,
            applied_fields: [],
        },
    };

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

    window.fetch = jest.fn(async (url, options = {}) => {
        if (url.endsWith('/api/v1/users/me/')) {
            return new Response(
                JSON.stringify({ id: 1, username: 'admin', role: 'admin' }),
                { status: 200 }
            );
        }

        if (url.endsWith('/api/v1/admin/monitoring/config') && (!options.method || options.method === 'GET')) {
            return new Response(JSON.stringify(configState), { status: 200 });
        }

        if (url.endsWith('/api/v1/admin/monitoring/config') && options.method === 'PATCH') {
            const updatePayload = JSON.parse(options.body || '{}');
            configState = {
                ...configState,
                editable_values: {
                    ...configState.editable_values,
                    ...updatePayload,
                },
                override_storage: {
                    ...configState.override_storage,
                    has_overrides: true,
                    applied_fields: Object.keys(updatePayload),
                },
                update_summary: {
                    updated_fields: Object.keys(updatePayload),
                    cleared_fields: [],
                    persisted_fields: Object.keys(updatePayload),
                },
            };
            return new Response(JSON.stringify(configState), { status: 200 });
        }

        return new Response(JSON.stringify({ detail: 'not found' }), { status: 404 });
    });
}

async function loadAdminScript() {
    await import('../admin_script.js');
    document.dispatchEvent(new Event('DOMContentLoaded'));
}

beforeEach(() => {
    jest.resetModules();
    setupDOM();
    installApiMock();
    window.localStorage.clear();
    window.localStorage.setItem('authToken', 'test-token');
});

afterEach(() => {
    jest.resetAllMocks();
});

test('application config section renders masked diagnostics and saves safe updates', async () => {
    await loadAdminScript();
    fireEvent.click(document.querySelector('[data-section="app-config"]'));

    await waitFor(() => {
        expect(document.getElementById('app-config-form')).not.toBeNull();
    });

    expect(document.getElementById('app-config-container').textContent).toContain('sk-test******');

    const modelInput = document.getElementById('app-config-field-text_model');
    const checkbox = document.getElementById('app-config-field-enable_image_generation');
    modelInput.value = 'gpt-4.1-mini';
    checkbox.checked = false;

    fireEvent.submit(document.getElementById('app-config-form'));

    await waitFor(() => {
        expect(window.fetch).toHaveBeenCalledWith(
            expect.stringContaining('/api/v1/admin/monitoring/config'),
            expect.objectContaining({
                method: 'PATCH',
                body: JSON.stringify({
                    text_model: 'gpt-4.1-mini',
                    enable_image_generation: false,
                }),
            })
        );
    });

    await waitFor(() => { expect(document.getElementById('admin-message-area').textContent).toContain('Application config updated'); });
});

test('application config validation blocks invalid URLs before save', async () => {
    await loadAdminScript();
    fireEvent.click(document.querySelector('[data-section="app-config"]'));

    await waitFor(() => {
        expect(document.getElementById('app-config-form')).not.toBeNull();
    });

    document.getElementById('app-config-field-openai_text_base_url').value = 'ftp://invalid-host';
    fireEvent.submit(document.getElementById('app-config-form'));

    await waitFor(() => {
        expect(document.getElementById('app-config-form-errors').textContent).toContain('must use http or https');
    });

    const patchCalls = window.fetch.mock.calls.filter(
        ([url, options]) => url.endsWith('/api/v1/admin/monitoring/config') && options && options.method === 'PATCH'
    );
    expect(patchCalls).toHaveLength(0);
});