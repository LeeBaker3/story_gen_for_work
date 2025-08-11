# 1. Purpose

The Story Generator Web App is a web-based application that allows users to generate custom illustrated stories using AI. It leverages the OpenAI ChatGPT API for story generation and an AI image generation model for generating corresponding illustrations. Users can log in, input story parameters, preview, edit, and export stories as PDFs.

# 2. Features and Functionality

## 2.1 User Interface (UI)
*   **Homepage:**
    *   Modern, clean design.
    *   Options to:
        *   Create a new story.
        *   Log in / Sign up.
        *   Browse previously created stories.
*   **Story Creation Form:**
    *   Select story genre (Children’s, Sci-Fi, Drama, Horror, Action). Dropdowns (e.g., genre) support alphabetical/numerical sorting.
    *   Enter:
        *   Story Title (Optional. If left blank, a title will be AI-generated. Can be edited later).
        *   Story outline.
        *   Main characters (name, personality, background).
        *   Includes a collapsible, detailed character creation section. Users can specify attributes like age, gender, physical appearance (hair color, eye color, ethnicity, build), clothing style, and key personality traits. The system will provide defaults or tips to guide users. This information is used to generate upfront character reference images to guide the AI image generation model for consistent character depiction throughout the story.
        *   Number of pages.
        *   Option to select a writing style for the story (e.g., narrative, descriptive, poetic, humorous, formal).
        *   Option to adjust word-to-picture ratio (e.g., one image every X words/paragraphs, or one image per page as default).
        *   Option to select an image style for story illustrations (e.g., cartoon, watercolor, photorealistic).
    *   Additional optional fields (tone, setting, etc.).
*   **Story Preview Page:**
    *   Displays the story, starting with a Title Page featuring the story title and a cover image.
    *   Displays generated story per page, with accompanying image.
    *   Navigation between pages.
    *   Export options (PDF).
    *   Option to edit story title, page text, and regenerate pages/images.
*   **Authentication:**
    *   Secure login and session management for regular and admin users. Admin users have distinct privileges.
    *   User dashboard showing saved stories.
    *   Forgot Password functionality.
*   **Admin Panel:** (New Section for FR-ADM-01, FR-ADM-05, FR-ADM-06)
    *   Accessible only to users with admin privileges.
    *   Interface for managing application-wide settings and dynamic content.
    *   Functionality to manage dropdown list items (e.g., genres, image styles).
    *   Interface for User Management (activate, deactivate, delete users).
    *   Interface for Content Moderation (review and remove stories).
    *   Interface for System Monitoring (view basic health, usage stats, logs).
    *   Interface for Application Configuration (e.g., API Keys, maintenance mode, broadcast messages).

# 3. Technical Requirements

## 3.1 Backend
*   Framework: Python FastAPI
*   OpenAI APIs:
    *   ChatGPT API: Returns story content in structured JSON format.
    *   AI Image Generation API (e.g., OpenAI's image API): Generates images based on page-specific prompts.
*   Functionality:
    *   Accepts user inputs (including an optional story title) and sends prompts to ChatGPT.
    *   If no title is provided by the user, generates a suitable story title based on the outline and other parameters.
    *   Parses and stores story (including title), pages (with a dedicated title page as the first page), and image metadata in a SQLite database.
    *   Generates a cover image for the title page using the AI image generation model, based on the final story title, overall themes, and main character descriptions.
    *   Generates PDF combining story text and locally stored images.
    *   Provides an endpoint to retrieve a list of stories for the authenticated user.
    *   Generates and stores character reference images based on detailed user input, to be used in subsequent image generation prompts for consistency.
    *   Supports different selectable image styles for AI image generation, with styles potentially managed dynamically.
    *   Manages adjustable word-to-picture ratios for story layout.
    *   Supports different selectable writing styles for ChatGPT, with styles potentially managed dynamically.
    *   Implements a secure 'Forgot Password' mechanism (e.g., token-based).
    *   Implements role-based access control (RBAC) to differentiate between regular users and admins.
    *   Provides CRUD endpoints for managing dynamic list content (e.g., genres, image styles) accessible only by admins.
    *   Handles user-defined story titles, allowing for creation and updates.
    *   Generates a cover image for the title page using the AI image generation model, based on the story title, themes, and character descriptions.
    *   Securely stores and manages API keys (e.g., OpenAI API Key), accessible/modifiable only by admins.
    *   Provides mechanisms to ensure data integrity when dynamic list items (e.g., genres, styles) are modified or deleted by an admin. This includes strategies like soft deletes, preventing deletion of in-use items, or indicating usage to the admin.
    *   Provides endpoints for admins to manage users (view, activate, deactivate, delete).
    *   Provides endpoints for admins to moderate content (list all stories, delete stories).
    *   Provides endpoints for admins to view system statistics and access application logs.
    *   Provides endpoints for admins to manage application configurations (e.g., API keys, maintenance mode) and send broadcast messages.

## 3.2 Frontend
*   Technologies: HTML, CSS (site-wide), JavaScript
*   Modern responsive design using CSS for theming.
*   Form validation and dynamic content updates.
*   Interface for detailed character attribute input.
*   Controls for selecting image style and word-to-picture ratio.
*   Controls for selecting writing style.
*   User flow and forms for 'Forgot Password' process.

## 3.3 Database
*   Database Type: SQLite
*   Entities:
    *   Users (username, password hash, email, role (e.g., 'user', 'admin'), is_active)
    *   Stories (title, outline, genre, metadata)
    *   Pages (story_id, page_number, text, image_description, image_path)
    *   DynamicList (list_name (e.g., 'genres', 'image_styles', 'writing_styles'))
    *   DynamicListItem (list_id, item_value, item_label, is_active, sort_order)
    *   APISettings (service_name, api_key, last_updated_by, last_updated_at)
    *   ApplicationConfig (setting_name, setting_value, description)
    *   BroadcastMessages (message_id, content, created_at, created_by, is_active)
*   Features:
    *   Stories are searchable by title.
    *   Users can edit and re-export stories.
    *   Image files are stored locally and linked in the DB.
    *   Strategies for handling stories linked to modified/deleted `DynamicListItem` values:
        *   Retain original value string in the `Stories` table if a linked `DynamicListItem` is deactivated or its label changes.
        *   Prevent hard deletion of `DynamicListItem` if it's referenced by any story; use an `is_active` flag instead (soft delete).
        *   Admin interface should indicate if a `DynamicListItem` is in use before allowing deactivation or modification.

## 3.4 Logging & Error Handling
*   Separate local log files.
*   Logged actions:
    *   User login/logout, story creation, edits, and exports.
    *   All API requests/responses (ChatGPT, AI Image Generation).
    *   Error logs (failed API calls, DB issues, image failures).
*   Graceful failure messages for:
    *   API timeouts/failures.
    *   Image generation errors.
    *   Invalid JSON responses.
*   Centralized, config-driven logging:
    *   Logging is configured via `config/logging.yaml` using `logging.config.dictConfig`.
    *   Daily rotating files (UTC midnight) for app, api, and error logs stored under `data/logs/`.
    *   Environment overrides for log levels: `APP_LOG_LEVEL`, `API_LOG_LEVEL`, `ERROR_LOG_LEVEL`.
    *   Base64 image payloads are redacted from logs for safety.

## 3.5 State Management & Recovery Story Generation Process
*  Process Tracking: The system shall track the progress of the story generation process, including the current step (e.g., "Generating reference images for characters") and the number of attempts made so far.
*  Timeout Detection: The system shall detect when a timeout occurs during the process and pause or retry the process accordingly.
*  Smart Retry Mechanism**: The system shall implement a smart retry mechanism that:
    *   Avoids retrying the same step multiple times in quick succession (to prevent infinite loops).
    *   Increases the delay between retries to prevent overwhelming the server with consecutive requests.
*  Uses a maximum number of attempts before giving up on the process.
*  Resume from Previous Attempt: The system shall be able to resume the process from where it left off, including re-trying failed steps and resuming image generation if necessary.
*  Error Handling: The system shall handle errors that occur during the process, such as OpenAI API errors or server-side errors, and provide meaningful error messages or logging information.

### 3.5.1 Additional Requirements:**
*  Process State Management**: The system shall maintain a state machine to track the progress of each step in the process.
*  Cache Mechanism**: The system shall consider implementing a cache mechanism to store intermediate results (e.g., generated images) to reduce processing time and improve performance.



# 4. Functional Requirements

## 4.1 Core Application & Backend
*   **FR-CORE-01:** Story and image data are generated using ChatGPT and an AI image generation model and stored in SQLite. (Previously FR3)
*   **FR-CORE-02:** All images must be downloaded and stored locally. (Previously FR5)
*   **FR-CORE-03:** Logging captures all key system and user activities. (Previously FR8)
*   **FR-CORE-04:** The app must run locally with a fully functioning backend and frontend. (Previously FR9)

## 4.2 User Interface & Experience
*   **FR-UI-01:** Users can preview the generated story and export it as a PDF. (Previously FR4)
*   **FR-UI-02:** Users can sort selectable options in forms (e.g., genres) alphabetically/numerically. (Previously FR11)

## 4.3 User Management & Authentication
*   **FR-AUTH-01:** Users can log in and access previous stories securely. (Previously FR1)
*   **FR-AUTH-02:** User Registration: Users can create a new account. (Previously FR26 - Implemented)
*   **FR-AUTH-03:** User Login: Registered users can log in to their accounts. (Previously FR27 - Implemented)
*   **FR-AUTH-04:** Forgot Password: Users can reset their password if they forget it. (Previously FR28, replaces old FR15)
*   **FR-AUTH-05:** Token Refresh Mechanism (Frontend): Implement a token refresh mechanism on the frontend to attempt to automatically renew expired access tokens, if a refresh token system is in place, to minimize session interruptions. (Previously FR29)
*   **FR-AUTH-06:** Clear 401 Error Handling (Frontend): When a 401 Unauthorized error occurs (e.g., due to an expired or invalid token), display a clear message to the user on the frontend, prompting them to log in again to continue. (Previously FR30)

## 4.4 Story Creation & Management
*   **FR-STORY-01:** Users can input story data and select a genre via a form. (Previously FR2)
*   **FR-STORY-02:** Each story page must have an image, including the story title page. (Previously FR6)
*   **FR-STORY-03:** Users can define detailed character attributes for consistent image generation, including upfront reference images. (Previously FR12)
*   **FR-STORY-04:** Users can adjust the ratio of words to pictures per page. (Previously FR13)
*   **FR-STORY-05:** Users can select a visual style for the story's illustrations. (Previously FR14)
*   **FR-STORY-XX:** Users can select a writing style for the story. (New Requirement)
*   **FR-STORY-06:** Edit Story Title: Users can edit the title of a generated story after its creation. (Previously FR20 - Implemented)
*   **FR-STORY-07:** Dedicated Title Page: Each story will begin with a dedicated title page. (Previously FR21 - Implemented)
*   **FR-STORY-08:** Cover Image on Title Page: The title page will feature a prominent cover image relevant to the story's theme or main character. (Previously FR22 - Implemented)
*   **FR-STORY-09:** Use Story as Template: Users can load the details of a previously generated story into the creation form to use as a template for a new story. (Previously FR23 - Implemented Q2 2025)
*   **FR-STORY-10:** Save Story Draft: Users can save a story in progress (before generation) as a draft and resume editing it later. (Previously FR24 - Implemented Q2 2025)
*   **FR-STORY-11:** Reusable Characters: Users can create and save character profiles independently and then select from these saved characters to include in new stories. (Previously FR25)

## 4.5 AI Model Integration
*   **FR-AI-01:** JSON format from ChatGPT includes title, pages, and image prompts with keys: Title, Page, Image_description. (Previously FR7)
*   **FR-AI-02:** Update AI Model Dependencies: (Previously FRXX)
    *   Upgrade the image generation model from the current version (e.g., DALL-E 3) to a newer version (e.g., "GPT Image 1" or similar, based on availability and API compatibility).
    *   Upgrade the text generation model from GPT-4 to a newer, more capable version (e.g. like "GPT-4.1", based on availability and API compatibility).
*   **FR-AI-03: Configurable Image Generation Style Mapping:**
    *   The mapping between the application's defined `ImageStyle` (e.g., `CARTOON`, `PHOTOREALISTIC`, `FANTASY_ART`) and the OpenAI Image API's `style` parameter (which accepts `vivid` or `natural`) shall be configurable by an administrator.
    *   The system will store these mappings (e.g., `FANTASY_ART` -> `vivid`, `PHOTOREALISTIC` -> `natural`).
    *   When generating an image, the backend will look up the user-selected `ImageStyle`, retrieve its corresponding OpenAI `style` parameter from the configuration, and use it in the API call.
    *   **Default Behavior:** If an `ImageStyle` does not have a specific mapping configured by the admin, the system shall default to using `vivid` for the OpenAI `style` parameter.

## 4.6 Administration
*   **FR-ADM-01:** Admin Role: An administrator role with elevated privileges will exist. (Previously FR16 - new context)
*   **FR-ADM-02:** User Management (Admin): Admins can view, activate, deactivate, and delete user accounts. (Previously FR17 - new context)
*   **FR-ADM-03:** Content Moderation (Admin): Admins can review and remove inappropriate or low-quality generated stories. (Previously FR18 - new context)
*   **FR-ADM-04:** System Monitoring (Admin): Admins can view basic system health and usage statistics. (Previously FR19 - new context)
*   **FR-ADM-05:** Manage Dynamic UI Content and System Behavior: Admins can manage content for dynamic UI elements (e.g., image styles, genres) and configure system behaviors such as the mapping between application image styles and OpenAI API style parameters (`vivid`/`natural`) through the admin panel. (Previously original FR18, expanded)
*   **FR-ADM-06:** Populate Dropdowns from DB: Dropdown content for story creation (e.g., image styles, genres) is populated from the database and manageable by admins. (Previously original FR19)
*   **FR-ADM-07: Application Configuration Management (Admin):** Admins can manage global application settings, including API keys (e.g., OpenAI API Key) and site-wide operational parameters (e.g., maintenance mode) through the admin panel.
*   **FR-ADM-08: Detailed Logging Access (Admin):** Admins can view and filter application logs (e.g., app.log, api.log, error.log) through the admin panel for troubleshooting.
*   **FR-ADM-09: Broadcast Messaging (Admin):** Admins can create, view, and activate/deactivate broadcast messages to be displayed to users (e.g., for announcements or maintenance notifications).
*   **FR-ADM-10: Enhanced Story Statistics & Analytics (Admin):** Admins can view detailed statistics and analytics regarding story creation (e.g., number of stories, popular genres/styles) and API usage (e.g., number of calls, token estimates if possible).
*   **FR-ADM-11: Data Integrity for Dynamic Content (System/Admin):** The system will implement strategies to handle data integrity when dynamic list items (e.g., genres, image styles) are modified or deleted by an admin. This includes:
    *   Indicating in the admin panel if a dynamic list item is currently in use by existing stories.
    *   Implementing "soft deletes" (marking items as `is_active = false` but retaining them for historical data integrity). Hard deletes of in-use items should be prevented.
    *   Ensuring stories continue to display their originally selected values (e.g., genre name) even if the corresponding list item is later deactivated or its label changed. The story itself should store the value string, not just a foreign key, or have a clear mechanism to retrieve the historical value.
    *   Providing admin tools or considerations for migrating existing story data if a list item's value is critically changed (e.g., correcting a significant spelling error in a genre that should be reflected everywhere).

## 4.7 Testing
*   **FR-TEST-01:** Unit Tests: Implement comprehensive unit tests for all backend modules (CRUD operations, AI service interactions, API endpoints). (Previously FR10)

# 5. Example Prompt (for ChatGPT API)
Please generate a story that meets the following requirements. The story will be of a specific length in pages. Each page of the story will need an image description that is appropriate for use as a prompt to generate an AI-created image. The image description should be relevant to the story content on that page and consistent in visual style.

Instructions:
- The story is about a father (age 53) and his 2-year-old daughter.
- The daughter has long blonde curly hair and likes dragons.
- It should be a children’s bedtime story.
- The story must be ten pages long.

Requirements:
- The story should start with a title.
- After the text for each page, include a detailed image prompt.
- Each image description should be enclosed in JSON with the key `Image_description`.
- Use a JSON key `Page` to indicate the page number and `Title` for the story title.
- Return the response as valid JSON.

# 6. Non-Functional Requirements
*   **NFR1:** The system should respond to story creation requests within 10 seconds.
*   **NFR2:** Must support at least 5 concurrent users in a local environment.
*   **NFR3:** Maintain consistent look and feel in generated images via detailed image prompts.
*   **NFR4:** UI must be responsive on desktop and tablet browsers.
*   **NFR5:** Session management using a secret key for form and input security.





# 7. Testing and Validation
*   Unit tests for:
    *   Prompt generation
    *   JSON validation
    *   PDF generation
    *   API response handling
*   Manual tests for:
    *   Login/logout flow
    *   Story creation and editing
    *   Image generation and preview
    *   PDF export functionality
    *   Story title creation (user-defined and AI-generated) and editing.
    *   Title page generation with cover image.

# 8. Deployment & Environment
*   Runs entirely on local machine:
    *   FastAPI backend
    *   SQLite DB
    *   HTML/CSS/JS frontend
    *   Local file system for storing images and logs
*   Configuration:
    *   The app reads settings from environment variables with sensible defaults.
    *   A lightweight `backend/settings.py` provides a single source of truth for:
        *   API prefix (default `/api/v1`), run env, paths for static content (`frontend`, `data`).
        *   Logging config path (`config/logging.yaml`) and logs directory (`data/logs`).
        *   OpenAI model names and retry/backoff defaults.
        *   CORS origins.
    *   Static mounts for `/static` and `/static_content` are disabled in tests and configurable via env.

# 9. Development Progress

This section tracks the major milestones and completed work items.

## 9.1 Core Functionality Debugging & Enhancements (Completed Q2 2025)
*   Resolved critical frontend JavaScript error ("null is not an object") in `frontend/script.js` affecting character input fields, enabling proper form reset and interaction.
*   Addressed and resolved multiple backend Python errors, including:
    *   Initial 401 Unauthorized issues during login (enhanced logging in `auth.py`, `main.py` to diagnose).
    *   OpenAI API `APIRemovedInV1` errors (resolved by clearing `__pycache__`).
    *   `bcrypt` version conflict (`AttributeError: module \'bcrypt\' has no attribute \'__about__\'`) (resolved by `pip uninstall/install` of specific versions and updating `requirements.txt`).
    *   Python `ImportError` due to incorrect Uvicorn execution command (corrected command provided).
    *   `ValueError: OPENAI_API_KEY not found` due to misplaced `.env` file (moved `.env` to project root).
*   Improved backend logging in `ai_services.py` by replacing `print()` statements with structured logging for better traceability of API calls and errors.
*   Enhanced AI image generation error diagnosis by adding full prompt logging in `backend/ai_services.py` when image generation API errors occur.
*   Resolved JavaScript error "Can't find variable: resetFormAndState" in `frontend/script.js` by ensuring proper function scope and definition, improving form stability.
*   Corrected story finalization payload structure in `frontend/script.js` (addressing 422 Unprocessable Content errors) to ensure successful creation and finalization of stories, including those initiated from drafts (related to FR-STORY-10).
*   Improved user experience after story generation: users now remain on the story preview page instead of being immediately redirected to the story creation form.
*   Enhanced date display in "My Stories" view: timestamps (e.g., "Created", "Generated") are now converted to the user's local time for better readability.
*   Resolved frontend freeze during new story generation by improving error handling and ensuring spinner is hidden in `frontend/script.js`.

## 9.2 Frontend Enhancements (Completed Q2 2025)
*   Implemented clearer session timeout handling in `frontend/script.js`: On 401 errors, the application now displays a "session timed out" message and redirects the user to the login page, clearing any stale session data.

## 9.3 Project Setup & Maintenance (Completed Q2 2025)
*   Cleaned the project workspace by removing extraneous and incorrectly placed folders.
*   Initialized a Git repository for the project to enable version control.
*   Configured a remote origin and performed an initial push of the project to GitHub (`https://github.com/LeeBaker3/story_gen_for_work.git`).

## 9.4 Documentation (Ongoing)
*   Updated `product_requirements_document.md` to include a backend requirement for listing user stories.
*   Continuously updating this document to reflect new features, completed work, and pending tasks.

## 9.5 Backend Enhancements (Completed Q2 2025)
*   Fixed "Method Not Allowed" error for "My Stories" by adding a `GET /stories/` endpoint in `backend/main.py`.
*   Added a `GET /genres/` endpoint in `backend/main.py` to provide a sorted list of `StoryGenre` enum values.
*   Updated `backend/schemas.py` with a `StoryGenre` enum and modifications to `CharacterDetail`.

## 9.6 New Feature Implementation (In Progress / Pending)
### 9.6.1 Detailed Character Creation (FR-STORY-03)
*   UI for inputting detailed character attributes (age, gender, physical appearance, clothing style, key traits) - **Completed Q2 2025**
*   Backend processing of detailed character attributes for story generation prompts - **Completed Q2 2025**
*   Generation of upfront character reference images to guide the AI image generation model for consistent character depiction - **Completed Q2 2025** (Logic implemented to generate images if missing during draft finalization. Addressed `TypeError` in `ai_services.py` related to `model` kwarg. Test cases updated.)
*   Story generation background task now reliably saves images and prompt sidecar files to disk under `data/images/user_{id}/story_{id}` with DB paths persisted. Frontend serves via `/static_content`.
### 9.6.2 Adjustable Word-to-Picture Ratio (FR-STORY-04) - *Pending*
### 9.6.3 Selectable Image Styles (FR-STORY-05) - *Completed Q2 2025*
### 9.6.4 "Forgot Password" Functionality (FR-AUTH-04) - *Pending*
### 9.6.5 Admin User Role & Panel (FR-ADM-01, FR-ADM-02) - *Pending*
### 9.6.6 Database-Managed Dropdowns (FR-ADM-05, FR-ADM-06) - *Pending*
### 9.6.7 User-Defined Story Title and Title Page (FR-STORY-06, FR-STORY-07, FR-STORY-08) - *Completed Q2 2025* (Note: FRs were marked implemented, this section reflects that)
### 9.6.8 Use Story as Template (FR-STORY-09) - *Implemented Q2 2025*
### 9.6.9 Save Story Draft (FR-STORY-10) - *Implemented Q2 2025*
### 9.6.10 Reusable Characters (FR-STORY-11) - *Pending*
### 9.6.11 Frontend Interaction and Story Management Enhancements (Completed Q2 2025)
*   **Fix "Show Details" Button for Main Character:** Resolved issues with the "Show Details" button for the first character in the story creation form (`frontend/index.html`, `frontend/script.js`). This involved correcting HTML attributes and refining JavaScript functions to ensure the toggle functionality works as expected for the main character.
*   **Implement Delete Story Functionality:** Added a `DELETE /stories/{story_id}` endpoint in `backend/main.py` and corresponding frontend logic in `frontend/script.js` to allow users to delete their stories. This includes UI elements (e.g., a delete button in the "My Stories" list) and confirmation prompts. Associated tests were added in `backend/tests/test_main.py`.

## 9.7 Testing & Quality Assurance
*   Unit Tests for Backend (FR-TEST-01) - *Pending*
*   Thorough testing of all new and existing features - *Ongoing*

## 9.8 Previously Pending High-Priority Tasks (Now Addressed or Re-categorized)
*   Diagnose and Fix "Method Not Allowed" Error: Addressed (see 9.5).
*   Implement New Features:
    *   Alphabetical/numerical sorting for dropdowns: Addressed (FR-UI-02, see 9.2.2 - assuming this was part of general UI enhancements or genre endpoint).
    *   Detailed character creation UI/backend with upfront reference images: Progress tracked in 9.6.1 (FR-STORY-03).
    *   Adjustable word-to-picture ratio: Tracked in 9.6.2 (FR-STORY-04).
    *   Selectable image styles: Tracked in 9.6.3 (FR-STORY-05).
    *   Admin User Role & Panel: Tracked in 9.6.5 (FR-ADM-01, FR-ADM-02).
    *   Database-Managed Dropdowns: Tracked in 9.6.6 (FR-ADM-05, FR-ADM-06).
    *   User-Defined Story Title and Title Page: Tracked in 9.6.7 (FR-STORY-06, FR-STORY-07, FR-STORY-08).
    *   Use Story as Template: Tracked in 9.6.8 (FR-STORY-09).
    *   Save Story Draft: Tracked in 9.6.9 (FR-STORY-10).
    *   Reusable Characters: Tracked in 9.6.10 (FR-STORY-11).
*   Implement "Forgot Password" functionality: Tracked in 9.6.4 (FR-AUTH-04).
*   Continue with 8-Step Development Plan (e.g., unit tests for backend - FR-TEST-01): Tracked in 9.7.
*   Thorough testing of all existing and new features: Tracked in 9.7.

