// Admin Panel Client-Side Logic - admin_script.js
console.log("admin_script.js loaded");

// Determine API_BASE_URL (same as main script.js)
let API_BASE_URL;
if (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") {
    API_BASE_URL = "http://127.0.0.1:8000"; // Local development
} else {
    API_BASE_URL = "https://story-gen-for-work.onrender.com"; // Deployed environment
}

document.addEventListener("DOMContentLoaded", function () {
    const adminMessageArea = document.getElementById("admin-message-area");
    const adminViewPanel = document.getElementById("admin-view-panel");
    const adminSidebarLinks = document.querySelectorAll("#admin-sidebar ul li a");

    const authToken = localStorage.getItem("authToken");

    if (!authToken) {
        displayAdminMessage("Access Denied. You must be logged in as an admin.", "error");
        return;
    }

    checkAdminRole();

    adminSidebarLinks.forEach(link => {
        link.addEventListener("click", function (event) {
            event.preventDefault();
            const section = this.dataset.section;
            loadAdminSection(section);
            adminSidebarLinks.forEach(l => l.classList.remove("active"));
            this.classList.add("active");
        });
    });

    async function checkAdminRole() {
        try {
            const user = await apiRequest("/users/me/");
            if (!user || user.role !== "admin") {
                displayAdminMessage("Access Denied: You do not have admin privileges.", "error");
                adminViewPanel.innerHTML = "<p>You do not have permission to view this page.</p>";
                adminSidebarLinks.forEach(link => link.style.pointerEvents = "none");
            } else {
                displayAdminMessage("Admin role verified.", "success");
                // loadAdminSection("user-management"); // Optionally load a default section
            }
        } catch (error) {
            console.error("Error verifying admin role:", error);
            displayAdminMessage("Error verifying admin role. Please try logging in again.", "error");
            adminViewPanel.innerHTML = "<p>Could not verify your admin status. Please ensure you are logged in correctly.</p>";
        }
    }

    function loadAdminSection(sectionName) {
        displayAdminMessage("");
        adminViewPanel.innerHTML = `<p>Loading ${sectionName.replace(/-/g, ' ')}...</p>`;

        switch (sectionName) {
            case "user-management":
                loadUserManagement();
                break;
            case "dynamic-content":
                loadDynamicContentManagement();
                break;
            case "content-moderation":
                adminViewPanel.innerHTML = "<h2>Content Moderation</h2><p>Functionality to review and manage user-generated stories will be here.</p>";
                break;
            case "system-monitoring":
                adminViewPanel.innerHTML = "<h2>System Monitoring</h2><p>Basic stats and log viewing capabilities will be here.</p>";
                break;
            case "app-config":
                adminViewPanel.innerHTML = "<h2>Application Configuration</h2><p>Settings for API keys, application behavior, and broadcast messages will be here.</p>";
                break;
            default:
                adminViewPanel.innerHTML = "<p>Section not found.</p>";
        }
    }

    // --- User Management Section ---
    async function loadUserManagement() {
        adminViewPanel.innerHTML = '<h2>User Management</h2><div id="user-list-table-container"></div>';
        try {
            const users = await apiRequest("/admin/users/", "GET");
            renderUserTable(users);
        } catch (error) {
            console.error("Error loading users:", error);
            displayAdminMessage("Failed to load users: " + error.message, "error");
            adminViewPanel.innerHTML += '<p class="error-message">Could not load user data.</p>';
        }
    }

    function renderUserTable(users) {
        const container = document.getElementById("user-list-table-container");
        if (!users || users.length === 0) {
            container.innerHTML = "<p>No users found.</p>";
            return;
        }

        let tableHTML = `
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Username</th>
                        <th>Email</th>
                        <th>Role</th>
                        <th>Active</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
        `;
        users.forEach(user => {
            tableHTML += `
                <tr data-user-id="${user.id}">
                    <td>${user.id}</td>
                    <td>${escapeHTML(user.username)}</td>
                    <td>${escapeHTML(user.email || 'N/A')}</td>
                    <td>${escapeHTML(user.role)}</td>
                    <td>
                        <input type="checkbox" class="user-active-checkbox" data-user-id="${user.id}" ${user.is_active ? 'checked' : ''} title="${user.is_active ? 'User is active' : 'User is inactive'}">
                    </td>
                    <td>
                        <button class="admin-button-secondary user-edit-btn" data-user-id="${user.id}">Edit Role</button>
                        </td>
                </tr>
            `;
        });
        tableHTML += '</tbody></table>';
        container.innerHTML = tableHTML;

        // Add event listeners for the new checkboxes and edit buttons
        container.querySelectorAll('.user-active-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', (event) => {
                const userId = event.target.dataset.userId;
                const isActive = event.target.checked;
                window.adminScript.toggleUserStatus(parseInt(userId), isActive);
            });
        });

        container.querySelectorAll('.user-edit-btn').forEach(button => {
            button.addEventListener('click', (event) => {
                const userId = event.target.dataset.userId;
                // Placeholder for edit role functionality - for now, just log
                console.log(`Edit role for user ID: ${userId}`);
                // Later, this could open a modal to change the user's role.
                // For now, the request was about the active checkbox and item edit mode.
                // We can implement showEditUserRoleModal(userId) here if needed.
                displayAdminMessage(`Role editing for user ${userId} not fully implemented yet.`, 'info');

            });
        });
    }

    // --- Dynamic Content Management Section ---
    async function loadDynamicContentManagement() {
        adminViewPanel.innerHTML = `
        <h2>Dynamic Content Management</h2>
        <div class="tabs">
            <button class="tab-link active" data-tab="manage-lists">Manage Lists</button>
            <button class="tab-link" data-tab="manage-items">Manage Items</button>
        </div>
        <div id="dynamic-content-lists-view" class="tab-content active">
            <h3>Dynamic Lists</h3>
            <button id="add-new-list-btn" class="admin-button">Add New List</button>
            <div id="dynamic-lists-container" class="table-responsive-container"></div>
        </div>
        <div id="dynamic-content-items-view" class="tab-content">
            <h3>Dynamic List Items</h3>
            <div class="form-group">
                <label for="select-list-for-items">Select List:</label>
                <select id="select-list-for-items"></select>
            </div>
            <button id="add-new-item-btn" class="admin-button" style="display:none;">Add New Item to Selected List</button>
            <div id="dynamic-list-items-container" class="table-responsive-container"></div>
        </div>
    `;

        setupDynamicContentTabs();
        await populateListsForManagement();
        await populateListSelectorForItems();

        document.getElementById('add-new-list-btn').addEventListener('click', () => showAddEditDynamicListModal());

        const addNewItemBtn = document.getElementById('add-new-item-btn');
        addNewItemBtn.addEventListener('click', () => {
            const selectedList = document.getElementById('select-list-for-items').value;
            if (selectedList) {
                showAddEditDynamicListItemModal(null, selectedList);
            } else {
                displayAdminMessage('Please select a list first.', 'warning');
            }
        });

        document.getElementById('select-list-for-items').addEventListener('change', (event) => {
            const listName = event.target.value;
            if (listName) {
                addNewItemBtn.style.display = 'inline-block';
                loadItemsForSelectedList(listName);
            } else {
                addNewItemBtn.style.display = 'none';
                document.getElementById('dynamic-list-items-container').innerHTML = '';
            }
        });
    }

    function setupDynamicContentTabs() {
        const tabLinks = adminViewPanel.querySelectorAll('.tab-link');
        const tabContents = adminViewPanel.querySelectorAll('.tab-content');

        tabLinks.forEach(link => {
            link.addEventListener('click', () => {
                tabLinks.forEach(l => l.classList.remove('active'));
                link.classList.add('active');

                const targetTab = link.dataset.tab;
                tabContents.forEach(content => {
                    // Corrected ID matching: e.g., targetTab 'manage-lists' -> content.id 'dynamic-content-lists-view'
                    if (content.id === `dynamic-content-${targetTab.replace('manage-', '')}-view`) {
                        content.classList.add('active');
                    } else {
                        content.classList.remove('active');
                    }
                });
            });
        });
    }

    async function populateListsForManagement() {
        const container = document.getElementById('dynamic-lists-container');
        container.innerHTML = '<p>Loading lists...</p>';
        try {
            const lists = await apiRequest("/admin/dynamic-lists/", "GET");
            if (!lists || lists.length === 0) {
                container.innerHTML = "<p>No dynamic lists found. You can add one!</p>";
                return;
            }
            let tableHTML = `
                <table>
                    <thead>
                        <tr>
                            <th>List Name</th>
                            <th>Description</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
            `;
            lists.forEach(list => {
                tableHTML += `
                    <tr>
                        <td>${escapeHTML(list.list_name)}</td>
                        <td>${escapeHTML(list.description || 'N/A')}</td>
                        <td>
                            <button class="admin-button-secondary" onclick="window.adminScript.editDynamicList('${escapeHTML(list.list_name)}')">Edit</button>
                            <button class="admin-button-danger" onclick="window.adminScript.deleteDynamicList('${escapeHTML(list.list_name)}')">Delete</button>
                        </td>
                    </tr>
                `;
            });
            tableHTML += '</tbody></table>';
            container.innerHTML = tableHTML;
        } catch (error) {
            console.error("Error loading dynamic lists:", error);
            container.innerHTML = '<p class="error-message">Failed to load dynamic lists.</p>';
            displayAdminMessage("Failed to load dynamic lists: " + error.message, "error");
        }
    }

    async function populateListSelectorForItems() {
        const selector = document.getElementById('select-list-for-items');
        selector.innerHTML = '<option value="">-- Select a List --</option>';
        try {
            const lists = await apiRequest("/admin/dynamic-lists/", "GET");
            lists.forEach(list => {
                const option = document.createElement('option');
                option.value = list.list_name;
                option.textContent = escapeHTML(list.list_name);
                selector.appendChild(option);
            });
        } catch (error) {
            console.error("Error populating list selector:", error);
            displayAdminMessage("Failed to load lists for item management: " + error.message, "error");
        }
    }

    async function loadItemsForSelectedList(listName) {
        const container = document.getElementById('dynamic-list-items-container');
        container.innerHTML = `<p>Loading items for <strong>${escapeHTML(listName)}</strong>...</p>`;
        try {
            // Fetch all items by omitting the only_active parameter
            const items = await apiRequest(`/admin/dynamic-lists/${listName}/items`, "GET");

            console.log(`Response for ${listName} items:`, items);

            if (!items || items.length === 0) {
                container.innerHTML = `<p>No items found for list: ${escapeHTML(listName)}. You can add one!</p>`;
                return;
            }

            let tableHTML = `
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Value</th>
                            <th>Label</th>
                            <th>Active</th>
                            <th>Sort Order</th>
                            <th>In Use</th>
                            <th>Additional Config</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
            `;

            const usagePromises = items.map(item =>
                apiRequest(`/admin/dynamic-list-items/${item.id}/in-use`, "GET")
                    .then(usageInfo => ({ itemId: item.id, isInUse: usageInfo.is_in_use }))
                    .catch(err => {
                        console.warn(`Could not fetch in-use status for item ${item.id}`, err);
                        return { itemId: item.id, isInUse: false };
                    })
            );
            const usageResults = await Promise.all(usagePromises);
            const usageMap = usageResults.reduce((map, current) => {
                map[current.itemId] = current.isInUse;
                return map;
            }, {});

            items.forEach(item => {
                const isInUse = usageMap[item.id] || false;
                tableHTML += `
                    <tr>
                        <td>${item.id}</td>
                        <td>${escapeHTML(item.item_value)}</td>
                        <td>${escapeHTML(item.item_label)}</td>
                        <td>
                            <button class="admin-button-${item.is_active ? 'danger' : 'success'}" onclick="window.adminScript.toggleDynamicListItemActiveStatus(${item.id}, '${escapeHTML(listName)}', ${!item.is_active})">
                                ${item.is_active ? 'Deactivate' : 'Activate'}
                            </button>
                        </td>
                        <td>${item.sort_order}</td>
                        <td><input type="checkbox" ${isInUse ? 'checked' : ''} disabled></td>
                        <td>${item.additional_config ? escapeHTML(JSON.stringify(item.additional_config)) : 'N/A'}</td>
                        <td>
                            <button class="admin-button-secondary" onclick="window.adminScript.editDynamicListItem(${item.id})">Edit</button>
                            <button class="admin-button-danger" onclick="window.adminScript.deleteDynamicListItem(${item.id}, '${escapeHTML(listName)}')">Delete</button>
                        </td>
                    </tr>
                `;
            });
            tableHTML += '</tbody></table>';
            container.innerHTML = tableHTML;
        } catch (error) {
            console.error(`Error loading items for list ${listName}:`, error);
            container.innerHTML = `<p class="error-message">Failed to load items for ${escapeHTML(listName)}.</p>`;
            displayAdminMessage(`Failed to load items for ${escapeHTML(listName)}: ` + error.message, "error");
        }
    }

    // MODAL for Dynamic List (Add/Edit)
    function showAddEditDynamicListModal(listName = null) {
        const isEdit = listName !== null;
        let currentDescription = '';

        const modalId = 'dynamicListModal';
        const existingModal = document.getElementById(modalId);
        if (existingModal) {
            existingModal.remove();
        }

        let modalHTML = `
            <div id="${modalId}" class="modal" style="display:block;">
                <div class="modal-content">
                    <span class="close-button" onclick="document.getElementById('${modalId}').remove();">&times;</span>
                    <h2>${isEdit ? 'Edit' : 'Add'} Dynamic List</h2>
                    <form id="dynamicListForm" class="admin-form">
                        <div class="form-group">
                            <label for="dl_list_name">List Name:</label>
                            <input type="text" id="dl_list_name" name="list_name" value="${isEdit ? escapeHTML(listName) : ''}" ${isEdit ? 'readonly' : 'required'}>
                        </div>
                        <div class="form-group">
                            <label for="dl_description">Description (Optional):</label>
                            <textarea id="dl_description" name="description">${isEdit ? escapeHTML(currentDescription) : ''}</textarea>
                        </div>
                        <button type="submit" class="admin-button">${isEdit ? 'Save Changes' : 'Create List'}</button>
                    </form>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', modalHTML);

        const form = document.getElementById('dynamicListForm');
        const descriptionTextarea = document.getElementById('dl_description');

        if (isEdit) {
            apiRequest(`/admin/dynamic-lists/${listName}`, "GET")
                .then(listData => {
                    if (listData && listData.description) {
                        descriptionTextarea.value = listData.description;
                    }
                })
                .catch(err => {
                    displayAdminMessage('Error fetching list details for editing: ' + err.message, 'error');
                    document.getElementById(modalId).remove();
                });
        }

        form.onsubmit = async (e) => {
            e.preventDefault();
            const formData = new FormData(form);
            const data = {
                list_name: formData.get('list_name'),
                description: formData.get('description')
            };

            try {
                if (isEdit) {
                    await apiRequest(`/admin/dynamic-lists/${listName}`, 'PUT', { description: data.description });
                    displayAdminMessage(`List '${listName}' updated.`, 'success');
                } else {
                    await apiRequest("/admin/dynamic-lists/", 'POST', data);
                    displayAdminMessage(`List '${data.list_name}' created.`, 'success');
                }
                document.getElementById(modalId).remove();
                await populateListsForManagement();
                await populateListSelectorForItems();
            } catch (error) {
                console.error("Error saving dynamic list:", error);
                displayAdminMessage("Error saving list: " + error.message, "error");
            }
        };
    }

    // MODAL for Dynamic List Item (Add/Edit)
    async function showAddEditDynamicListItemModal(itemId = null, listNameForNewItem = null) {
        const isEdit = itemId !== null;
        let itemData = null;
        let currentListName = listNameForNewItem;

        const modalId = 'dynamicListItemModal';
        const existingModal = document.getElementById(modalId);
        if (existingModal) {
            existingModal.remove();
        }

        if (isEdit) {
            try {
                itemData = await apiRequest(`/admin/dynamic-list-items/${itemId}`, "GET");
                if (!itemData) {
                    displayAdminMessage(`Error: Item ID ${itemId} not found.`, "error");
                    return;
                }
                currentListName = itemData.list_name;
            } catch (error) {
                displayAdminMessage("Error fetching item details: " + error.message, "error");
                return;
            }
        }

        const itemValue = isEdit ? itemData.item_value : '';
        const itemLabel = isEdit ? itemData.item_label : '';
        const isActive = isEdit ? itemData.is_active : true;
        const sortOrder = isEdit ? itemData.sort_order : 0;

        let additionalConfigString = '';
        let openAIStyle = 'vivid';
        if (isEdit && itemData.additional_config) {
            if (currentListName === 'image_styles' && itemData.additional_config.openai_style) {
                openAIStyle = itemData.additional_config.openai_style;
                const otherConfigs = { ...itemData.additional_config };
                delete otherConfigs.openai_style;
                if (Object.keys(otherConfigs).length > 0) {
                    additionalConfigString = JSON.stringify(otherConfigs, null, 2);
                }
            } else {
                additionalConfigString = JSON.stringify(itemData.additional_config, null, 2);
            }
        }

        let imageStyleSpecificHTML = '';
        if (currentListName === 'image_styles') {
            imageStyleSpecificHTML = `
                <div class="form-group">
                    <label for="item_openai_style">OpenAI Style Parameter (for DALL-E 'style'):</label>
                    <select id="item_openai_style" name="item_openai_style" class="admin-form-control">
                        <option value="vivid" ${openAIStyle === 'vivid' ? 'selected' : ''}>Vivid</option>
                        <option value="natural" ${openAIStyle === 'natural' ? 'selected' : ''}>Natural</option>
                    </select>
                </div>
            `;
        }

        let modalHTML = `
            <div id="${modalId}" class="modal" style="display:block;">
                <div class="modal-content">
                    <span class="close-button" onclick="document.getElementById('${modalId}').remove();">&times;</span>
                    <h2>${isEdit ? 'Edit' : 'Add'} Dynamic List Item (for List: ${escapeHTML(currentListName)})</h2>
                    <form id="dynamicListItemForm" class="admin-form">
                        <input type="hidden" id="item_list_name" name="item_list_name" value="${escapeHTML(currentListName)}">
                        <div class="form-group">
                            <label for="item_value">Item Value (unique within list):</label>
                            <input type="text" id="item_value" name="item_value" value="${escapeHTML(itemValue)}" required class="admin-form-control">
                        </div>
                        <div class="form-group">
                            <label for="item_label">Item Label (user-friendly):</label>
                            <input type="text" id="item_label" name="item_label" value="${escapeHTML(itemLabel)}" required class="admin-form-control">
                        </div>
                        <div class="form-group">
                            <label for="item_sort_order">Sort Order:</label>
                            <input type="number" id="item_sort_order" name="item_sort_order" value="${sortOrder}" required class="admin-form-control">
                        </div>
                        <div class="form-group">
                            <label for="item_is_active" style="display: inline-block; margin-right: 10px;">Is Active:</label>
                            <input type="checkbox" id="item_is_active" name="item_is_active" ${isActive ? 'checked' : ''} style="width: auto; vertical-align: middle;">
                        </div>
                        ${imageStyleSpecificHTML}
                        <div class="form-group">
                            <label for="item_additional_config">Additional Config (JSON, Optional ${currentListName === 'image_styles' ? ' - OpenAI style handled above' : ''}):</label>
                            <textarea id="item_additional_config" name="item_additional_config" rows="3" class="admin-form-control">${escapeHTML(additionalConfigString)}</textarea>
                        </div>
                        <button type="submit" class="admin-button">${isEdit ? 'Save Changes' : 'Create Item'}</button>
                    </form>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', modalHTML);

        const form = document.getElementById('dynamicListItemForm');
        form.onsubmit = async (e) => {
            e.preventDefault();
            const formData = new FormData(form);
            let additionalConfig = null;
            const additionalConfigText = formData.get('item_additional_config').trim();

            if (additionalConfigText) {
                try {
                    additionalConfig = JSON.parse(additionalConfigText);
                } catch (jsonError) {
                    displayAdminMessage("Invalid JSON in Additional Config: " + jsonError.message, "error");
                    return;
                }
            } else {
                additionalConfig = {};
            }

            if (currentListName === 'image_styles') {
                additionalConfig.openai_style = formData.get('item_openai_style');
            }
            if (Object.keys(additionalConfig).length === 0) {
                additionalConfig = null;
            }

            const data = {
                item_value: formData.get('item_value'),
                item_label: formData.get('item_label'),
                sort_order: parseInt(formData.get('item_sort_order'), 10),
                is_active: document.getElementById('item_is_active').checked,
                additional_config: additionalConfig
            };

            try {
                if (isEdit) {
                    await apiRequest(`/admin/dynamic-list-items/${itemId}`, 'PUT', data);
                    displayAdminMessage(`Item ID ${itemId} updated.`, 'success');
                } else {
                    data.list_name = formData.get('item_list_name');
                    await apiRequest(`/admin/dynamic-lists/${data.list_name}/items`, 'POST', data);
                    displayAdminMessage(`New item created in list '${data.list_name}'.`, 'success');
                }
                document.getElementById(modalId).remove();
                await loadItemsForSelectedList(currentListName);
            } catch (error) {
                console.error("Error saving dynamic list item:", error);
                let errorDetail = error.message;
                if (error.response && error.response.detail) {
                    errorDetail = typeof error.response.detail === 'string' ? error.response.detail : JSON.stringify(error.response.detail);
                }
                displayAdminMessage(`Error saving item: ${errorDetail}`, "error");
            }
        };
    }

    // Expose functions to global scope for inline onclick handlers
    window.adminScript = {
        toggleUserStatus: async function (userId, newStatus) {
            const checkbox = document.querySelector(`.user-active-checkbox[data-user-id="${userId}"]`);
            try {
                await apiRequest(`/admin/users/${userId}/status`, 'PUT', { is_active: newStatus });
                displayAdminMessage(`User ${userId} status updated successfully.`, 'success');
                // No need to call loadUserManagement() if the UI is already visually correct
                // and the server confirmed the change.
                // If newStatus is false, the checkbox is already unchecked.
                // If newStatus is true, the checkbox is already checked.
            } catch (error) {
                console.error("Error updating user status:", error);
                let userMessage = "Failed to update user status: " + error.message;
                if (error.status === 403 && error.response && error.response.detail === "Admins cannot deactivate their own account.") {
                    userMessage = "Error: Admins cannot deactivate their own account.";
                    // Revert the checkbox state if it was an attempt to deactivate self
                    if (checkbox && !newStatus) { // If tried to uncheck (deactivate)
                        checkbox.checked = true;
                    }
                } else {
                    // For other errors, also revert if possible, assuming the operation failed.
                    if (checkbox) {
                        checkbox.checked = !newStatus; // Revert to previous state
                    }
                }
                displayAdminMessage(userMessage, "error");
            }
        },
        editDynamicList: async (listName) => {
            showAddEditDynamicListModal(listName);
        },
        deleteDynamicList: async (listName) => {
            if (!confirm(`Are you sure you want to delete the list "${listName}" and all its items? This cannot be undone.`)) return;
            try {
                await apiRequest(`/admin/dynamic-lists/${listName}`, 'DELETE');
                displayAdminMessage(`List '${listName}' deleted successfully.`, 'success');
                await populateListsForManagement();
                await populateListSelectorForItems();
                document.getElementById('dynamic-list-items-container').innerHTML = '';
                const listSelector = document.getElementById('select-list-for-items');
                if (listSelector.value === listName) {
                    listSelector.value = "";
                    document.getElementById('add-new-item-btn').style.display = 'none';
                }
            } catch (error) {
                console.error("Error deleting list:", error);
                displayAdminMessage("Failed to delete list: " + error.message, "error");
            }
        },
        editDynamicListItem: async (itemId) => {
            showAddEditDynamicListItemModal(itemId);
        },
        deleteDynamicListItem: async (itemId, listName) => {
            try {
                const usageInfo = await apiRequest(`/admin/dynamic-list-items/${itemId}/in-use`, "GET");
                if (usageInfo.is_in_use) {
                    alert(`Cannot delete item ID ${itemId}. It is currently in use: ${usageInfo.details.join(', ')}`);
                    return;
                }

                if (!confirm(`Are you sure you want to delete item ID ${itemId}? This cannot be undone.`)) return;

                await apiRequest(`/admin/dynamic-list-items/${itemId}`, 'DELETE');
                displayAdminMessage(`Item ID ${itemId} deleted successfully.`, 'success');
                await loadItemsForSelectedList(listName);
            } catch (error) {
                console.error("Error deleting item:", error);
                displayAdminMessage("Failed to delete item: " + error.message, "error");
            }
        },
        toggleDynamicListItemActiveStatus: async (itemId, listName, newStatus) => {
            try {
                const itemData = await apiRequest(`/admin/dynamic-list-items/${itemId}`, "GET");
                if (!itemData) {
                    displayAdminMessage(`Error: Item ID ${itemId} not found for status update.`, "error");
                    return;
                }

                const updatePayload = {
                    item_value: itemData.item_value,
                    item_label: itemData.item_label,
                    sort_order: itemData.sort_order,
                    is_active: newStatus,
                    additional_config: itemData.additional_config
                };

                await apiRequest(`/admin/dynamic-list-items/${itemId}`, 'PUT', updatePayload);
                displayAdminMessage(`Item ID ${itemId} status updated to ${newStatus ? 'active' : 'inactive'}.`, 'success');
                await loadItemsForSelectedList(listName);
            } catch (error) {
                console.error("Error updating item status:", error);
                displayAdminMessage("Failed to update item status: " + error.message, "error");
            }
        }
    };

}); // End of DOMContentLoaded

// --- Utility Functions ---
function escapeHTML(str) {
    if (str === null || str === undefined) return '';
    return String(str).replace(/[&<>\"']/g, function (match) {
        return {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#39;'
        }[match];
    });
}

async function apiRequest(endpoint, method = 'GET', body = null) {
    const headers = {
        'Authorization': `Bearer ${localStorage.getItem('authToken')}`,
        'Content-Type': 'application/json'
    };
    const config = {
        method: method,
        headers: headers
    };
    if (body) {
        config.body = JSON.stringify(body);
    }

    const response = await fetch(API_BASE_URL + endpoint, config);

    if (!response.ok) {
        let errorData;
        try {
            errorData = await response.json();
        } catch (e) {
            // If response is not JSON, use statusText
            errorData = { message: response.statusText, detail: response.statusText };
        }
        const error = new Error(`API request failed: ${response.status}`);
        error.response = errorData;
        error.status = response.status;
        console.error(`API Error (${method} ${endpoint}):`, errorData);
        throw error;
    }
    if (response.status === 204) { // No Content
        return null;
    }
    return response.json();
}

function displayAdminMessage(message, type = 'info') {
    const messageArea = document.getElementById('admin-message-area');
    if (!messageArea) return;
    messageArea.textContent = message;

    messageArea.className = 'admin-message'; // Reset classes
    if (type) {
        messageArea.classList.add(type); // e.g., 'success', 'error', 'warning', 'info'
    }

    // Ensure styles for these classes are in admin_style.css
    // .admin-message.success { color: green; background-color: #e6ffed; border: 1px solid #b7ebc9; }
    // .admin-message.error { color: red; background-color: #ffe6e6; border: 1px solid #ffb3b3; }
    // .admin-message.warning { color: orange; background-color: #fff4e6; border: 1px solid #ffe0b3; }
    // .admin-message.info { color: blue; background-color: #e6f7ff; border: 1px solid #b3e0ff; }
    // These are examples; actual styling is in admin_style.css

    if (message) {
        messageArea.style.display = 'block';
    } else {
        messageArea.style.display = 'none';
    }
}
