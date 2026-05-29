import { fireEvent, waitFor } from '@testing-library/dom';
import { jest } from '@jest/globals';

function setupDOM() {
    document.body.innerHTML = `
    <div id="admin-message-area"></div>
    <div id="snackbar" style="display:none"></div>
    <aside id="admin-sidebar"><ul>
      <li><a href="#" data-section="dynamic-content">Dynamic Content</a></li>
    </ul></aside>
    <section id="admin-view-panel"></section>
  `;
}

beforeEach(() => {
    setupDOM();
    window.localStorage.setItem('authToken', 'test-token');
    window.__adminDynamicXssTriggered = 0;
});

afterEach(() => {
    jest.resetAllMocks();
});

function installApiMock(options = {}) {
    const initialLists = options.lists || [
        { list_name: 'genres', list_label: 'Genres', description: 'Story genres' }
    ];
    const mappingSummary = options.mappingSummary || {
        mapping_feature_enabled: true,
        default_openai_style: 'vivid',
        rules: []
    };
    const initialItemsByList = options.itemsByList || {
        genres: [
            {
                id: 5,
                list_name: 'genres',
                item_value: '<img src=x data-admin-dynamic-xss="value">',
                item_label: '" autofocus onfocus="window.__adminDynamicXssTriggered=1',
                is_active: true,
                sort_order: 1,
                additional_config: null
            }
        ]
    };
    const initialUsageByItemId = options.usageByItemId || {
        5: { is_in_use: false, details: [] }
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
                get: () => (init.headers && init.headers['Content-Type']) || 'application/json'
            }
        };
    };

    let currentLists = initialLists.map((list) => ({ ...list }));
    let currentItemsByList = Object.fromEntries(
        Object.entries(initialItemsByList).map(([listName, items]) => [
            listName,
            items.map((item) => ({ ...item }))
        ])
    );
    const usageByItemId = { ...initialUsageByItemId };

    function nextItemId() {
        return Math.max(
            0,
            ...Object.values(currentItemsByList).flat().map((item) => item.id)
        ) + 1;
    }

    window.fetch = jest.fn(async (url, options = {}) => {
        if (url.endsWith('/api/v1/users/me/')) {
            return new Response(JSON.stringify({ id: 1, username: 'admin', role: 'admin' }), { status: 200 });
        }
        if (url.endsWith('/api/v1/admin/image-style-mappings')) {
            return new Response(JSON.stringify(mappingSummary), { status: 200 });
        }
        if (url.endsWith('/api/v1/admin/dynamic-lists/')) {
            return new Response(JSON.stringify(currentLists), { status: 200 });
        }
        const listDetailMatch = url.match(/\/api\/v1\/admin\/dynamic-lists\/([^/]+)$/);
        if (listDetailMatch && (!options.method || options.method === 'GET')) {
            const listName = decodeURIComponent(listDetailMatch[1]);
            const list = currentLists.find((entry) => entry.list_name === listName);
            if (list) {
                return new Response(JSON.stringify(list), { status: 200 });
            }
        }
        if (listDetailMatch && options.method === 'DELETE') {
            const listName = decodeURIComponent(listDetailMatch[1]);
            currentLists = currentLists.filter((entry) => entry.list_name !== listName);
            delete currentItemsByList[listName];
            return new Response('', { status: 204 });
        }
        const listItemsMatch = url.match(/\/api\/v1\/admin\/dynamic-lists\/([^/]+)\/items$/);
        if (listItemsMatch && (!options.method || options.method === 'GET')) {
            const listName = decodeURIComponent(listItemsMatch[1]);
            return new Response(
                JSON.stringify(currentItemsByList[listName] || []),
                { status: 200 }
            );
        }
        if (listItemsMatch && options.method === 'POST') {
            const listName = decodeURIComponent(listItemsMatch[1]);
            const payload = JSON.parse(options.body || '{}');
            const createdItem = {
                id: nextItemId(),
                list_name: listName,
                item_value: payload.item_value,
                item_label: payload.item_label,
                is_active: payload.is_active,
                sort_order: payload.sort_order,
                additional_config: payload.additional_config ?? null
            };
            currentItemsByList[listName] = [
                ...(currentItemsByList[listName] || []),
                createdItem
            ];
            usageByItemId[createdItem.id] = { is_in_use: false, details: [] };
            return new Response(JSON.stringify(createdItem), { status: 201 });
        }
        const itemDetailMatch = url.match(/\/api\/v1\/admin\/dynamic-lists\/items\/(\d+)$/);
        if (itemDetailMatch && (!options.method || options.method === 'GET')) {
            const itemId = Number(itemDetailMatch[1]);
            const item = Object.values(currentItemsByList)
                .flat()
                .find((entry) => entry.id === itemId);
            if (item) {
                return new Response(JSON.stringify(item), { status: 200 });
            }
        }
        if (itemDetailMatch && options.method === 'PUT') {
            const itemId = Number(itemDetailMatch[1]);
            const payload = JSON.parse(options.body || '{}');
            let updatedItem = null;
            currentItemsByList = Object.fromEntries(
                Object.entries(currentItemsByList).map(([listName, items]) => [
                    listName,
                    items.map((entry) => {
                        if (entry.id !== itemId) {
                            return entry;
                        }
                        updatedItem = {
                            ...entry,
                            ...payload,
                            additional_config: payload.additional_config ?? null
                        };
                        return updatedItem;
                    })
                ])
            );
            if (updatedItem) {
                return new Response(JSON.stringify(updatedItem), { status: 200 });
            }
        }
        if (itemDetailMatch && options.method === 'DELETE') {
            const itemId = Number(itemDetailMatch[1]);
            currentItemsByList = Object.fromEntries(
                Object.entries(currentItemsByList).map(([listName, items]) => [
                    listName,
                    items.filter((entry) => entry.id !== itemId)
                ])
            );
            return new Response('', { status: 204 });
        }
        const itemUsageMatch = url.match(/\/api\/v1\/admin\/dynamic-lists\/items\/(\d+)\/in-use$/);
        if (itemUsageMatch) {
            const itemId = Number(itemUsageMatch[1]);
            return new Response(
                JSON.stringify(usageByItemId[itemId] || { is_in_use: false, details: [] }),
                { status: 200 }
            );
        }
        return new Response(JSON.stringify({ detail: 'not found' }), { status: 404 });
    });
}

async function loadAdminScript() {
    await import('../admin_script.js');
    document.dispatchEvent(new Event('DOMContentLoaded'));
}

test('dynamic list item modal escapes stored values before injecting innerHTML', async () => {
    installApiMock();

    await loadAdminScript();
    fireEvent.click(document.querySelector('[data-section="dynamic-content"]'));

    await waitFor(() => {
        expect(document.getElementById('select-list-for-items')).toBeTruthy();
    });

    await waitFor(() => {
        expect(document.querySelector('#select-list-for-items option[value="genres"]')).toBeTruthy();
    });

    fireEvent.click(document.querySelector('[data-tab="manage-items"]'));
    fireEvent.change(document.getElementById('select-list-for-items'), {
        target: { value: 'genres' }
    });

    await waitFor(() => {
        expect(document.querySelector('.edit-dynamic-list-item-btn')).toBeTruthy();
    });

    fireEvent.click(document.querySelector('.edit-dynamic-list-item-btn'));

    await waitFor(() => {
        expect(document.getElementById('dynamicListItemForm')).toBeTruthy();
    });

    const itemValueInput = document.getElementById('item_value');
    const itemLabelInput = document.getElementById('item_label');

    expect(document.querySelector('#dynamicListItemModal [data-admin-dynamic-xss="value"]')).toBeNull();
    expect(itemValueInput.value).toBe('<img src=x data-admin-dynamic-xss="value">');
    expect(itemLabelInput.value).toBe('" autofocus onfocus="window.__adminDynamicXssTriggered=1');
    expect(itemLabelInput.getAttribute('autofocus')).toBeNull();
    expect(itemLabelInput.getAttribute('onfocus')).toBeNull();

    fireEvent.focus(itemLabelInput);
    expect(window.__adminDynamicXssTriggered).toBe(0);
});

test('dynamic content renders image style mapping summary and opens rule management', async () => {
    installApiMock({
        lists: [
            { list_name: 'genres', list_label: 'Genres', description: 'Story genres' },
            {
                list_name: 'image_style_mappings',
                list_label: 'Image Style Mappings',
                description: 'Maps image styles to OpenAI style values'
            }
        ],
        itemsByList: {
            genres: [],
            image_style_mappings: [
                {
                    id: 7,
                    list_name: 'image_style_mappings',
                    item_value: 'Fantasy',
                    item_label: 'Fantasy -> Natural',
                    is_active: true,
                    sort_order: 1,
                    additional_config: { openai_style: 'natural' }
                }
            ]
        },
        usageByItemId: {
            7: { is_in_use: false, details: [] }
        },
        mappingSummary: {
            mapping_feature_enabled: true,
            default_openai_style: 'vivid',
            rules: [
                {
                    business_style: 'Fantasy',
                    image_style_item_id: 3,
                    image_style_item_label: 'Fantasy',
                    image_style_item_active: true,
                    mapping_item_id: 7,
                    mapping_item_label: 'Fantasy -> Natural',
                    mapping_item_active: true,
                    configured_openai_style: 'natural',
                    effective_openai_style: 'natural',
                    source: 'dynamic_list',
                    sort_order: 1
                }
            ]
        }
    });

    await loadAdminScript();
    fireEvent.click(document.querySelector('[data-section="dynamic-content"]'));

    await waitFor(() => {
        expect(document.getElementById('image-style-mapping-summary-container')).toBeTruthy();
        expect(document.getElementById('image-style-mapping-summary-container').textContent).toContain('Fantasy');
        expect(document.getElementById('image-style-mapping-summary-container').textContent).toContain('natural');
    });

    fireEvent.click(document.getElementById('manage-image-style-mapping-btn'));

    await waitFor(() => {
        expect(document.querySelector('[data-tab="manage-items"]').classList.contains('active')).toBe(true);
        expect(document.getElementById('select-list-for-items').value).toBe('image_style_mappings');
        expect(document.getElementById('dynamic-list-items-container').textContent).toContain('Fantasy -> Natural');
    });

    fireEvent.click(document.querySelector('.image-style-mapping-rule-action-btn'));

    await waitFor(() => {
        expect(document.getElementById('dynamicListItemForm')).toBeTruthy();
        expect(document.getElementById('item_value').value).toBe('Fantasy');
    });
});

test('dynamic list modal exposes dialog semantics and restores focus after escape', async () => {
    installApiMock();

    await loadAdminScript();
    fireEvent.click(document.querySelector('[data-section="dynamic-content"]'));

    await waitFor(() => {
        expect(document.querySelector('.edit-dynamic-list-btn')).toBeTruthy();
    });

    const triggerButton = document.getElementById('add-new-list-btn');
    window.adminScript.editDynamicList('genres', triggerButton);

    await waitFor(() => {
        expect(document.getElementById('dynamicListModal')).toBeTruthy();
    });

    const dialog = document.getElementById('dynamicListModal');
    const title = dialog.querySelector('h2');
    const listLabelInput = document.getElementById('dl_list_label');

    expect(dialog.getAttribute('role')).toBe('dialog');
    expect(dialog.getAttribute('aria-modal')).toBe('true');
    expect(dialog.getAttribute('aria-labelledby')).toBe(title.id);
    expect(document.activeElement).toBe(listLabelInput);

    fireEvent.keyDown(dialog, { key: 'Escape' });

    await waitFor(() => {
        expect(document.getElementById('dynamicListModal')).toBeNull();
    });
    expect(document.activeElement).toBe(triggerButton);
});

test('dynamic list delete uses admin confirmation modal before removing the list', async () => {
    const confirmSpy = jest.spyOn(window, 'confirm').mockImplementation(() => true);
    installApiMock();

    await loadAdminScript();
    fireEvent.click(document.querySelector('[data-section="dynamic-content"]'));

    await waitFor(() => {
        expect(document.querySelector('.edit-dynamic-list-btn')).toBeTruthy();
    });

    fireEvent.click(document.querySelector('.edit-dynamic-list-btn'));

    await waitFor(() => {
        expect(document.getElementById('deleteDynamicListButton')).toBeTruthy();
    });

    fireEvent.click(document.getElementById('deleteDynamicListButton'));

    await waitFor(() => {
        expect(document.querySelector('[id^="adminActionDialog-"]')).toBeTruthy();
    });

    const dialog = document.querySelector('[id^="adminActionDialog-"]');
    expect(dialog.textContent).toContain("Delete list 'genres'?");
    fireEvent.click(dialog.querySelector('.admin-button-danger'));

    await waitFor(() => {
        expect(document.querySelector('.edit-dynamic-list-btn')).toBeNull();
    });

    expect(confirmSpy).not.toHaveBeenCalled();
});

test('dynamic list item edit modal proactively shows usage details and disables delete when in use', async () => {
    installApiMock({
        usageByItemId: {
            5: { is_in_use: true, details: ['story template', 'featured prompt'] }
        }
    });

    await loadAdminScript();
    fireEvent.click(document.querySelector('[data-section="dynamic-content"]'));

    await waitFor(() => {
        expect(typeof window.adminScript.showAddEditDynamicListItemModal)
            .toBe('function');
    });

    await window.adminScript.showAddEditDynamicListItemModal(
        5,
        null,
        document.getElementById('add-new-item-btn')
    );

    await waitFor(() => {
        expect(document.getElementById('deleteDynamicListItemButton')).toBeTruthy();
    });

    const usageStatus = document.getElementById('dynamicListItemModal-usage-status');
    const deleteButton = document.getElementById('deleteDynamicListItemButton');

    expect(usageStatus).toBeTruthy();
    expect(usageStatus.textContent).toContain('This item is currently in use and cannot be deleted.');
    expect(usageStatus.textContent).toContain('Referenced by:');
    expect(usageStatus.textContent).toContain('story template');
    expect(usageStatus.textContent).toContain('featured prompt');
    expect(deleteButton.disabled).toBe(true);
    expect(deleteButton.getAttribute('aria-describedby')).toBe('dynamicListItemModal-usage-status');
});

test('dynamic list item delete uses admin confirmation modal before removing the item', async () => {
    const confirmSpy = jest.spyOn(window, 'confirm').mockImplementation(() => true);
    installApiMock();

    await loadAdminScript();
    fireEvent.click(document.querySelector('[data-section="dynamic-content"]'));

    await waitFor(() => {
        expect(typeof window.adminScript.showAddEditDynamicListItemModal)
            .toBe('function');
    });

    await window.adminScript.showAddEditDynamicListItemModal(
        5,
        null,
        document.getElementById('add-new-item-btn')
    );

    await waitFor(() => {
        expect(document.getElementById('deleteDynamicListItemButton')).toBeTruthy();
    });

    expect(document.getElementById('dynamicListItemModal-usage-status').textContent)
        .toContain('This item is not currently referenced and can be deleted.');
    expect(document.getElementById('deleteDynamicListItemButton').disabled).toBe(false);

    fireEvent.click(document.getElementById('deleteDynamicListItemButton'));

    await waitFor(() => {
        expect(document.querySelector('[id^="adminActionDialog-"]')).toBeTruthy();
    });

    const dialog = document.querySelector('[id^="adminActionDialog-"]');
    expect(dialog.textContent).toContain('Delete item 5?');
    fireEvent.click(dialog.querySelector('.admin-button-danger'));

    await waitFor(() => {
        expect(document.querySelector('.edit-dynamic-list-item-btn')).toBeNull();
    });

    expect(confirmSpy).not.toHaveBeenCalled();
});

test('dynamic list item modal submits create and edit payloads to the admin API', async () => {
    installApiMock();

    await loadAdminScript();
    fireEvent.click(document.querySelector('[data-section="dynamic-content"]'));

    await waitFor(() => {
        expect(typeof window.adminScript.showAddEditDynamicListItemModal)
            .toBe('function');
    });

    await window.adminScript.showAddEditDynamicListItemModal(
        null,
        'genres',
        document.getElementById('add-new-item-btn')
    );

    await waitFor(() => {
        expect(document.getElementById('dynamicListItemForm')).toBeTruthy();
    });

    fireEvent.change(document.getElementById('item_value'), {
        target: { value: 'mystery' }
    });
    fireEvent.change(document.getElementById('item_label'), {
        target: { value: 'Mystery' }
    });
    fireEvent.change(document.getElementById('item_sort_order'), {
        target: { value: '7' }
    });
    fireEvent.click(document.getElementById('item_is_active'));
    fireEvent.change(document.getElementById('item_additional_config'), {
        target: { value: '{"openai_style":"vivid"}' }
    });
    fireEvent.submit(document.getElementById('dynamicListItemForm'));

    let createCall;
    await waitFor(() => {
        createCall = window.fetch.mock.calls.find(([url, requestOptions]) => (
            String(url).endsWith('/api/v1/admin/dynamic-lists/genres/items')
            && requestOptions?.method === 'POST'
        ));
        expect(createCall).toBeTruthy();
    });

    expect(JSON.parse(createCall[1].body)).toEqual({
        list_name: 'genres',
        item_value: 'mystery',
        item_label: 'Mystery',
        sort_order: 7,
        is_active: false,
        additional_config: { openai_style: 'vivid' }
    });

    await window.adminScript.showAddEditDynamicListItemModal(
        5,
        null,
        document.querySelector('.edit-dynamic-list-item-btn')
    );

    await waitFor(() => {
        expect(document.getElementById('dynamicListItemForm')).toBeTruthy();
        expect(document.getElementById('item_value').value).toBe('<img src=x data-admin-dynamic-xss="value">');
    });

    fireEvent.change(document.getElementById('item_value'), {
        target: { value: 'spooky' }
    });
    fireEvent.change(document.getElementById('item_label'), {
        target: { value: 'Spooky label' }
    });
    fireEvent.change(document.getElementById('item_sort_order'), {
        target: { value: '9' }
    });
    fireEvent.change(document.getElementById('item_additional_config'), {
        target: { value: '{"openai_style":"natural"}' }
    });
    fireEvent.submit(document.getElementById('dynamicListItemForm'));

    let updateCall;
    await waitFor(() => {
        updateCall = window.fetch.mock.calls.find(([url, requestOptions]) => (
            String(url).endsWith('/api/v1/admin/dynamic-lists/items/5')
            && requestOptions?.method === 'PUT'
        ));
        expect(updateCall).toBeTruthy();
    });

    expect(JSON.parse(updateCall[1].body)).toEqual({
        item_value: 'spooky',
        item_label: 'Spooky label',
        sort_order: 9,
        is_active: true,
        additional_config: { openai_style: 'natural' }
    });
});