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
    const navLogout = document.getElementById("nav-logout");
    if (navLogout) {
        navLogout.addEventListener("click", () => {
            localStorage.removeItem("authToken");
            window.location.href = "index.html";
        });
    }

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
            const user = await apiRequest("/api/v1/users/me/");
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
                loadSystemMonitoring();
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
            const users = await apiRequest("/api/v1/admin/management/users/", "GET");
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
                <tr data-user-id=\"${user.id}\">
                    <td>${user.id}</td>
                    <td>${escapeHTML(user.username)}</td>
                    <td>${escapeHTML(user.email || 'N/A')}</td>
                    <td>${escapeHTML(user.role)}</td>
                    <td>
                        <input type=\"checkbox\" class=\"user-active-checkbox\" data-user-id=\"${user.id}\" ${user.is_active ? 'checked' : ''} title=\"${user.is_active ? 'User is active' : 'User is inactive'}\">
                    </td>
                    <td>
                        <button class=\"admin-button-secondary user-edit-details-btn\" data-user-id=\"${user.id}\">Edit User</button>
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
                // Directly call the PUT /admin/users/{user_id} endpoint for status change
                window.adminScript.updateUser(parseInt(userId), { is_active: isActive }, 'status');
            });
        });

        container.querySelectorAll('.user-edit-details-btn').forEach(button => {
            button.addEventListener('click', (event) => {
                const userId = parseInt(event.target.dataset.userId);
                showEditUserDetailsModal(userId);
            });
        });
    }

    // --- MODAL for User Details Edit ---
    async function showEditUserDetailsModal(userId) {
        const modalId = 'editUserDetailsModal';
        const existingModal = document.getElementById(modalId);
        if (existingModal) {
            existingModal.remove();
        }

        let currentUserData;
        try {
            // Fetch the specific user's current details.
            // Assuming /admin/users/ returns a list, find the user.
            // A direct /admin/users/{user_id} GET endpoint would be more efficient if available.
            const users = await apiRequest("/api/v1/admin/management/users/", "GET");
            currentUserData = users.find(u => u.id === userId);

            if (!currentUserData) {
                // As a fallback, try fetching the single user if the list doesn't contain them or direct endpoint exists
                try {
                    currentUserData = await apiRequest(`/api/v1/admin/management/users/${userId}`, "GET");
                } catch (singleFetchError) {
                    console.warn(`Could not fetch user ${userId} individually, relying on list or failing. Error: ${singleFetchError.message}`);
                }
            }

            if (!currentUserData) {
                displayAdminMessage(`User with ID ${userId} not found for editing.`, "error");
                return;
            }
        } catch (error) {
            displayAdminMessage("Error fetching user data for editing: " + error.message, "error");
            return;
        }

        const { username, email, role, is_active } = currentUserData;

        let modalHTML = `
            <div id=\"${modalId}\" class=\"modal\" style=\"display:block;\">
                <div class=\"modal-content\">
                    <span class=\"close-button\" onclick=\"document.getElementById(\'${modalId}\').remove();\">&times;</span>
                    <h2>Edit User Details: ${escapeHTML(username)} (ID: ${userId})</h2>
                    <form id=\"editUserDetailsForm\" class=\"admin-form\">
                        <input type=\"hidden\" name=\"user_id\" value=\"${userId}\">
                        <div class=\"form-group\">
                            <label for=\"edit_username\">Username:</label>
                            <input type=\"text\" id=\"edit_username\" name=\"username\" value=\"${escapeHTML(username)}\" class=\"admin-form-control\" required>
                        </div>
                        <div class=\"form-group\">
                            <label for=\"edit_email\">Email:</label>
                            <input type=\"email\" id=\"edit_email\" name=\"email\" value=\"${escapeHTML(email || '')}\" class=\"admin-form-control\">
                        </div>
                        <div class=\"form-group\">
                            <label for=\"edit_user_role\">Role:</label>
                            <select id=\"edit_user_role\" name=\"role\" class=\"admin-form-control\">
                                <option value=\"user\" ${role === 'user' ? 'selected' : ''}>User</option>
                                <option value=\"admin\" ${role === 'admin' ? 'selected' : ''}>Admin</option>
                            </select>
                        </div>
                        <div class=\"form-group\">
                            <label for=\"edit_is_active\" style=\"display: inline-block; margin-right: 10px;\">Is Active:</label>
                            <input type=\"checkbox\" id=\"edit_is_active\" name=\"is_active\" ${is_active ? 'checked' : ''} style=\"width: auto; vertical-align: middle;\">
                        </div>
                        <button type=\"submit\" class=\"admin-button\">Save Changes</button>
                    </form>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', modalHTML);

        const form = document.getElementById('editUserDetailsForm');
        form.onsubmit = async (e) => {
            e.preventDefault();
            const formData = new FormData(form);
            const updatedUsername = formData.get('username');
            const updatedEmail = formData.get('email');
            const updatedRole = formData.get('role');
            const updatedIsActive = document.getElementById('edit_is_active').checked;

            const payload = {};
            if (updatedUsername !== username) payload.username = updatedUsername;
            if (updatedEmail !== (email || '')) payload.email = updatedEmail; // Handle null email from server
            if (updatedRole !== role) payload.role = updatedRole;
            if (updatedIsActive !== is_active) payload.is_active = updatedIsActive;

            if (Object.keys(payload).length === 0) {
                displayAdminMessage("No changes detected.", "info");
                document.getElementById(modalId).remove();
                return;
            }

            window.adminScript.updateUser(userId, payload, 'details');
        };
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
            const lists = await apiRequest("/api/v1/admin/dynamic-lists/", "GET");
            if (!lists || lists.length === 0) {
                container.innerHTML = "<p>No dynamic lists found. You can add one!</p>";
                return;
            }
            let tableHTML = `
                <table>
                    <thead>
                        <tr>
                            <th>List Name</th>
                            <th>List Label</th>
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
                        <td>${escapeHTML(list.list_label || list.list_name)}</td>
                        <td>${escapeHTML(list.description || 'N/A')}</td>
                        <td>
                            <button class=\"admin-button-secondary edit-dynamic-list-btn\" data-list-name=\"${escapeHTML(list.list_name)}\">Edit</button>
                        </td>
                    </tr>
                `;
            });
            tableHTML += '</tbody></table>';
            container.innerHTML = tableHTML;

            // Add event listeners for the new "Edit" buttons
            container.querySelectorAll('.edit-dynamic-list-btn').forEach(button => {
                button.addEventListener('click', (e) => {
                    const listName = e.target.dataset.listName;
                    // This function will now handle edit and delete via modal
                    showAddEditDynamicListModal(listName); // Corrected: Call local function directly
                });
            });

        } catch (error) {
            console.error("Error loading dynamic lists:", error);
            container.innerHTML = '<p class="error-message">Failed to load dynamic lists.</p>';
            displayAdminMessage("Failed to load dynamic lists: " + error.message, "error");
        }
    }

    // --- System Monitoring Section ---
    async function loadSystemMonitoring() {
        adminViewPanel.innerHTML = `
            <h2>System Monitoring</h2>
            <div id="system-stats" class="table-responsive-container">
                <div style="display:flex; justify-content: space-between; align-items:center; gap:12px; flex-wrap:wrap;">
                    <p style="margin:0;">Loading system stats...</p>
                    <label class="admin-form" style="display:flex; align-items:center; gap:8px; margin:0;">
                        <input type="checkbox" id="auto-refresh-stats" />
                        <span>Auto refresh stats</span>
                    </label>
                </div>
            </div>
            <div id="logs-viewer" class="table-responsive-container">
                <h3>Logs</h3>
                <div class="admin-form" style="display:flex; gap:10px; align-items:flex-end; flex-wrap:wrap;">
                    <div class="form-group" style="min-width:260px; flex: 1 1 320px;">
                        <label for="log-file-select">Select log file</label>
                        <select id="log-file-select" class="admin-form-control">
                            <option value="">-- Loading log files --</option>
                        </select>
                    </div>
                    <div class="form-group" style="width:140px;">
                        <label for="log-tail-lines">Tail lines (10 - 5000)</label>
                        <input type="number" id="log-tail-lines" class="admin-form-control" min="10" max="5000" value="1000">
                    </div>
                    <div class="form-group" style="display:flex; gap:8px;">
                        <button id="refresh-logs-list" class="admin-button-secondary" title="Refresh log files list">Refresh List</button>
                        <button id="view-log-button" class="admin-button" title="View selected log">View</button>
                        <button id="download-log-button" class="admin-button-secondary" title="Download full log">Download</button>
                        <label style="display:flex; align-items:center; gap:6px; margin-left:8px;">
                            <input type="checkbox" id="auto-refresh-log" /> Auto refresh
                        </label>
                    </div>
                </div>
                <div class="admin-form" style="margin:8px 0; display:flex; gap:10px; align-items:center; flex-wrap:wrap;">
                    <div class="form-group" style="flex:1 1 280px;">
                        <label for="log-filter-input">Filter (client-side, regex or text)</label>
                        <input type="text" id="log-filter-input" class="admin-form-control" placeholder="e.g. ERROR|WARN or keyword...">
                    </div>
                    <div class="form-group" style="width:auto; display:flex; gap:8px; align-items:center;">
                        <label style="display:flex; align-items:center; gap:6px;">
                            <input type="checkbox" id="filter-regex" /> Regex
                        </label>
                        <label style="display:flex; align-items:center; gap:6px;">
                            <input type="checkbox" id="filter-invert" /> Invert match
                        </label>
                        <button id="apply-filter-button" class="admin-button-secondary">Apply Filter</button>
                        <button id="clear-filter-button" class="admin-button-secondary">Clear</button>
                    </div>
                </div>
                <pre id="log-content" style="background:#111; color:#ddd; padding:12px; border:1px solid #333; border-radius:6px; max-height:420px; overflow:auto; white-space:pre-wrap;"></pre>
            </div>
        `;

        // Load stats and logs list in parallel
        try {
            await Promise.all([renderSystemStats(), populateLogsList()]);
            displayAdminMessage("Monitoring loaded.", "success");
        } catch (e) {
            console.warn("Monitoring load encountered issues:", e);
        }

        // Wire up controls
        const viewBtn = document.getElementById("view-log-button");
        const refreshListBtn = document.getElementById("refresh-logs-list");
        const downloadBtn = document.getElementById("download-log-button");
        const selectEl = document.getElementById("log-file-select");
        const tailEl = document.getElementById("log-tail-lines");
        const autoRefreshStatsEl = document.getElementById("auto-refresh-stats");
        const autoRefreshLogEl = document.getElementById("auto-refresh-log");
        const filterInput = document.getElementById("log-filter-input");
        const filterRegex = document.getElementById("filter-regex");
        const filterInvert = document.getElementById("filter-invert");
        const applyFilterBtn = document.getElementById("apply-filter-button");
        const clearFilterBtn = document.getElementById("clear-filter-button");

        viewBtn.addEventListener("click", async () => {
            await fetchAndRenderSelectedLog();
        });

        refreshListBtn.addEventListener("click", async () => {
            await populateLogsList();
        });

        downloadBtn.addEventListener("click", async () => {
            const file = selectEl.value;
            if (!file) return;
            const url = `${API_BASE_URL}/api/v1/admin/monitoring/logs/${encodeURIComponent(file)}/download`;
            // Use a hidden link to preserve auth; since FileResponse is protected, attach auth via fetch+blob
            try {
                const resp = await fetch(url, { headers: { 'Authorization': `Bearer ${localStorage.getItem('authToken')}` } });
                if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
                const blob = await resp.blob();
                const a = document.createElement('a');
                const objectUrl = URL.createObjectURL(blob);
                a.href = objectUrl;
                a.download = file;
                document.body.appendChild(a);
                a.click();
                a.remove();
                URL.revokeObjectURL(objectUrl);
            } catch (err) {
                displayAdminMessage("Failed to download log: " + err.message, "error");
            }
        });

        // Auto-load first log if available after list populates
        selectEl.addEventListener("change", async () => {
            // No auto fetch on every change; keep it explicit unless already loaded once
        });

        // Auto-refresh timers
        let statsTimer = null;
        let logTimer = null;

        autoRefreshStatsEl.addEventListener('change', () => {
            if (autoRefreshStatsEl.checked) {
                statsTimer = setInterval(renderSystemStats, 5000);
            } else if (statsTimer) {
                clearInterval(statsTimer);
                statsTimer = null;
            }
        });

        autoRefreshLogEl.addEventListener('change', () => {
            if (autoRefreshLogEl.checked) {
                logTimer = setInterval(fetchAndRenderSelectedLog, 3000);
            } else if (logTimer) {
                clearInterval(logTimer);
                logTimer = null;
            }
        });

        // Filter handlers
        applyFilterBtn.addEventListener('click', () => applyLogFilter());
        clearFilterBtn.addEventListener('click', () => {
            filterInput.value = '';
            filterRegex.checked = false;
            filterInvert.checked = false;
            applyLogFilter();
        });

        async function renderSystemStats() {
            try {
                const stats = await apiRequest("/api/v1/admin/monitoring/stats", "GET");
                const el = document.getElementById("system-stats");
                el.innerHTML = `
                    <table>
                        <tbody>
                            <tr><th>Server Time (UTC)</th><td>${escapeHTML(stats.server_time_utc)}</td></tr>
                            <tr><th>Uptime</th><td>${formatUptime(stats.uptime_seconds)}</td></tr>
                            <tr><th>Platform</th><td>${escapeHTML(stats.platform)}</td></tr>
                            <tr><th>Python</th><td>${escapeHTML(stats.python_version)}</td></tr>
                            <tr><th>Load Average</th><td>${formatLoadAvg(stats.load_average)}</td></tr>
                            <tr><th>Disk Used</th><td>${stats.disk_used_gb} GB / ${stats.disk_total_gb} GB (${stats.disk_percent}%)</td></tr>
                            <tr><th>Logs Dir</th><td>${escapeHTML(stats.logs_dir)}</td></tr>
                            <tr><th>Log Files</th><td>${stats.log_files_count}</td></tr>
                        </tbody>
                    </table>
                `;
            } catch (error) {
                console.error("Failed to load system stats:", error);
                document.getElementById("system-stats").innerHTML = '<p class="error-message">Failed to load system stats.</p>';
                displayAdminMessage("Failed to load system stats: " + error.message, "error");
            }
        }

        async function populateLogsList() {
            const select = document.getElementById("log-file-select");
            select.innerHTML = '<option value="">-- Loading log files --</option>';
            try {
                const files = await apiRequest("/api/v1/admin/monitoring/logs/", "GET");
                if (!files || files.length === 0) {
                    select.innerHTML = '<option value="">(no .log files found)</option>';
                    document.getElementById("log-content").textContent = "";
                    return;
                }
                select.innerHTML = files.map((f, idx) => `<option value="${escapeHTML(f)}" ${idx === 0 ? 'selected' : ''}>${escapeHTML(f)}</option>`).join("");
                // After populating, auto-view the first log
                await fetchAndRenderSelectedLog();
            } catch (error) {
                console.error("Failed to load log list:", error);
                select.innerHTML = '<option value="">(failed to load logs)</option>';
                displayAdminMessage("Failed to load logs list: " + error.message, "error");
            }
        }

        async function fetchAndRenderSelectedLog() {
            const file = document.getElementById("log-file-select").value;
            const tail = Math.max(10, Math.min(5000, parseInt(document.getElementById("log-tail-lines").value || "1000", 10)));
            if (!file) {
                document.getElementById("log-content").textContent = "Select a log file to view.";
                return;
            }
            try {
                // Build URL with encoded filename and query param
                const endpoint = `/api/v1/admin/monitoring/logs/${encodeURIComponent(file)}?lines=${tail}`;
                const headers = {
                    'Authorization': `Bearer ${localStorage.getItem('authToken')}`,
                };
                const response = await fetch(API_BASE_URL + endpoint, { method: 'GET', headers });
                if (!response.ok) {
                    let txt = await response.text();
                    throw new Error(txt || `HTTP ${response.status}`);
                }
                const text = await response.text();
                document.getElementById("log-content").textContent = text || "(no content)";
                applyLogFilter();
            } catch (error) {
                console.error("Failed to fetch log content:", error);
                document.getElementById("log-content").textContent = `Error loading log: ${error.message}`;
                displayAdminMessage("Failed to load log content: " + error.message, "error");
            }
        }

        function formatUptime(seconds) {
            if (!Number.isFinite(seconds)) return 'n/a';
            const d = Math.floor(seconds / 86400);
            const h = Math.floor((seconds % 86400) / 3600);
            const m = Math.floor((seconds % 3600) / 60);
            const s = Math.floor(seconds % 60);
            const parts = [];
            if (d) parts.push(`${d}d`);
            if (h || d) parts.push(`${h}h`);
            if (m || h || d) parts.push(`${m}m`);
            parts.push(`${s}s`);
            return parts.join(" ");
        }

        function formatLoadAvg(load) {
            if (!load || !Array.isArray(load)) return 'n/a';
            return load.map(v => typeof v === 'number' ? v.toFixed(2) : v).join(', ');
        }

        function applyLogFilter() {
            const raw = document.getElementById('log-content').textContent || '';
            const query = filterInput.value;
            if (!query) {
                // Show raw
                document.getElementById('log-content').textContent = raw;
                return;
            }
            let lines = raw.split(/\n/);
            let matcher;
            if (filterRegex.checked) {
                try {
                    matcher = new RegExp(query, 'i');
                } catch (e) {
                    displayAdminMessage('Invalid regex: ' + e.message, 'error');
                    return;
                }
            }
            const filtered = lines.filter(line => {
                const matched = matcher ? matcher.test(line) : line.toLowerCase().includes(query.toLowerCase());
                return filterInvert.checked ? !matched : matched;
            });
            document.getElementById('log-content').textContent = filtered.join('\n');
        }
    }

    async function populateListSelectorForItems() {
        const selector = document.getElementById('select-list-for-items');
        selector.innerHTML = '<option value="">-- Select a List --</option>';
        try {
            const lists = await apiRequest("/api/v1/admin/dynamic-lists/", "GET");
            lists.forEach(list => {
                const option = document.createElement('option');
                option.value = list.list_name;
                option.textContent = escapeHTML(list.list_label || list.list_name); // Use list_label if available, otherwise list_name
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
            const items = await apiRequest(`/api/v1/admin/dynamic-lists/${listName}/items`, "GET");

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
                apiRequest(`/api/v1/admin/dynamic-lists/items/${item.id}/in-use`, "GET") // Corrected path
                    .then(usageInfo => ({ itemId: item.id, isInUse: usageInfo.is_in_use, details: usageInfo.details }))
                    .catch(err => {
                        console.warn(`Could not fetch in-use status for item ${item.id}`, err);
                        return { itemId: item.id, isInUse: false, details: [] }; // Default on error
                    })
            );
            const usageResults = await Promise.all(usagePromises);
            const usageMap = usageResults.reduce((map, current) => {
                map[current.itemId] = { isInUse: current.isInUse, details: current.details };
                return map;
            }, {});

            items.forEach(item => {
                const usageInfo = usageMap[item.id] || { isInUse: false, details: [] };
                const isInUse = usageInfo.isInUse;
                tableHTML += `
                    <tr data-item-id="${item.id}" data-list-name="${escapeHTML(listName)}">
                        <td>${item.id}</td>
                        <td>${escapeHTML(item.item_value)}</td>
                        <td>${escapeHTML(item.item_label)}</td>
                        <td>${item.is_active ? 'Yes' : 'No'}</td>
                        <td>${item.sort_order}</td>
                        <td><input type="checkbox" ${isInUse ? 'checked' : ''} disabled title="${isInUse ? 'Item is in use' + (usageInfo.details.length > 0 ? ': ' + usageInfo.details.join(', ') : '') : 'Item is not in use'}"></td>
                        <td>${item.additional_config ? escapeHTML(JSON.stringify(item.additional_config)) : 'N/A'}</td>
                        <td class="actions-cell">
                            <button class="admin-button-secondary edit-dynamic-list-item-btn" data-item-id="${item.id}">Edit</button>
                        </td>
                    </tr>
                `;
            });
            tableHTML += '</tbody></table>';
            container.innerHTML = tableHTML;

            // Add event listeners for the new "Edit" buttons
            container.querySelectorAll('.edit-dynamic-list-item-btn').forEach(button => {
                button.addEventListener('click', (e) => {
                    const itemId = parseInt(e.target.dataset.itemId);
                    // This function now handles edit, delete, and active status within the modal
                    window.adminScript.showAddEditDynamicListItemModal(itemId);
                });
            });

        } catch (error) {
            console.error(`Error loading items for list ${listName}:`, error);
            container.innerHTML = `<p class="error-message">Failed to load items for ${escapeHTML(listName)}.</p>`;
            displayAdminMessage(`Failed to load items for ${escapeHTML(listName)}: ` + error.message, "error");
        }
    }

    // MODAL for Dynamic List (Add/Edit/Delete)
    function showAddEditDynamicListModal(listName = null) {
        const isEdit = listName !== null;
        let currentDescription = '';
        let currentListLabel = ''; // Added for list_label

        const modalId = 'dynamicListModal';
        const existingModal = document.getElementById(modalId);
        if (existingModal) {
            existingModal.remove();
        }

        // Modal message area
        const modalMessageId = `${modalId}-message-area`;

        let modalHTML = `
            <div id="${modalId}" class="modal" style="display:block;">
                <div class="modal-content">
                    <span class="close-button" onclick="document.getElementById('${modalId}').remove();">&times;</span>
                    <h2>${isEdit ? 'Edit' : 'Add'} Dynamic List</h2>
                    <div id="${modalMessageId}" class="admin-message" style="display:none; margin-bottom:15px;"></div>
                    <form id="dynamicListForm" class="admin-form">
                        <div class="form-group">
                            <label for="dl_list_name">List Name (ID):</label>
                            <input type="text" id="dl_list_name" name="list_name" value="${isEdit ? escapeHTML(listName) : ''}" ${isEdit ? 'readonly' : 'required'} class="admin-form-control">
                        </div>
                        <div class="form-group">
                            <label for="dl_list_label">List Label (User-Friendly):</label>
                            <input type="text" id="dl_list_label" name="list_label" value="${isEdit ? escapeHTML(currentListLabel) : ''}" class="admin-form-control">
                        </div>
                        <div class="form-group">
                            <label for="dl_description">Description (Optional):</label>
                            <textarea id="dl_description" name="description" class="admin-form-control">${isEdit ? escapeHTML(currentDescription) : ''}</textarea>
                        </div>
                        <div class="modal-actions">
                            <button type="submit" id="saveDynamicListButton" class="admin-button">${isEdit ? 'Save Changes' : 'Create List'}</button>
                            ${isEdit ? `<button type="button" id="deleteDynamicListButton" class="admin-button-danger">Delete List</button>` : ''}
                            <button type="button" id="cancelDynamicListModalButton" class="admin-button-secondary" onclick="document.getElementById('${modalId}').remove();">Cancel</button>
                        </div>
                    </form>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', modalHTML);

        const form = document.getElementById('dynamicListForm');
        const descriptionTextarea = document.getElementById('dl_description');
        const listLabelInput = document.getElementById('dl_list_label'); // Added for list_label
        const modalMessageArea = document.getElementById(modalMessageId);

        if (isEdit) {
            apiRequest(`/api/v1/admin/dynamic-lists/${listName}`, "GET")
                .then(listData => {
                    if (listData) {
                        if (listData.description) {
                            descriptionTextarea.value = listData.description;
                        }
                        if (listData.list_label) { // Added for list_label
                            listLabelInput.value = listData.list_label;
                        }
                    }
                })
                .catch(err => {
                    displayAdminMessage('Error fetching list details for editing: ' + err.message, 'error', modalId);
                    // document.getElementById(modalId).remove(); // Keep modal open to show error
                });

            const deleteButton = document.getElementById('deleteDynamicListButton');
            if (deleteButton) { // Ensure delete button exists (it should in edit mode)
                deleteButton.addEventListener('click', async () => {
                    if (!confirm(`Are you sure you want to delete the list \"${escapeHTML(listName)}\" and all its items? This cannot be undone.`)) return;
                    try {
                        await apiRequest(`/api/v1/admin/dynamic-lists/${listName}`, 'DELETE');
                        displayAdminMessage(`List '${escapeHTML(listName)}' deleted successfully.`, 'success'); // Global message
                        document.getElementById(modalId).remove();
                        await populateListsForManagement();
                        await populateListSelectorForItems(); // Refresh selector in items tab
                        // Clear items view if the deleted list was selected
                        const listSelector = document.getElementById('select-list-for-items');
                        if (listSelector.value === listName) {
                            listSelector.value = "";
                            document.getElementById('dynamic-list-items-container').innerHTML = '';
                            document.getElementById('add-new-item-btn').style.display = 'none';
                        }
                    } catch (error) {
                        console.error("Error deleting list:", error);
                        let errorDetail = error.message;
                        if (error.response && error.response.detail) {
                            errorDetail = typeof error.response.detail === 'string' ? error.response.detail : JSON.stringify(error.response.detail);
                        }
                        displayAdminMessage(`Failed to delete list: ${errorDetail}`, "error", modalId); // Display error in modal
                    }
                });
            }
        }

        form.onsubmit = async (e) => {
            e.preventDefault();
            const formData = new FormData(form);
            const data = {
                list_name: formData.get('list_name'), // list_name will be readonly in edit mode
                list_label: formData.get('list_label'), // Added for list_label
                description: formData.get('description')
            };

            try {
                if (isEdit) {
                    // Only send description and list_label for update
                    await apiRequest(`/api/v1/admin/dynamic-lists/${listName}`, 'PUT', { description: data.description, list_label: data.list_label });
                    displayAdminMessage(`List '${escapeHTML(listName)}' updated.`, 'success'); // Global message
                } else {
                    await apiRequest("/api/v1/admin/dynamic-lists/", 'POST', data);
                    displayAdminMessage(`List '${escapeHTML(data.list_name)}' created.`, 'success'); // Global message
                }
                document.getElementById(modalId).remove();
                await populateListsForManagement();
                await populateListSelectorForItems(); // Refresh selector in items tab
            } catch (error) {
                console.error("Error saving dynamic list:", error);
                let errorDetail = error.message;
                if (error.response && error.response.detail) {
                    errorDetail = typeof error.response.detail === 'string' ? error.response.detail : JSON.stringify(error.response.detail);
                }
                displayAdminMessage(`Error saving list: ${errorDetail}`, "error", modalId); // Display error in modal
            }
        };
    }

    // MODAL for Dynamic List Item (Add/Edit)
    async function showAddEditDynamicListItemModal(itemId = null, listNameForNewItem = null) {
        const isEdit = itemId !== null;
        let itemData = null;
        let currentListName = listNameForNewItem;
        let itemInUseDetails = []; // To store in-use details for the modal

        const modalId = 'dynamicListItemModal';
        const existingModal = document.getElementById(modalId);
        if (existingModal) {
            existingModal.remove();
        }

        if (isEdit) {
            try {
                itemData = await apiRequest(`/api/v1/admin/dynamic-lists/items/${itemId}`, "GET");
                if (!itemData) {
                    displayAdminMessage(`Error: Item ID ${itemId} not found.`, "error", modalId);
                    return;
                }
                currentListName = itemData.list_name;

                // Fetch in-use status for the item being edited
                const usageInfo = await apiRequest(`/api/v1/admin/dynamic-lists/items/${itemId}/in-use`, "GET"); // Corrected path
                itemInUseDetails = usageInfo.is_in_use ? usageInfo.details : [];

            } catch (error) {
                displayAdminMessage("Error fetching item details: " + error.message, "error", modalId);
                return;
            }
        }

        const itemValue = isEdit ? itemData.item_value : '';
        const itemLabel = isEdit ? itemData.item_label : '';
        const isActive = isEdit ? itemData.is_active : true;
        const sortOrder = isEdit ? itemData.sort_order : 0;

        let additionalConfigString = '';
        if (isEdit && itemData.additional_config) {
            additionalConfigString = JSON.stringify(itemData.additional_config, null, 2);
        }


        let imageStyleSpecificHTML = '';


        // Modal message area
        const modalMessageId = `${modalId}-message-area`;

        let modalHTML = `
            <div id="${modalId}" class="modal" style="display:block;">
                <div class="modal-content">
                    <span class="close-button" onclick="document.getElementById(\'${modalId}\').remove();">&times;</span>
                    <h2>${isEdit ? 'Edit' : 'Add'} Dynamic List Item (for List: ${escapeHTML(currentListName)})</h2>
                    <div id="${modalMessageId}" class="admin-message" style="display:none; margin-bottom:15px;"></div>
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
                        <div class="form-group">
                            <label for="item_additional_config">Additional Config (JSON, Optional):</label>
                            <textarea id="item_additional_config" name="item_additional_config" rows="3" class="admin-form-control">${escapeHTML(additionalConfigString)}</textarea>
                        </div>
                        <div class="modal-actions">
                            <button type="submit" id="saveDynamicListItemButton" class="admin-button">${isEdit ? 'Save Changes' : 'Create Item'}</button>
                            ${isEdit ? `<button type="button" id="deleteDynamicListItemButton" class="admin-button-danger">Delete Item</button>` : ''}
                            <button type="button" id="cancelDynamicListItemModalButton" class="admin-button-secondary" onclick="document.getElementById(\\'${modalId}\\').remove();">Cancel</button>
                        </div>
                    </form>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', modalHTML);

        const form = document.getElementById('dynamicListItemForm');
        form.onsubmit = async (e) => {
            e.preventDefault();
            const formData = new FormData(form);
            let additionalConfig = {}; // Initialize as empty object
            const additionalConfigText = formData.get('item_additional_config').trim();

            if (additionalConfigText) {
                try {
                    additionalConfig = JSON.parse(additionalConfigText);
                } catch (jsonError) {
                    displayAdminMessage("Invalid JSON in Additional Config: " + jsonError.message, "error", modalId);
                    return;
                }
            }

            // Set to null if additionalConfig remains empty
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
                    await apiRequest(`/api/v1/admin/dynamic-lists/items/${itemId}`, 'PUT', data); // Corrected path
                    displayAdminMessage(`Item ID ${itemId} updated.`, 'success'); // Global message
                } else {
                    data.list_name = formData.get('item_list_name'); // list_name only needed for POST
                    await apiRequest(`/api/v1/admin/dynamic-lists/${data.list_name}/items`, 'POST', data);
                    displayAdminMessage(`New item created in list '${data.list_name}'.`, 'success'); // Global message
                }
                document.getElementById(modalId).remove();
                await loadItemsForSelectedList(currentListName);
            } catch (error) {
                console.error("Error saving dynamic list item:", error);
                let errorDetail = error.message;
                if (error.response && error.response.detail) {
                    errorDetail = typeof error.response.detail === 'string' ? error.response.detail : JSON.stringify(error.response.detail);
                }
                displayAdminMessage(`Error saving item: ${errorDetail}`, "error", modalId); // Display error in modal
            }
        };

        if (isEdit) {
            const deleteButton = document.getElementById('deleteDynamicListItemButton'); // Corrected ID
            deleteButton.addEventListener('click', async () => {
                // Use itemInUseDetails fetched when modal opened
                if (itemInUseDetails.length > 0) {
                    alert(`Cannot delete item ID ${itemId}. It is currently in use: ${itemInUseDetails.join(', ')}`);
                    return;
                }

                if (!confirm(`Are you sure you want to delete item ID ${itemId} ('${escapeHTML(itemValue)}')? This cannot be undone.`)) return;

                try {
                    await apiRequest(`/api/v1/admin/dynamic-lists/items/${itemId}`, 'DELETE'); // Corrected path
                    displayAdminMessage(`Item ID ${itemId} deleted successfully.`, 'success'); // Global message
                    document.getElementById(modalId).remove();
                    await loadItemsForSelectedList(currentListName);
                } catch (error) {
                    console.error("Error deleting item:", error);
                    let errorDetail = error.message;
                    if (error.response && error.response.detail) {
                        errorDetail = typeof error.response.detail === 'string' ? error.response.detail : JSON.stringify(error.response.detail);
                    }
                    displayAdminMessage(`Failed to delete item: ${errorDetail}`, "error", modalId); // Display error in modal
                }
            });
        }
    }

    // Expose functions to global scope for inline onclick handlers
    window.adminScript = {
        updateUser: async function (userId, payload, updateType = 'details') { // updateType can be 'status' or 'details'
            const modalId = 'editUserDetailsModal'; // Assuming this is the relevant modal for details
            try {
                await apiRequest(`/api/v1/admin/management/users/${userId}`, 'PUT', payload);
                displayAdminMessage(`User ${userId} ${updateType} updated successfully.`, 'success');
                if (updateType === 'details' && document.getElementById(modalId)) {
                    document.getElementById(modalId).remove();
                }
                await loadUserManagement(); // Refresh the user table
            } catch (error) {
                console.error(`Error updating user ${updateType}:`, error);
                let errorDetail = error.message;
                if (error.response && error.response.detail) {
                    errorDetail = typeof error.response.detail === 'string' ? error.response.detail : JSON.stringify(error.response.detail);
                }

                if (updateType === 'details' && document.getElementById(modalId)) {
                    const form = document.getElementById('editUserDetailsForm');
                    const modalContent = form.closest('.modal-content');
                    let errorDiv = modalContent.querySelector('.modal-error-message');
                    if (!errorDiv) {
                        errorDiv = document.createElement('div');
                        errorDiv.className = 'modal-error-message admin-message error';
                        errorDiv.style.marginTop = '10px';
                        form.appendChild(errorDiv);
                    }
                    errorDiv.textContent = `Error: ${errorDetail}`;
                } else if (updateType === 'status') { // Error for status toggle from checkbox
                    displayAdminMessage(`Error updating status: ${errorDetail}`, "error");
                    // Revert checkbox if it was a self-deactivation attempt or other critical error
                    if (error.status === 403 && errorDetail.includes("deactivate their own account")) {
                        // Checkbox already reverted by the browser, or we can force it
                        const checkbox = document.querySelector(`.user-active-checkbox[data-user-id=\"${userId}\"]`);
                        if (checkbox) checkbox.checked = true; // Force re-check
                    } else if (error.status === 403 && errorDetail.includes("sole admin")) {
                        const checkbox = document.querySelector(`.user-active-checkbox[data-user-id=\"${userId}\"]`);
                        if (checkbox) checkbox.checked = true; // Revert if trying to deactivate sole admin
                    }
                    // For other errors, the table refresh will show the actual state.
                } else {
                    displayAdminMessage(`Error updating user: ${errorDetail}`, "error");
                }
            }
        },
        editDynamicList: async (listName) => { // This function is now effectively an alias for the modal
            showAddEditDynamicListModal(listName);
        },
        // Exposing the new modal function for adding/editing items
        showAddEditDynamicListItemModal: async (itemId = null, listNameForNewItem = null) => {
            // This is the primary function now for adding AND editing dynamic list items via modal
            showAddEditDynamicListItemModal(itemId, listNameForNewItem);
        },
        deleteDynamicList: async (listName) => {
            // This function is effectively replaced by the modal's delete button logic.
            // Kept for now if any old references exist, but should be deprecated.
            // UI uses modal.
            console.warn("deleteDynamicList directly called. UI uses modal. Consider removing this direct exposure if not needed.");
            // The actual deletion logic is now within showAddEditDynamicListModal
            // For safety, this could call the modal or just log a warning.
            // To prevent accidental direct calls from breaking things if old code exists:
            showAddEditDynamicListModal(listName); // Open the modal which contains the delete logic
        },
        editDynamicListItem: async (itemId) => { // This function is now effectively an alias for the modal
            showAddEditDynamicListItemModal(itemId);
        },
        deleteDynamicListItem: async (itemId, listName) => {
            // This function is effectively replaced by the modal's delete button logic.
            // Kept for now if any old references exist, but should be deprecated.
            // For direct deletion (e.g. from console), it might still be useful, but UI uses modal.
            console.warn("deleteDynamicListItem directly called. UI uses modal. Consider removing this direct exposure if not needed.");
            try {
                const usageInfo = await apiRequest(`/api/v1/admin/dynamic-lists/items/${itemId}/in-use`, "GET"); // Corrected path for safety, though deprecated
                if (usageInfo.is_in_use) {
                    alert(`Cannot delete item ID ${itemId}. It is currently in use: ${usageInfo.details.join(', ')}`);
                    return;
                }

                if (!confirm(`Are you sure you want to delete item ID ${itemId}? This cannot be undone.`)) return;

                await apiRequest(`/api/v1/admin/dynamic-lists/items/${itemId}`, 'DELETE'); // Corrected path for safety, though deprecated
                displayAdminMessage(`Item ID ${itemId} deleted successfully.`, 'success');
                await loadItemsForSelectedList(listName); // listName needs to be available
            } catch (error) {
                console.error("Error deleting item directly:", error);
                displayAdminMessage("Failed to delete item: " + error.message, "error");
            }
        }
        // toggleDynamicListItemActiveStatus is removed as its functionality is in the modal.
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

function displayAdminMessage(message, type = 'info', modalId = null) {
    let messageArea;
    if (modalId) {
        messageArea = document.getElementById(`${modalId}-message-area`);
    } else {
        messageArea = document.getElementById('admin-message-area');
    }

    if (!messageArea) {
        // Fallback to global message area if modal-specific one isn't found (should not happen if HTML is correct)
        messageArea = document.getElementById('admin-message-area');
        if (!messageArea) return; // Still no message area, abort.
        console.warn("Modal message area not found, using global.");
    }

    messageArea.textContent = message;
    messageArea.className = 'admin-message'; // Reset classes
    if (type) {
        messageArea.classList.add(type); // e.g., 'success', 'error', 'warning', 'info'
    }

    if (message) {
        messageArea.style.display = 'block';
    } else {
        messageArea.style.display = 'none';
    }
}
