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
	•	Select story genre (Children’s, Sci-Fi, Drama, Horror, Action).
	•	Enter:
	•	Story outline.
	•	Main characters (name, personality, background).
	•	Number of pages.
	•	Additional optional fields (tone, setting, etc.).
	•	Story Preview Page:
	•	Displays generated story per page, with accompanying image.
	•	Navigation between pages.
	•	Export options (PDF).
	•	Option to edit story and regenerate pages/images.
	•	Authentication:
	•	Secure login and session management.
	•	User dashboard showing saved stories.

3. Technical Requirements

3.1 Backend
	•	Framework: Python FastAPI
	•	OpenAI APIs:
	•	ChatGPT API: Returns story content in structured JSON format.
	•	DALL·E 3 API: Generates images based on page-specific prompts.
	•	Functionality:
	•	Accepts user inputs and sends prompts to ChatGPT.
	•	Parses and stores story and image metadata in a SQLite database.
	•	Generates PDF combining story text and locally stored images.

3.2 Frontend
	•	Technologies: HTML, CSS (site-wide), JavaScript
	•	Modern responsive design using CSS for theming.
	•	Form validation and dynamic content updates.

3.3 Database
	•	Database Type: SQLite
	•	Entities:
	•	Users (username, password hash, session token)
	•	Stories (title, outline, genre, metadata)
	•	Pages (story_id, page_number, text, image_description, image_path)
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

8. Deployment & Environment
	•	Runs entirely on local machine:
	•	FastAPI backend
	•	SQLite DB
	•	HTML/CSS/JS frontend
	•	Local file system for storing images and logs