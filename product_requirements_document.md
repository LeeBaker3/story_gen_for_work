1. Purpose

The Story Generator Web App is a web-based application that allows users to generate custom illustrated stories using AI. It leverages the OpenAI ChatGPT API for story generation and DALL·E 3 for generating corresponding illustrations. Users can log in, input story parameters, preview, edit, and export stories as PDFs.

2. Features and Functionality

2.1 User Interface (UI)
	•	Homepage:
	•	Modern, clean design.
	•	Options to:
	•	Create a new story.
	•	Log in / Sign up.
	•	Browse previously created stories.
	•	Story Creation Form:
	•	Select story genre (Children’s, Sci-Fi, Drama, Horror, Action). Dropdowns (e.g., genre) support alphabetical/numerical sorting.
	•	Enter:
	•	Story Title (Optional. If left blank, a title will be AI-generated. Can be edited later).
	•	Story outline.
	•	Main characters (name, personality, background).
	•	Includes a collapsible, detailed character creation section. Users can specify attributes like age, gender, physical appearance (hair color, eye color, ethnicity, build), clothing style, and key personality traits. The system will provide defaults or tips to guide users. This information is used to generate upfront character reference images to guide DALL·E for consistent character depiction throughout the story.
	•	Number of pages.
	•	Option to adjust word-to-picture ratio (e.g., one image every X words/paragraphs, or one image per page as default).
	•	Option to select an image style for story illustrations (e.g., cartoon, watercolor, photorealistic).
	•	Additional optional fields (tone, setting, etc.).
	•	Story Preview Page:
	•	Displays the story, starting with a Title Page featuring the story title and a cover image.
	•	Displays generated story per page, with accompanying image.
	•	Navigation between pages.
	•	Export options (PDF).
	•	Option to edit story title, page text, and regenerate pages/images.
	•	Authentication:
	•	Secure login and session management for regular and admin users. Admin users have distinct privileges.
	•	User dashboard showing saved stories.
	•	Forgot Password functionality.
	•	Admin Panel (New Section for FR16, FR17, FR18):
	•	Accessible only to users with admin privileges.
	•	Interface for managing application-wide settings and dynamic content.
	•	Functionality to manage dropdown list items (e.g., genres, image styles).

3. Technical Requirements

3.1 Backend
	•	Framework: Python FastAPI
	•	OpenAI APIs:
	•	ChatGPT API: Returns story content in structured JSON format.
	•	DALL·E 3 API: Generates images based on page-specific prompts.
	•	Functionality:
	•	Accepts user inputs (including an optional story title) and sends prompts to ChatGPT.
	•	If no title is provided by the user, generates a suitable story title based on the outline and other parameters.
	•	Parses and stores story (including title), pages (with a dedicated title page as the first page), and image metadata in a SQLite database.
	•	Generates a cover image for the title page using DALL·E 3, based on the final story title, overall themes, and main character descriptions.
	•	Generates PDF combining story text and locally stored images.
	•	Provides an endpoint to retrieve a list of stories for the authenticated user.
	•	Generates and stores character reference images based on detailed user input, to be used in subsequent DALL·E prompts for consistency.
	•	Supports different selectable image styles for DALL·E generation, with styles potentially managed dynamically.
	•	Manages adjustable word-to-picture ratios for story layout.
	•	Implements a secure 'Forgot Password' mechanism (e.g., token-based).
	•	Implements role-based access control (RBAC) to differentiate between regular users and admins.
	•	Provides CRUD endpoints for managing dynamic list content (e.g., genres, image styles) accessible only by admins.
	•	Handles user-defined story titles, allowing for creation and updates. (New)
	•	Generates a cover image for the title page using DALL·E 3, based on the story title, themes, and character descriptions. (New)

3.2 Frontend
	•	Technologies: HTML, CSS (site-wide), JavaScript
	•	Modern responsive design using CSS for theming.
	•	Form validation and dynamic content updates.
	•	Interface for detailed character attribute input.
	•	Controls for selecting image style and word-to-picture ratio.
	•	User flow and forms for 'Forgot Password' process.

3.3 Database
	•	Database Type: SQLite
	•	Entities:
	•	Users (username, password hash, email, role (e.g., 'user', 'admin'))
	•	Stories (title, outline, genre, metadata)
	•	Pages (story_id, page_number, text, image_description, image_path)
	•	DynamicList (list_name (e.g., 'genres', 'image_styles')) (New for FR18, FR19)
	•	DynamicListItem (list_id, item_value, item_label, is_active) (New for FR18, FR19)
	•	Features:
	•	Stories are searchable by title.
	•	Users can edit and re-export stories.
	•	Image files are stored locally and linked in the DB.

3.4 Logging & Error Handling
	•	Separate local log files.
	•	Logged actions:
	•	User login/logout, story creation, edits, and exports.
	•	All API requests/responses (ChatGPT, DALL·E).
	•	Error logs (failed API calls, DB issues, image failures).
	•	Graceful failure messages for:
	•	API timeouts/failures.
	•	Image generation errors.
	•	Invalid JSON responses.

4. Functional Requirements
    FR1	Users can log in and access previous stories securely.
    FR2	Users can input story data and select a genre via a form.
    FR3	Story and image data are generated using ChatGPT and DALL·E and stored in SQLite.
    FR4	Users can preview the generated story and export it as a PDF.
    FR5	All images must be downloaded and stored locally.
    FR6	Each story page must have an image, including the story title page.
    FR7	JSON format from ChatGPT includes title, pages, and image prompts with keys: Title, Page, Image_description.
    FR8	Logging captures all key system and user activities.
    FR9	The app must run locally with a fully functioning backend and frontend.
    FR10	Generate unit test cases for backend logic and critical workflows.
    FR11 Users can sort selectable options in forms (e.g., genres) alphabetically/numerically.
    FR12 Users can define detailed character attributes for consistent image generation, including upfront reference images.
    FR13 Users can adjust the ratio of words to pictures per page.
    FR14 Users can select a visual style for the story's illustrations.
    FR15 Users can reset their password if forgotten.
    FR16 System supports an admin user role with elevated privileges. (New)
    FR17 Admins can log in and access a dedicated admin panel/functions. (New)
    FR18 Admins can manage content for dynamic UI elements (e.g., image styles, genres) through the admin panel. (New)
    FR19 Dropdown content for story creation (e.g., image styles, genres) is populated from the database and manageable by admins. (New)
    FR20 Users can specify a story title before generation or edit an AI-generated/user-provided title after generation. (New)
    FR21 Each story will have a dedicated title page as the first page, displaying the story title and a cover image. (New)
    FR22 The system will automatically generate a cover image for the title page based on the story's final title, overall themes, and main character descriptions. (New)

5. Example Prompt (for ChatGPT API)
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

6. Non-Functional Requirements
    NFR1	The system should respond to story creation requests within 10 seconds.
    NFR2	Must support at least 5 concurrent users in a local environment.
    NFR3	Maintain consistent look and feel in generated images via detailed image prompts.
    NFR4	UI must be responsive on desktop and tablet browsers.
    NFR5	Session management using a secret key for form and input security.

7. Testing and Validation
	•	Unit tests for:
	•	Prompt generation
	•	JSON validation
	•	PDF generation
	•	API response handling
	•	Manual tests for:
	•	Login/logout flow
	•	Story creation and editing
	•	Image generation and preview
	•	PDF export functionality
	•	Story title creation (user-defined and AI-generated) and editing. (New)
	•	Title page generation with cover image. (New)

8. Deployment & Environment
	•	Runs entirely on local machine:
	•	FastAPI backend
	•	SQLite DB
	•	HTML/CSS/JS frontend
	•	Local file system for storing images and logs

9. Development Progress

This section tracks the major milestones and completed work items.

9.1 Core Functionality Debugging & Enhancements (Completed Q2 2025)
    •   Resolved critical frontend JavaScript error ("null is not an object") in `frontend/script.js` affecting character input fields, enabling proper form reset and interaction.
    •   Addressed and resolved multiple backend Python errors, including:
        •   Initial 401 Unauthorized issues during login (enhanced logging in `auth.py`, `main.py` to diagnose).
        •   OpenAI API `APIRemovedInV1` errors (resolved by clearing `__pycache__`).
        •   `bcrypt` version conflict (`AttributeError: module 'bcrypt' has no attribute '__about__'`) (resolved by `pip uninstall/install` of specific versions and updating `requirements.txt`).
        •   Python `ImportError` due to incorrect Uvicorn execution command (corrected command provided).
        •   `ValueError: OPENAI_API_KEY not found` due to misplaced `.env` file (moved `.env` to project root).
    •   Improved backend logging in `ai_services.py` by replacing `print()` statements with structured logging for better traceability of API calls and errors.
    •   Confirmed core application functionality: Server starts successfully, story text generation, image generation, and PDF export are operational.

9.2 Frontend Enhancements (Completed Q2 2025)
    •   Implemented clearer session timeout handling in `frontend/script.js`: On 401 errors, the application now displays a "session timed out" message and redirects the user to the login page, clearing any stale session data.

9.3 Project Setup & Maintenance (Completed Q2 2025)
    •   Cleaned the project workspace by removing extraneous and incorrectly placed folders.
    •   Initialized a Git repository for the project to enable version control.
    •   Configured a remote origin and performed an initial push of the project to GitHub (`https://github.com/LeeBaker3/story_gen_for_work.git`).

9.4 Documentation (Ongoing)
    •   Updated `product_requirements_document.md` to include a backend requirement for listing user stories.
    •   Continuously updating this document to reflect new features, completed work, and pending tasks.

9.5 Backend Enhancements (Completed Q2 2025)
    •   Fixed "Method Not Allowed" error for "My Stories" by adding a `GET /stories/` endpoint in `backend/main.py`.
    •   Added a `GET /genres/` endpoint in `backend/main.py` to provide a sorted list of `StoryGenre` enum values.
    •   Updated `backend/schemas.py` with a `StoryGenre` enum and modifications to `CharacterDetail`.

9.6 New Feature Implementation (In Progress / Pending)
    9.6.1 Detailed Character Creation (FR12)
        *   UI for inputting detailed character attributes (age, gender, physical appearance, clothing style, key traits) - **Completed Q2 2025**
        *   Backend processing of detailed character attributes for story generation prompts - **Completed Q2 2025**
        *   Generation of upfront character reference images to guide DALL·E for consistent character depiction - *Partially Completed Q2 2025 (basic generation working, consistency needs improvement)*
    9.6.2 Adjustable Word-to-Picture Ratio (FR13) - *Pending*
    9.6.3 Selectable Image Styles (FR14) - *Completed Q2 2025*
    9.6.4 "Forgot Password" Functionality (FR15) - *Pending*
    9.6.5 Admin User Role & Panel (FR16, FR17) - *Pending* (New)
    9.6.6 Database-Managed Dropdowns (FR18, FR19) - *Pending* (New)
    9.6.7 User-Defined Story Title and Title Page (FR20, FR21, FR22) - *Pending* (New)

9.7 Testing & Quality Assurance
    •   Unit Tests for Backend (FR10) - *Pending*
    •   Thorough testing of all new and existing features - *Ongoing*

9.8 Previously Pending High-Priority Tasks (Now Addressed or Re-categorized)
    •   Diagnose and Fix "Method Not Allowed" Error: Addressed (see 9.5).
    •   Implement New Features:
        •   Alphabetical/numerical sorting for dropdowns: Addressed (see 9.2.2).
        •   Detailed character creation UI/backend with upfront reference images: Progress tracked in 9.6.1.
        •   Adjustable word-to-picture ratio: Tracked in 9.6.2.
        •   Selectable image styles: Tracked in 9.6.3.
        •   Admin User Role & Panel: Tracked in 9.6.5.
        •   Database-Managed Dropdowns: Tracked in 9.6.6.
        •   User-Defined Story Title and Title Page: Tracked in 9.6.7.
    •   Implement "Forgot Password" functionality: Tracked in 9.6.4.
    •   Continue with 8-Step Development Plan (e.g., unit tests for backend - FR10): Tracked in 9.7.
    •   Thorough testing of all existing and new features: Tracked in 9.7.