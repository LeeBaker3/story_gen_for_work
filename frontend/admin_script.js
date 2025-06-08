// Admin Panel Client-Side Logic - admin_script.js
console.log(\"admin_script.js loaded\");

// Determine API_BASE_URL (same as main script.js)
let API_BASE_URL;
if (window.location.hostname === \"localhost\" || window.location.hostname === \"127.0.0.1\") {
API_BASE_URL = \"http://127.0.0.1:8000\"; // Local development
} else {
    API_BASE_URL = \"https://story-gen-for-work.onrender.com\"; // Deployed environment
}

document.addEventListener(\"DOMContentLoaded\", function () {
    const adminMessageArea = document.getElementById(\"admin-message-area\");
    const adminViewPanel = document.getElementById(\"admin-view-panel\");
    const adminSidebarLinks = document.querySelectorAll(\"#admin-sidebar ul li a\");

    const authToken = localStorage.getItem(\"authToken\");

    if (!authToken) {
    displayAdminMessage(\"Access Denied. You must be logged in as an admin.\", \"error\");
        // Optionally redirect to main login page or hide admin content
        // window.location.href = \"index.html\"; // Example redirect
        return;
}

// Verify admin role on page load
checkAdminRole();

adminSidebarLinks.forEach(link => {
    link.addEventListener(\"click\", function (event) {
            event.preventDefault();
    const section = this.dataset.section;
    loadAdminSection(section);
    // Highlight active link
    adminSidebarLinks.forEach(l => l.classList.remove(\"active\"));
            this.classList.add(\"active\");
        });
    });

async function checkAdminRole() {
    try {
        const user = await apiRequest(\"/users/me/\"); // Uses the main app\'s token
            if (!user || user.role !== \"admin\") {
        displayAdminMessage(\"Access Denied: You do not have admin privileges.\", \"error\");
                // Disable admin panel functionality
                adminViewPanel.innerHTML = \"<p>You do not have permission to view this page.</p>\";
                adminSidebarLinks.forEach(link => link.style.pointerEvents = \"none\");
            } else {
        displayAdminMessage(\"Admin role verified.\", \"success\");
                // Load a default section if needed, e.g., user management
                // loadAdminSection(\"user-management\"); 
            }
} catch (error) {
    console.error(\"Error verifying admin role:\", error);
            displayAdminMessage(\"Error verifying admin role. Please try logging in again.\", \"error\");
            adminViewPanel.innerHTML = \"<p>Could not verify your admin status. Please ensure you are logged in correctly.</p>\";
        }
    }


function loadAdminSection(sectionName) {
    displayAdminMessage(\"\"); // Clear previous messages
        adminViewPanel.innerHTML = \`<p>Loading ${sectionName.replace(/-/g, \' \')}...</p>\`;

        switch (sectionName) {
        case \"user-management\":
            loadUserManagement();
            break;
        case \"dynamic-content\":
            loadDynamicContentManagement();
            break;
        case \"content-moderation\":
            // Placeholder for Content Moderation
            adminViewPanel.innerHTML = \"<h2>Content Moderation</h2><p>Functionality to review and manage user-generated stories will be here.</p>\";
            break;
        case \"system-monitoring\":
            // Placeholder for System Monitoring
            adminViewPanel.innerHTML = \"<h2>System Monitoring</h2><p>Basic stats and log viewing capabilities will be here.</p>\";
            break;
        case \"app-config\":
            // Placeholder for Application Configuration
            adminViewPanel.innerHTML = \"<h2>Application Configuration</h2><p>Settings for API keys, application behavior, and broadcast messages will be here.</p>\";
            break;
        default:
            adminViewPanel.innerHTML = \"<p>Section not found.</p>\";
    }
}

// --- User Management Section ---
async function loadUserManagement() {
    adminViewPanel.innerHTML = \'<h2>User Management</h2><div id=\"user-list-table-container\"></div>\';
    try {
        const users = await apiRequest(\"/admin/users/\", \"GET\"); // Assuming this endpoint exists from Phase 2
            renderUserTable(users);
    } catch (error) {
        console.error(\"Error loading users:\", error);
            displayAdminMessage(\"Failed to load users: \" + error.message, \"error\");
            adminViewPanel.innerHTML += \'<p class=\"error-message\">Could not load user data.</p>\';
        }
}

function renderUserTable(users) {
    const container = document.getElementById(\"user-list-table-container\");
        if (!users || users.length === 0) {
        container.innerHTML = \"<p>No users found.</p>\";
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
                <tr>
                    <td>${user.id}</td>
                    <td>${escapeHTML(user.username)}</td>
                    <td>${escapeHTML(user.email || \'N/A\')}</td>
            < td > ${ escapeHTML(user.role)}</td>
                    <td>${user.is_active ?\'Yes\' : \'No\'}</td>
            < td >
            <button class=\"admin-button-secondary\" onclick=\"toggleUserStatus(${user.id}, ${!user.is_active})\">${user.is_active ? \'Deactivate\' : \'Activate\'}</button>
                < !--Add more actions like delete, change role later-- >
                    </td >
                </tr >
            `;
        });
        tableHTML += \'</tbody></table>\';
        container.innerHTML = tableHTML;
    }
    
    window.toggleUserStatus = async function(userId, newStatus) {
        // Expose to global scope for inline onclick
        try {
            await apiRequest(`/ admin / users / ${ userId }/status`, \'PUT\', { is_active: newStatus });
    displayAdminMessage(`User ${userId} status updated successfully.`, \'success\');
            loadUserManagement(); // Refresh table
} catch (error) {
    console.error(\"Error updating user status:\", error);
            displayAdminMessage(\"Failed to update user status: \" + error.message, \"error\");
        }
    };


// --- Dynamic Content Management Section ---
async function loadDynamicContentManagement() {
    adminViewPanel.innerHTML = \'<h2>Dynamic Content Management</h2>\';
    adminViewPanel.innerHTML += \`
            <div class=\"tabs\">
                <button class=\"tab-link active\" data-tab=\"manage-lists\">Manage Lists</button>
                <button class=\"tab-link\" data-tab=\"manage-items\">Manage Items</button>
            </div>
            <div id=\"dynamic-content-lists-view\" class=\"tab-content active\">
                <h3>Dynamic Lists</h3>
                <button id=\"add-new-list-btn\" class=\"admin-button\">Add New List</button>
                <div id=\"dynamic-lists-container\"></div>
            </div>
            <div id=\"dynamic-content-items-view\" class=\"tab-content\">
                <h3>Dynamic List Items</h3>
                <div class=\"form-group\">
                    <label for=\"select-list-for-items\">Select List:</label>
                    <select id=\"select-list-for-items\"></select>
                </div>
                <button id=\"add-new-item-btn\" class=\"admin-button\" style=\"display:none;\">Add New Item to Selected List</button>
                <div id=\"dynamic-list-items-container\"></div>
            </div>
        \`;
        
        setupDynamicContentTabs();
        await populateListsForManagement(); // For the "Manage Lists" tab
        await populateListSelectorForItems(); // For the "Manage Items" tab dropdown

        document.getElementById(\'add-new-list-btn\').addEventListener(\'click\', () => showAddEditDynamicListModal());
        document.getElementById(\'add-new-item-btn\').addEventListener(\'click\', () => {
            const selectedList = document.getElementById(\'select-list-for-items\').value;
            if (selectedList) {
                showAddEditDynamicListItemModal(null, selectedList);
            } else {
                displayAdminMessage(\'Please select a list first.\', \'warning\');
            }
        });
        document.getElementById(\'select-list-for-items\').addEventListener(\'change\', (event) => {
            const listName = event.target.value;
            if (listName) {
                document.getElementById(\'add-new-item-btn\').style.display = \'inline-block\';
                loadItemsForSelectedList(listName);
            } else {
                document.getElementById(\'add-new-item-btn\').style.display = \'none\';
                document.getElementById(\'dynamic-list-items-container\').innerHTML = \'\';
            }
        });
    }

    function setupDynamicContentTabs() {
        const tabLinks = adminViewPanel.querySelectorAll(\'.tab-link\');
        const tabContents = adminViewPanel.querySelectorAll(\'.tab-content\');

        tabLinks.forEach(link => {
            link.addEventListener(\'click\', () => {
                tabLinks.forEach(l => l.classList.remove(\'active\'));
                link.classList.add(\'active\');

                const targetTab = link.dataset.tab;
                tabContents.forEach(content => {
                    if (content.id === \`dynamic-content-${targetTab === \'manage-lists\' ? \'lists\' : \'items\'}-view\`) {
    content.classList.add(\'active\');
                    } else {
    content.classList.remove(\'active\');
                    }
                });
            });
        });
    }

async function populateListsForManagement() {
    const container = document.getElementById(\'dynamic-lists-container\');
        container.innerHTML = \'<p>Loading lists...</p>\';
        try {
        const lists = await apiRequest(\"/admin/dynamic-lists/\", \"GET\");
            if (!lists || lists.length === 0) {
            container.innerHTML = \"<p>No dynamic lists found. You can add one!</p>\";
            return;
        }
        let html = \'<table><thead><tr><th>List Name</th><th>Description</th><th>Actions</th></tr></thead><tbody>\';
        lists.forEach(list => {
            html += `
                    <tr>
                        <td>${escapeHTML(list.list_name)}</td>
                        <td>${escapeHTML(list.description || \'N/A\')}</td>
                < td >
                <button class=\"admin-button-secondary\" onclick=\"window.adminScript.editDynamicList(\'${escapeHTML(list.list_name)}\')\">Edit</button>
            < button class=\"admin-button-danger\" onclick=\"window.adminScript.deleteDynamicList(\'${escapeHTML(list.list_name)}\')\">Delete</button>
                        </td >
                    </tr >
                `;
            });
            html += \'</tbody></table>\';
            container.innerHTML = html;
        } catch (error) {
            console.error(\"Error loading dynamic lists:\", error);
            container.innerHTML = \'<p class=\"error-message\">Failed to load dynamic lists.</p>\';
            displayAdminMessage(\"Failed to load dynamic lists: \" + error.message, \"error\");
        }
    }
    
    async function populateListSelectorForItems() {
        const selector = document.getElementById(\'select-list-for-items\');
        selector.innerHTML = \'<option value=\"\">-- Select a List --</option>\';
        try {
            const lists = await apiRequest(\"/admin/dynamic-lists/\", \"GET\");
            lists.forEach(list => {
                const option = document.createElement(\'option\');
                option.value = list.list_name;
                option.textContent = list.list_name;
                selector.appendChild(option);
            });
        } catch (error) {
            console.error(\"Error populating list selector:\", error);
            displayAdminMessage(\"Failed to load lists for item management: \" + error.message, \"error\");
        }
    }

    async function loadItemsForSelectedList(listName) {
        const container = document.getElementById(\'dynamic-list-items-container\');
        container.innerHTML = \`<p>Loading items for <strong>${escapeHTML(listName)}</strong>...</p>\`;
        try {
            // Admin should see all items, active or not
            const items = await apiRequest(`/ admin / dynamic - lists / ${ listName } / items ? only_active = false`, \"GET\");
            if (!items || items.length === 0) {
                container.innerHTML = \`<p>No items found for list: ${escapeHTML(listName)}. You can add one!</p>\`;
                return;
            }
            let html = \'<table><thead><tr><th>ID</th><th>Value</th><th>Label</th><th>Active</th><th>Sort Order</th><th>Config</th><th>Actions</th></tr></thead><tbody>\';
            items.forEach(item => {
                html += `
                < tr >
                        <td>${item.id}</td>
                        <td>${escapeHTML(item.item_value)}</td>
                        <td>${escapeHTML(item.item_label)}</td>
                        <td>${item.is_active ? \'Yes\' : \'No\'}</td>
                        <td>${item.sort_order}</td>
                        <td>${item.additional_config ? escapeHTML(JSON.stringify(item.additional_config)) : \'N/A\'}</td>
                        <td>
                            <button class=\"admin-button-secondary\" onclick=\"window.adminScript.editDynamicListItem(${item.id})\">Edit</button>
                            <button class=\"admin-button-danger\" onclick=\"window.adminScript.deleteDynamicListItem(${item.id}, \'${escapeHTML(listName)}\')\">Delete</button>
            < button class=\"admin-button\" onclick=\"window.adminScript.checkItemInUse(${item.id})\">Check Usage</button>
                        </td >
                    </tr >
                `;
            });
            html += \'</tbody></table>\';
            container.innerHTML = html;
        } catch (error) {
            console.error(`Error loading items for list ${ listName }: `, error);
            container.innerHTML = \`<p class=\"error-message\">Failed to load items for ${escapeHTML(listName)}.</p>\`;
            displayAdminMessage(`Failed to load items for ${ escapeHTML(listName) }: ` + error.message, \"error\");
        }
    }

    // MODAL for Dynamic List (Add/Edit)
    function showAddEditDynamicListModal(listData = null) {
        const isEdit = listData !== null;
        const listName = isEdit ? listData.list_name : \'\';
        const description = isEdit ? listData.description : \'\';

        let modalHTML = `
                < div id =\"dynamicListModal\" class=\"modal\" style=\"display:block;\">
                    < div class=\"modal-content\">
                        < span class=\"close-button\" onclick=\"document.getElementById(\'dynamicListModal\').style.display=\'none\'\">&times;</span>
                            < h2 > ${
                                isEdit ?\'Edit\' : \'Add\'} Dynamic List</h2>
                                    < form id =\"dynamicListForm\" class=\"admin-form\">
                                        < div class=\"form-group\">
                                            < label for=\"list_name\">List Name:</label>
                                                < input type =\"text\" id=\"list_name\" name=\"list_name\" value=\"${escapeHTML(listName)}\" ${isEdit ? \'readonly\' : \'required\'}>
                        </div >
                    <div class=\"form-group\">
                        < label for=\"description\">Description (Optional):</label>
                            < textarea id =\"description\" name=\"description\">${escapeHTML(description)}</textarea>
                        </div >
                    <button type=\"submit\" class=\"admin-button\">${isEdit ? \'Save Changes\' : \'Create List\'}</button>
                    </form >
                </div >
            </div >
                    `;
        // Append modal to body or a specific modal container
        document.body.insertAdjacentHTML(\'beforeend\', modalHTML);
        
        const form = document.getElementById(\'dynamicListForm\');
        form.onsubmit = async (e) => {
            e.preventDefault();
            const formData = new FormData(form);
            const data = {
                list_name: formData.get(\'list_name\'),
                description: formData.get(\'description\')
            };

            try {
                if (isEdit) {
                    // Update logic - API does not support changing list_name, only description
                    await apiRequest(`/ admin / dynamic - lists / ${ listName } `, \'PUT\', { description: data.description }); 
                    displayAdminMessage(`List \'${listName}\' updated.`, \'success\');
            } else {
                await apiRequest(\"/admin/dynamic-lists/\", \'POST\', data);
                    displayAdminMessage(`List \'${data.list_name}\' created.`, \'success\');
                }
            document.getElementById(\'dynamicListModal\').remove();
                await populateListsForManagement(); // Refresh lists table
            await populateListSelectorForItems(); // Refresh dropdown for items tab
        } catch (error) {
            console.error(\"Error saving dynamic list:\", error);
                displayAdminMessage(\"Error saving list: \" + error.message, \"error\");
            }
    };
    // Close modal if already exists
    const existingModal = document.getElementById(\'dynamicListModal\');
        if (existingModal && existingModal !== form.closest(\'.modal\')) {
            existingModal.remove();
}
    }

// MODAL for Dynamic List Item (Add/Edit)
async function showAddEditDynamicListItemModal(itemData = null, listNameForNewItem = null) {
    const isEdit = itemData !== null;
    const itemId = isEdit ? itemData.id : null;
    const listName = isEdit ? itemData.list_name : listNameForNewItem;
    const itemValue = isEdit ? itemData.item_value : \'\';
    const itemLabel = isEdit ? itemData.item_label : \'\';
    const isActive = isEdit ? itemData.is_active : true;
    const sortOrder = isEdit ? itemData.sort_order : 0;
    const additionalConfig = isEdit && itemData.additional_config ? JSON.stringify(itemData.additional_config, null, 2) : \'\';


    let modalHTML = `
            <div id=\"dynamicListItemModal\" class=\"modal\" style=\"display:block;\">
                <div class=\"modal-content\">
                    <span class=\"close-button\" onclick=\"document.getElementById(\'dynamicListItemModal\').style.display=\'none\'\">&times;</span>
                    <h2>${isEdit ?\'Edit\' : \'Add\'} Dynamic List Item (for List: ${escapeHTML(listName)})</h2>
        < form id =\"dynamicListItemForm\" class=\"admin-form\">
            < input type =\"hidden\" id=\"item_list_name\" name=\"item_list_name\" value=\"${escapeHTML(listName)}\">
                < div class=\"form-group\">
                    < label for=\"item_value\">Item Value (unique within list):</label>
                        < input type =\"text\" id=\"item_value\" name=\"item_value\" value=\"${escapeHTML(itemValue)}\" required>
                        </div >
        <div class=\"form-group\">
            < label for=\"item_label\">Item Label (user-friendly):</label>
                < input type =\"text\" id=\"item_label\" name=\"item_label\" value=\"${escapeHTML(itemLabel)}\" required>
                        </div >
        <div class=\"form-group\">
            < label for=\"item_sort_order\">Sort Order:</label>
                < input type =\"number\" id=\"item_sort_order\" name=\"item_sort_order\" value=\"${sortOrder}\" required>
                        </div >
        <div class=\"form-group\">
            < label for=\"item_is_active\">Is Active:</label>
                < input type =\"checkbox\" id=\"item_is_active\" name=\"item_is_active\" ${isActive ? \'checked\' : \'\'}>
                        </div >
        <div class=\"form-group\">
            < label for=\"item_additional_config\">Additional Config (JSON, Optional):</label>
                < textarea id =\"item_additional_config\" name=\"item_additional_config\" rows=\"3\">${escapeHTML(additionalConfig)}</textarea>
                        </div >
        <button type=\"submit\" class=\"admin-button\">${isEdit ? \'Save Changes\' : \'Create Item\'}</button>
                    </form >
                </div >
            </div >
        `;
        document.body.insertAdjacentHTML(\'beforeend\', modalHTML);

        const form = document.getElementById(\'dynamicListItemForm\');
        form.onsubmit = async (e) => {
            e.preventDefault();
            const formData = new FormData(form);
            let configJson = null;
            if (formData.get(\'item_additional_config\').trim()) {
                try {
                    configJson = JSON.parse(formData.get(\'item_additional_config\'));
                } catch (jsonError) {
                    displayAdminMessage(\"Invalid JSON in Additional Config: \" + jsonError.message, \"error\");
                    return;
                }
            }

            const data = {
                item_value: formData.get(\'item_value\'),
                item_label: formData.get(\'item_label\'),
                sort_order: parseInt(formData.get(\'item_sort_order\'), 10),
                is_active: document.getElementById(\'item_is_active\').checked,
                additional_config: configJson
            };

            try {
                if (isEdit) {
                    await apiRequest(`/ admin / dynamic - lists / items / ${ itemId } `, \'PUT\', data);
                    displayAdminMessage(`Item ID ${ itemId } updated.`, \'success\');
                } else {
                    data.list_name = formData.get(\'item_list_name\'); // Add list_name for creation
                    await apiRequest(`/ admin / dynamic - lists / ${ data.list_name }/items`, \'POST\', data);
    displayAdminMessage(`New item created in list \'${data.list_name}\'.`, \'success\');
                }
document.getElementById(\'dynamicListItemModal\').remove();
                await loadItemsForSelectedList(listName); // Refresh items table for the current list
            } catch (error) {
    console.error(\"Error saving dynamic list item:\", error);
                displayAdminMessage(\"Error saving item: \" + error.message, \"error\");
            }
        };
const existingModal = document.getElementById(\'dynamicListItemModal\');
        if (existingModal && existingModal !== form.closest(\'.modal\')) {
            existingModal.remove();
        }
    }

// Expose functions to global scope for inline onclick handlers
window.adminScript = {
    editDynamicList: async (listName) => {
        try {
            const listData = await apiRequest(`/admin/dynamic-lists/${listName}`, \"GET\");
                showAddEditDynamicListModal(listData);
        } catch (error) {
            displayAdminMessage(\"Error fetching list details: \" + error.message, \"error\");
            }
    },
    deleteDynamicList: async (listName) => {
        if (!confirm(`Are you sure you want to delete the list \"${listName}\" and all its items? This cannot be undone.`)) return;
        try {
            await apiRequest(`/admin/dynamic-lists/${listName}`, \'DELETE\');
                displayAdminMessage(`List \'${listName}\' deleted successfully.`, \'success\');
                await populateListsForManagement();
            await populateListSelectorForItems(); // Also refresh item list selector
            document.getElementById(\'dynamic-list-items-container\').innerHTML = \'\'; // Clear items if deleted list was selected
            } catch (error) {
            console.error(\"Error deleting list:\", error);
                displayAdminMessage(\"Failed to delete list: \" + error.message, \"error\");
            }
    },
    editDynamicListItem: async (itemId) => {
        try {
            const itemData = await apiRequest(`/admin/dynamic-lists/items/${itemId}`, \"GET\");
                showAddEditDynamicListItemModal(itemData);
        } catch (error) {
            displayAdminMessage(\"Error fetching item details: \" + error.message, \"error\");
            }
    },
    deleteDynamicListItem: async (itemId, listName) => {
        if (!confirm(`Are you sure you want to delete item ID ${itemId}? This cannot be undone.`)) return;
        try {
            await apiRequest(`/admin/dynamic-lists/items/${itemId}`, \'DELETE\');
                displayAdminMessage(`Item ID ${itemId} deleted successfully.`, \'success\');
                await loadItemsForSelectedList(listName); // Refresh items for the current list
        } catch (error) {
            console.error(\"Error deleting item:\", error);
                displayAdminMessage(\"Failed to delete item: \" + error.message, \"error\");
            }
    },
    checkItemInUse: async (itemId) => {
        try {
            const usage = await apiRequest(`/admin/dynamic-lists/items/${itemId}/in-use`, \"GET\");
                const message = usage.in_use
                ? `Item ID ${itemId} IS currently in use.`
                : `Item ID ${itemId} is NOT currently in use.`;
            displayAdminMessage(message, usage.in_use ?\'warning\' : \'info\');
            } catch (error) {
            displayAdminMessage(\"Error checking item usage: \" + error.message, \"error\");
            }
    }
};


// --- Utility Functions ---
function displayAdminMessage(message, type = \"info\") {
        if (!adminMessageArea) return;
adminMessageArea.textContent = message;
adminMessageArea.className = \'message-\' + type; // Use classes for styling

// Simple styling via JS, can be enhanced with CSS classes
switch (type) {
    case \"error\":
        adminMessageArea.style.color = \"#FF6B6B\"; // Red
        adminMessageArea.style.backgroundColor = \"rgba(255, 107, 107, 0.1)\";
        adminMessageArea.style.border = \"1px solid rgba(255, 107, 107, 0.3)\";
        break;
    case \"warning\":
        adminMessageArea.style.color = \"#FFA500\"; // Orange
        adminMessageArea.style.backgroundColor = \"rgba(255, 165, 0, 0.1)\";
        adminMessageArea.style.border = \"1px solid rgba(255, 165, 0, 0.3)\";
        break;
    case \"success\":
        adminMessageArea.style.color = \"#6BFF6B\"; // Green
        adminMessageArea.style.backgroundColor = \"rgba(107, 255, 107, 0.1)\";
        adminMessageArea.style.border = \"1px solid rgba(107, 255, 107, 0.3)\";
        break;
    case \"info\":
    default:
        adminMessageArea.style.color = \"#ADD8E6\"; // Light Blue for info
        adminMessageArea.style.backgroundColor = \"rgba(173, 216, 230, 0.1)\";
        adminMessageArea.style.border = \"1px solid rgba(173, 216, 230, 0.3)\";
        break;
}
adminMessageArea.style.padding = \"0.8rem\";
adminMessageArea.style.borderRadius = \"4px\";

if (message) {
    adminMessageArea.style.display = \'block\';
} else {
    adminMessageArea.style.display = \'none\';
}
    }

function escapeHTML(str) {
    if (str === null || str === undefined) return \'\';
    return String(str).replace(/[&<>\"]/g, function (tag) {
        const chars = {
        \'&\': \'&amp;\',
        \'<\': \'&lt;\',
        \'>\': \'&gt;\',
        \'\"\': \'&quot;\'
    };
    return chars[tag] || tag;
});
    }

async function apiRequest(endpoint, method = \"GET\", body = null) {
        const headers = {
        \"Authorization\": `Bearer ${authToken}`
        };
        if (method !== \"GET\" && method !== \"DELETE\" && body) { // For POST, PUT
headers[\"Content-Type\"] = \"application/json\";
        }

const options = {
    method: method,
    headers: headers
};

if (body && (method === \"POST\" || method === \"PUT\")) {
options.body = JSON.stringify(body);
        }

const response = await fetch(`${API_BASE_URL}${endpoint}`, options);
if (!response.ok) {
    let errorDetail = `HTTP error! Status: ${response.status}`;
    try {
        const errorData = await response.json();
        errorDetail = errorData.detail || JSON.stringify(errorData);
    } catch (e) {
        // If response is not JSON, use text
        errorDetail = await response.text() || errorDetail;
    }
    throw new Error(errorDetail);
}
if (response.status === 204) { // No Content
    return null;
}
return response.json();
    }

    // Initial load - e.g., load user management by default if admin role is confirmed
    // loadAdminSection(\"user-management\"); // Or whatever default section is preferred
    // For now, let the user click a section.
});
