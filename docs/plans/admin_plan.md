Okay, the PRD updates look good and the strategy for handling dynamic list item changes is much clearer now.

Here's a refined implementation plan for the admin functionality, incorporating the new requirements and breaking it down into manageable phases:

**Phase 1: Core Admin Role, Authentication, and Basic Panel Structure (FR-ADM-01)**

1.  **Backend (Python/FastAPI):**
    *   **User Model & DB (`schemas.py`, `database.py`):**
        *   Ensure the `User` model in `schemas.py` and the corresponding `Users` table (via Alembic if used, or manual DDL) include `role: str` (e.g., 'user', 'admin') and `is_active: bool = True`.
    *   **Admin User Creation:**
        *   Implement a CLI command (e.g., using Typer integrated with FastAPI) or a secure one-time script to create the first admin user or update an existing user's role to 'admin'.
    *   **RBAC - Admin Dependency (`auth.py`):**
        *   Create a FastAPI dependency (e.g., `require_admin_user`) that verifies if the currently authenticated user (from `get_current_active_user`) has the 'admin' role. This will protect admin-only API endpoints.
        *   Ensure the JWT token issued upon login contains role information, or the dependency can fetch user details including the role.
2.  **Frontend (HTML/CSS/JavaScript):**
    *   **Admin Panel Files:**
        *   Create `frontend/admin.html` as the main page for the admin panel.
        *   Create `frontend/admin_style.css` for admin panel specific styles.
        *   Create `frontend/admin_script.js` for admin panel client-side logic.
    *   **Admin Panel Access (`index.html`, `script.js`):**
        *   In the main navigation of `index.html`, add a link/button to "Admin Panel" (`admin.html`).
        *   Use JavaScript in `script.js` to show this link only if the logged-in user's role (fetched after login) is 'admin'.
    *   **Basic Admin Panel Layout (`admin.html`):**
        *   Design a simple layout with a persistent sidebar for navigation (e.g., User Management, Content Management, Settings) and a main content area.

**Phase 2: User Management (FR-ADM-02)**

1.  **Backend:**
    *   **CRUD Operations (`crud.py`):**
        *   `get_users(db: Session, skip: int = 0, limit: int = 100)`: Retrieve a list of all users.
        *   `update_user_active_status(db: Session, user_id: int, is_active: bool)`: Update the `is_active` status of a user.
        *   `delete_db_user(db: Session, user_id: int)`: Delete a user account (consider implications, soft delete might be better long-term, but PRD implies hard delete for now).
    *   **API Endpoints (`main.py` or new `admin_router.py` under an `/admin` prefix, protected by `require_admin_user`):**
        *   `GET /users`: List all users.
        *   `PUT /users/{user_id}/status`: Update user's `is_active` status.
        *   `DELETE /users/{user_id}`: Delete a user.
2.  **Frontend (`admin.html`, `admin_script.js`):**
    *   **User List View:** Section in `admin.html` to display a table of users (username, email, role, `is_active` status).
    *   **Actions:** Buttons/controls for each user to toggle `is_active` status and delete (with confirmation dialogs).

**Phase 3: Dynamic Content & Image Style Mapping (FR-ADM-05, FR-ADM-06, FR-AI-03, FR-ADM-11)**

1.  **Database (`database.py`, `schemas.py`):**
    *   `DynamicList` table: `list_name` (PK).
    *   `DynamicListItem` table: `id` (PK), `list_name` (FK to `DynamicList`), `item_value` (unique within its list_name), `item_label`, `is_active: bool = True`, `sort_order: int = 0`.
    *   `Stories` table: Ensure fields like `genre`, `image_style`, `writing_style` are designed to store the actual string values (e.g., `item_label` from `DynamicListItem`) at the time of story creation to preserve historical data if list items change.
2.  **Backend:**
    *   **CRUD (`crud.py`):**
        *   Full CRUD for `DynamicList` and `DynamicListItem` (respecting `is_active`, `sort_order`).
        *   Function `is_dynamic_list_item_in_use(db: Session, item_id: int)`: Checks if a `DynamicListItem` (by its ID or value/list_name combo) is referenced in any existing `Stories`.
    *   **API Endpoints (admin router):**
        *   CRUD endpoints for `/dynamic-lists` and `/dynamic-lists/{list_name}/items`.
        *   When an admin tries to deactivate or delete a `DynamicListItem`, the backend should use `is_dynamic_list_item_in_use`. Prevent hard delete if in use; allow deactivation. Return an "in-use" status to the admin UI.
    *   **Application Logic (`ai_services.py`, story creation endpoints in `main.py`):**
        *   When fetching items for user-facing dropdowns (e.g., genres), retrieve only `DynamicListItem` where `is_active = True`, ordered by `sort_order`.
        *   During story creation/update, save the chosen `item_label` (string) to the `Stories` table.
        *   Implement `FR-AI-03`: For image generation, look up the OpenAI `style` parameter (`vivid`/`natural`) from a specific `DynamicList` (e.g., 'image_style_mappings') where `item_value` is the application's `ImageStyle` and `item_label` (or another field) stores the OpenAI style. Default to `vivid` if no mapping.
3.  **Frontend (`admin.html`, `admin_script.js`):**
    *   **Dynamic List Management UI:**
        *   Interface to view, create, edit `DynamicList` entries.
        *   For each list, manage its `DynamicListItem`s: add, edit (value, label, sort_order), toggle `is_active`.
        *   Display an "in-use" indicator next to items that cannot be hard-deleted.
    *   **Story Creation Form (`index.html`, `script.js`):**
        *   Modify to fetch dropdown content (genres, image styles, writing styles) from new public backend endpoints that serve active `DynamicListItem`s.

**Phase 4: Content Moderation (FR-ADM-03)**

1.  **Backend:**
    *   **CRUD (`crud.py`):**
        *   `get_all_stories_admin(db: Session, skip: int = 0, limit: int = 100)`: Retrieve all stories.
        *   `delete_story_admin(db: Session, story_id: int)`: Admin deletes any story.
    *   **API Endpoints (admin router):**
        *   `GET /stories`: List all stories for admin review.
        *   `DELETE /stories/{story_id}`: Admin deletes a story.
2.  **Frontend (`admin.html`, `admin_script.js`):**
    *   **Story List View (Admin):** Table of all stories with key details, links to view (user-facing preview), and a delete button (with confirmation).

**Phase 5: System Monitoring, Logging & Enhanced Stats (FR-ADM-04, FR-ADM-08, FR-ADM-10)**

1.  **Backend:**
    *   **API Endpoints (admin router):**
        *   `GET /stats/basic`: Returns counts (users, stories). (FR-ADM-04)
        *   `GET /stats/enhanced`: Returns popular genres/styles (from `Stories` table), story creation trends (e.g., per day/week - requires timestamped story creation). (FR-ADM-10)
        *   `GET /logs/{log_filename}`: Endpoint to stream or paginate content of specified log files (`app.log`, `api.log`, `error.log`). Ensure path safety. (FR-ADM-08)
        *   `GET /logs`: List available log files.
2.  **Frontend (`admin.html`, `admin_script.js`):**
    *   **Dashboard/Monitoring Section:**
        *   Display basic and enhanced statistics.
        *   Log viewer: Select log file, view contents (potentially with simple client-side filtering or search).

**Phase 6: Application & API Key Configuration, Broadcast Messaging (FR-ADM-07, FR-ADM-09)**

1.  **Database (`database.py`, `schemas.py`):**
    *   `APISettings` table: `service_name` (PK, e.g., 'OpenAI'), `api_key: str`, `last_updated_by: str`, `last_updated_at: datetime`.
    *   `ApplicationConfig` table: `setting_name` (PK), `setting_value: str`, `description: str`.
    *   `BroadcastMessages` table: `id` (PK), `content: str`, `created_at: datetime`, `created_by: str`, `is_active: bool = True`.
2.  **Backend:**
    *   **CRUD (`crud.py`):** CRUD operations for `APISettings`, `ApplicationConfig`, `BroadcastMessages`.
        *   API keys in `APISettings` should ideally be encrypted/decrypted during CRUD if not using environment variables managed outside the app. For now, assume direct storage if simpler.
    *   **API Endpoints (admin router):**
        *   CRUD endpoints for `/config/api-keys`, `/config/application-settings`, `/broadcast-messages`.
    *   **Application Logic:**
        *   `ai_services.py` (and other services) to fetch API keys from `APISettings` via a CRUD function.
        *   Relevant parts of the application to read settings from `ApplicationConfig`.
    *   **Public Endpoint (`main.py`):**
        *   `GET /broadcast-messages/active`: For regular users to fetch active messages.
3.  **Frontend:**
    *   **Admin UI (`admin.html`, `admin_script.js`):**
        *   Sections for managing API Keys (view masked, update), Application Settings (e.g., maintenance mode toggle, default values), and Broadcast Messages (create, edit, toggle active).
    *   **User-Facing UI (`index.html`, `script.js`):**
        *   Logic to fetch and display active broadcast messages (e.g., as a banner).

**[2025-06-03] Update:**
- The database is now seeded with a base set of dynamic lists and items (genres, image styles, writing styles) via `scripts/seed_dynamic_lists.sql`.
- The admin panel UI fetches and displays dynamic lists/items from the database, not static enums.
- Story creation dropdowns are now populated from the DB (via `/dynamic-lists/{list_name}/active-items`), not from static arrays/enums.
- **Next:** Enhance admin panel to allow adding, editing, deleting, and toggling active status for dynamic list items directly from the UI. This will complete Phase 3 and allow full admin control over all user-facing categories.
