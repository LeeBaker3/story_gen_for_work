const API_BASE_URL = 'http://127.0.0.1:8000'; // Define the base URL for API calls
console.log("script.js file loaded and parsed by the browser.");

document.addEventListener('DOMContentLoaded', function () {
    // console.log('<<<<< SCRIPT_JS_VERSION_DEBUG_A - DOMContentLoaded >>>>>');
    // Variable declarations (ensure authToken is declared only once here)
    const navLoginSignup = document.getElementById('nav-login-signup');
    const navCreateStory = document.getElementById('nav-create-story');
    const navBrowseStories = document.getElementById('nav-browse-stories');
    const navLogout = document.getElementById('nav-logout');

    // Sections
    const authSection = document.getElementById('auth-section');
    const storyCreationSection = document.getElementById('story-creation-section');
    const storyPreviewSection = document.getElementById('story-preview-section');
    const browseStoriesSection = document.getElementById('browse-stories-section');
    const messageArea = document.getElementById('api-message');

    // Forms
    const loginForm = document.getElementById('login-form');
    const signupForm = document.getElementById('signup-form');
    const storyCreationForm = document.getElementById('story-creation-form');

    // Auth view toggle links
    const showSignupLink = document.getElementById('show-signup-link');
    const showLoginLink = document.getElementById('show-login-link');

    // Buttons
    const addCharacterButton = document.getElementById('add-character-button');
    const exportPdfButton = document.getElementById('export-pdf-button');
    const generateStoryButton = document.getElementById('generate-story-button'); // Assuming this ID for the main submit button
    const saveDraftButton = document.getElementById('save-draft-button');

    // Corrected: authToken declared once.
    let authToken = localStorage.getItem('authToken');

    // State variables for draft editing
    let currentStoryId = null;
    let currentStoryIsDraft = false;

    // Content Areas
    const storyPreviewContent = document.getElementById('story-preview-content');
    const userStoriesList = document.getElementById('user-stories-list');

    let characterCount = 1;

    // Spinner Elements
    const spinner = document.getElementById('spinner');

    // --- RESET FUNCTION (MOVED HERE) ---
    function resetFormAndState() {
        console.log('[resetFormAndState] Attempting to reset form and state.');
        if (storyCreationForm) {
            storyCreationForm.reset();
            console.log('[resetFormAndState] storyCreationForm reset called.');
        } else {
            console.error('[resetFormAndState] storyCreationForm is null!');
        }

        // Clear existing dynamic characters (beyond the first one if it's static or part of the template)
        const characterEntries = document.querySelectorAll('#main-characters-fieldset .character-entry');
        console.log(`[resetFormAndState] Found ${characterEntries.length} character entries.`);
        characterEntries.forEach((entry, index) => {
            if (index > 0) { // Keep the first entry (index 0)
                entry.remove();
                console.log(`[resetFormAndState] Removed character entry ${index + 1}.`);
            } else { // Reset fields of the first character entry
                const nameInput = entry.querySelector('input[id^="char-name-"]');
                if (nameInput) nameInput.value = '';

                const ageInput = entry.querySelector('input[id^="char-age-"]');
                if (ageInput) ageInput.value = '';

                const genderInput = entry.querySelector('input[id^="char-gender-"]');
                if (genderInput) genderInput.value = '';

                const physicalTextarea = entry.querySelector('textarea[id^="char-physical-appearance-"]');
                if (physicalTextarea) physicalTextarea.value = '';

                const clothingTextarea = entry.querySelector('textarea[id^="char-clothing-style-"]');
                if (clothingTextarea) clothingTextarea.value = '';

                const traitsTextarea = entry.querySelector('textarea[id^="char-key-traits-"]');
                if (traitsTextarea) traitsTextarea.value = '';

                // Ensure details are hidden for the first character
                const detailsDiv = entry.querySelector('div[id^="char-details-"]');
                const toggleButton = entry.querySelector('button[id^="char-details-toggle-"]');
                if (detailsDiv) detailsDiv.style.display = 'none';
                if (toggleButton) toggleButton.textContent = 'Show Details';
                console.log('[resetFormAndState] Reset fields for first character entry.');
            }
        });
        characterCount = 1; // Reset character count
        console.log('[resetFormAndState] characterCount reset to 1.');

        // Reset draft-specific state
        currentStoryId = null;
        currentStoryIsDraft = false;
        console.log('[resetFormAndState] currentStoryId and currentStoryIsDraft reset.');

        if (generateStoryButton) {
            generateStoryButton.textContent = 'Generate Story'; // Reset button text for new story
            console.log('[resetFormAndState] generateStoryButton text reset.');
        }

        // Explicitly clear the title field
        const storyTitleInput = document.getElementById('story-title');
        if (storyTitleInput) {
            storyTitleInput.value = '';
            console.log('[resetFormAndState] Story title input cleared.');
        }

        // Hide PDF button as no story is actively being previewed after a reset from creation
        if (exportPdfButton) {
            exportPdfButton.style.display = 'none';
            console.log('[resetFormAndState] exportPdfButton hidden.');
        }

        showSection(storyCreationSection); // Ensure the creation form is visible
        displayMessage('Form cleared. Ready for a new story.', 'info');
        console.log('[resetFormAndState] Form fields and draft state reset. Navigated to story creation section.');
    }


    // --- INITIALIZATION ---
    initializeCharacterDetailsToggle(document.querySelector('.character-details-toggle'));
    updateNav(!!authToken);
    if (!!authToken) {
        showSection(storyCreationSection);
        populateGenreDropdown(); // Populate genres on load if logged in
        // Add first character entry if not already present by HTML
        if (document.querySelectorAll('#main-characters-fieldset .character-entry').length === 0) {
            addCharacterEntry();
        }
    } else {
        showSection(authSection);
    }

    // --- UTILITY FUNCTIONS ---
    function showSpinner() {
        if (spinner) spinner.style.display = 'block';
    }
    function hideSpinner() {
        if (spinner) spinner.style.display = 'none';
    }
    // Function to initialize a character details toggle
    function initializeCharacterDetailsToggle(toggleButton) {
        if (!toggleButton) return;
        const charNum = toggleButton.id.split('-').pop();
        const detailsDiv = document.getElementById(`char-details-${charNum}`);
        if (!detailsDiv) return;

        // Set initial state based on whether details are visible or not
        // This assumes details are hidden by default via CSS or inline style
        if (detailsDiv.style.display === 'block') {
            toggleButton.textContent = 'Hide Details';
        } else {
            detailsDiv.style.display = 'none'; // Ensure it's hidden if not 'block'
            toggleButton.textContent = 'Show Details';
        }

        toggleButton.addEventListener('click', () => {
            if (detailsDiv.style.display === 'none') {
                detailsDiv.style.display = 'block';
                toggleButton.textContent = 'Hide Details';
            } else {
                detailsDiv.style.display = 'none';
                toggleButton.textContent = 'Show Details';
            }
        });
    }

    // Function to add a new character entry to the form
    function addCharacterEntry() {
        console.log("'Add Character' button clicked. addCharacterEntry function started.");
        characterCount++;
        const fieldset = document.getElementById('main-characters-fieldset');
        if (!fieldset) {
            console.error('CRITICAL ERROR: Main characters fieldset (id: main-characters-fieldset) not found! Cannot add new character entry.');
            return;
        }
        console.log("Main characters fieldset found. Proceeding to add new character entry.");

        const newCharacterEntry = document.createElement('div');
        newCharacterEntry.classList.add('character-entry');
        newCharacterEntry.innerHTML = `
            <hr>
            <h4>Character ${characterCount} <button type="button" class="character-details-toggle" id="char-details-toggle-${characterCount}">Show Details</button></h4>
            <div class="form-group">
                <label for="char-name-${characterCount}">Name:</label>
                <input type="text" id="char-name-${characterCount}" name="char-name-${characterCount}" required>
            </div>
            <div id="char-details-${characterCount}" class="character-details-fields" style="display: none;">
                <div class="form-group">
                    <label for="char-age-${characterCount}">Age (Optional):</label>
                    <input type="number" id="char-age-${characterCount}" name="char-age-${characterCount}">
                </div>
                <div class="form-group">
                    <label for="char-gender-${characterCount}">Gender (Optional):</label>
                    <input type="text" id="char-gender-${characterCount}" name="char-gender-${characterCount}">
                </div>
                <div class="form-group">
                    <label for="char-physical-appearance-${characterCount}">Physical Appearance (Optional):</label>
                    <textarea id="char-physical-appearance-${characterCount}" name="char-physical-appearance-${characterCount}" rows="2"></textarea>
                </div>
                <div class="form-group">
                    <label for="char-clothing-style-${characterCount}">Clothing Style (Optional):</label>
                    <textarea id="char-clothing-style-${characterCount}" name="char-clothing-style-${characterCount}" rows="2"></textarea>
                </div>
                <div class="form-group">
                    <label for="char-key-traits-${characterCount}">Key Traits/Habits (Optional):</label>
                    <textarea id="char-key-traits-${characterCount}" name="char-key-traits-${characterCount}" rows="2"></textarea>
                </div>
            </div>
        `;
        fieldset.appendChild(newCharacterEntry);

        // Initialize the toggle for the new character entry
        const newToggle = newCharacterEntry.querySelector('.character-details-toggle');
        if (newToggle) {
            initializeCharacterDetailsToggle(newToggle);
        }
    }

    // Event listener for the "Add Another Character" button
    if (addCharacterButton) {
        addCharacterButton.addEventListener('click', addCharacterEntry);
        console.log("Event listener for 'Add Character' button (add-character-button) attached successfully.");
    } else {
        console.error("CRITICAL ERROR: 'Add Character' button (id: add-character-button) not found in the DOM. This feature will not work.");
    }

    // --- UTILITY FUNCTIONS ---
    function formatDate(dateString) {
        if (!dateString) return 'N/A';

        let processedDateString = dateString;
        // Check if the date string looks like an ISO string without timezone information
        // e.g., "2023-10-27T10:30:00" or "2023-10-27T10:30:00.123456"
        // If so, append 'Z' to treat it as UTC.
        // This regex checks for "T" and no "Z" at the end, and no explicit offset like +05:00 or -0800.
        if (processedDateString.includes('T') && !processedDateString.endsWith('Z') && !/[+-]\\d{2}:?\\d{2}$/.test(processedDateString)) {
            processedDateString += 'Z';
        }

        const date = new Date(processedDateString);

        // Check if the date is valid after processing
        if (isNaN(date.getTime())) {
            console.warn(`[formatDate] Could not parse date string: ${dateString} (processed as ${processedDateString}). Returning original.`);
            return dateString; // Or 'Invalid Date' or 'N/A'
        }

        const options = {
            year: 'numeric', month: 'long', day: 'numeric',
            hour: '2-digit', minute: '2-digit',
            // timeZoneName: 'short' // Optional: to show timezone like PST, EST if desired
        };
        return date.toLocaleString(undefined, options); // Using toLocaleString for date and time
    }

    // Function to render the story preview
    function displayStory(story) {
        if (!storyPreviewContent || !story) {
            console.error('[displayStory] Story preview content area or story data is missing.');
            displayMessage('Could not display story preview.', 'error');
            if (exportPdfButton) exportPdfButton.style.display = 'none';
            return;
        }

        console.log('[displayStory] Story object received:', JSON.parse(JSON.stringify(story)));
        currentStoryId = story.id; // Store current story ID for reuse

        storyPreviewContent.innerHTML = ''; // Clear previous content

        // --- Main Story Title with Edit Functionality ---
        const titleContainer = document.createElement('div');
        titleContainer.classList.add('story-main-title-container');

        const mainStoryTitleElement = document.createElement('h2');
        mainStoryTitleElement.textContent = story.title || 'Untitled Story';
        mainStoryTitleElement.classList.add('story-main-title');
        mainStoryTitleElement.id = `story-title-text-${story.id}`; // ID for easy access
        mainStoryTitleElement.style.display = 'inline'; // Ensure it's inline from the start

        const editTitleIcon = document.createElement('span');
        editTitleIcon.textContent = ' ✏️'; // Pencil emoji for edit
        editTitleIcon.classList.add('edit-title-icon');
        editTitleIcon.style.cursor = 'pointer';
        editTitleIcon.title = 'Edit title';
        editTitleIcon.id = `edit-title-icon-${story.id}`;

        const titleEditForm = document.createElement('div');
        titleEditForm.classList.add('title-edit-form');
        titleEditForm.style.display = 'none'; // Hidden by default
        titleEditForm.id = `title-edit-form-${story.id}`;

        const titleInput = document.createElement('input');
        titleInput.type = 'text';
        titleInput.classList.add('title-edit-input');
        titleInput.value = story.title || 'Untitled Story';

        const saveTitleButton = document.createElement('button');
        saveTitleButton.textContent = 'Save';
        saveTitleButton.classList.add('save-title-button');

        const cancelTitleButton = document.createElement('button');
        cancelTitleButton.textContent = 'Cancel';
        cancelTitleButton.classList.add('cancel-title-button');

        titleEditForm.appendChild(titleInput);
        titleEditForm.appendChild(saveTitleButton);
        titleEditForm.appendChild(cancelTitleButton);

        titleContainer.appendChild(mainStoryTitleElement);
        titleContainer.appendChild(editTitleIcon);
        titleContainer.appendChild(titleEditForm);
        storyPreviewContent.appendChild(titleContainer);

        editTitleIcon.addEventListener('click', () => {
            mainStoryTitleElement.style.display = 'none';
            editTitleIcon.style.display = 'none';
            titleEditForm.style.display = 'inline-block'; // Or 'flex' if using flexbox for layout
            titleInput.value = mainStoryTitleElement.textContent; // Ensure current value
            titleInput.focus();
        });

        saveTitleButton.addEventListener('click', async () => {
            const newTitle = titleInput.value.trim();
            if (newTitle && newTitle !== mainStoryTitleElement.textContent) {
                await updateStoryTitle(story.id, newTitle, mainStoryTitleElement, editTitleIcon, titleEditForm);
            } else if (!newTitle) {
                displayMessage('Title cannot be empty.', 'warning');
            } else { // No change
                mainStoryTitleElement.style.display = 'inline';
                editTitleIcon.style.display = 'inline';
                titleEditForm.style.display = 'none';
            }
        });

        cancelTitleButton.addEventListener('click', () => {
            mainStoryTitleElement.style.display = 'inline'; // Or 'block' or 'initial' based on original display
            editTitleIcon.style.display = 'inline';
            titleEditForm.style.display = 'none';
            // Optionally reset input value if needed: titleInput.value = mainStoryTitleElement.textContent;
        });
        // --- End Main Story Title with Edit Functionality ---


        if (story.pages && story.pages.length > 0) {
            console.log('[displayStory] story.pages.length:', story.pages.length);

            // Sort pages to ensure title page (page_number 0) is first, then others by page_number
            const sortedPages = story.pages.sort((a, b) => {
                // Ensure page_number is treated as a number for sorting, even if it's a string like "0" or "Title" (which becomes 0)
                const pageNumA = parseInt(a.page_number, 10);
                const pageNumB = parseInt(b.page_number, 10);
                return pageNumA - pageNumB;
            });

            sortedPages.forEach((page, index) => {
                console.log(`[displayStory] Processing page data (Page Number: ${page.page_number}):`, JSON.parse(JSON.stringify(page)));

                const pageContainer = document.createElement('div');

                // Check if it's the title page (page_number 0)
                // The backend converts "Title" to 0, so we check for numeric 0.
                if (parseInt(page.page_number, 10) === 0) {
                    pageContainer.classList.add('story-title-page-preview');

                    // Title from page.text (should be the story title for page 0)
                    if (page.text) {
                        const titlePageTitleElement = document.createElement('h3'); // Title on the title page
                        titlePageTitleElement.classList.add('title-page-story-title');
                        titlePageTitleElement.textContent = page.text;
                        pageContainer.appendChild(titlePageTitleElement);
                    }

                    // Cover image for title page
                    if (page.image_path) {
                        const imageElement = document.createElement('img');
                        imageElement.classList.add('title-page-cover-image');
                        // Ensure the path is correctly formed for static content
                        if (page.image_path.startsWith('data/')) {
                            imageElement.src = '/static_content/' + page.image_path.substring('data/'.length);
                        } else if (page.image_path.startsWith('/static_content/')) {
                            imageElement.src = page.image_path; // Already correctly prefixed
                        } else {
                            // Assuming it might be a relative path that needs the prefix
                            imageElement.src = '/static_content/' + page.image_path;
                        }
                        imageElement.alt = story.title ? `Cover image for ${story.title}` : 'Cover image';
                        // Basic styling for preview - can be enhanced with CSS
                        imageElement.style.maxWidth = '80%';
                        imageElement.style.maxHeight = '400px';
                        imageElement.style.display = 'block';
                        imageElement.style.margin = '20px auto'; // Center it a bit
                        pageContainer.appendChild(imageElement);
                    } else if (page.image_description) { // Fallback to description if no image
                        const descElement = document.createElement('p');
                        descElement.style.fontStyle = 'italic';
                        descElement.textContent = `Cover Image Description: ${page.image_description}`;
                        pageContainer.appendChild(descElement);
                    }
                } else { // Regular content page
                    pageContainer.classList.add('story-content-page-preview');

                    const pageNumberElement = document.createElement('h4');
                    pageNumberElement.textContent = `Page ${page.page_number}`;
                    pageContainer.appendChild(pageNumberElement);

                    if (page.text) {
                        const textElement = document.createElement('p');
                        textElement.textContent = page.text;
                        pageContainer.appendChild(textElement);
                    }

                    if (page.image_path) {
                        const imageElement = document.createElement('img');
                        imageElement.classList.add('content-page-image');
                        // Ensure the path is correctly formed for static content
                        if (page.image_path.startsWith('data/')) {
                            imageElement.src = '/static_content/' + page.image_path.substring('data/'.length);
                        } else if (page.image_path.startsWith('/static_content/')) {
                            imageElement.src = page.image_path; // Already correctly prefixed
                        } else {
                            // Assuming it might be a relative path that needs the prefix
                            imageElement.src = '/static_content/' + page.image_path;
                        }
                        imageElement.alt = `Image for page ${page.page_number}`;
                        imageElement.style.maxWidth = '300px';
                        imageElement.style.maxHeight = '300px';
                        imageElement.style.display = 'block';
                        imageElement.style.marginTop = '10px';
                        imageElement.style.marginBottom = '10px';
                        pageContainer.appendChild(imageElement);
                    } else if (page.image_description) {
                        const descElement = document.createElement('p');
                        descElement.style.fontStyle = 'italic';
                        descElement.textContent = `Image Description: ${page.image_description}`;
                        pageContainer.appendChild(descElement);
                    }
                }

                storyPreviewContent.appendChild(pageContainer);
                // Add a separator if not the last page (considering sortedPages)
                if (index < sortedPages.length - 1) {
                    storyPreviewContent.appendChild(document.createElement('hr'));
                }
            });
        } else {
            const noPagesElement = document.createElement('p');
            noPagesElement.textContent = 'This story has no pages or page data is missing.';
            storyPreviewContent.appendChild(noPagesElement);
        }

        if (exportPdfButton) {
            const shouldShowButton = story.pages && story.pages.length > 0;
            console.log('[displayStory] Condition (story.pages && story.pages.length > 0):', shouldShowButton);
            exportPdfButton.style.display = shouldShowButton ? 'block' : 'none';
            console.log('[displayStory] exportPdfButton display set to:', exportPdfButton.style.display);
        } else {
            console.error('[displayStory] exportPdfButton element is NULL or undefined!');
        }
    }

    function showSection(sectionToShow) {
        // Clear message area when changing sections
        if (messageArea) {
            messageArea.textContent = '';
            messageArea.style.backgroundColor = 'transparent'; // Reset background
            messageArea.style.border = 'none'; // Reset border
        }
        [authSection, storyCreationSection, storyPreviewSection, browseStoriesSection].forEach(section => {
            section.style.display = 'none';
        });
        if (sectionToShow) {
            sectionToShow.style.display = 'block';
            // If showing auth section, ensure login form is visible and signup is hidden by default
            if (sectionToShow === authSection) {
                loginForm.style.display = 'block';
                signupForm.style.display = 'none';
                const authSectionHeading = authSection.querySelector('h2');
                if (authSectionHeading) {
                    authSectionHeading.textContent = 'Login';
                }
            }
            // When navigating TO storyPreviewSection directly (e.g. from browse),
            // we don't know if a story is loaded yet, so PDF button should be hidden.
            // displayStory will manage its visibility based on actual content.
            if (sectionToShow === storyPreviewSection) {
                if (exportPdfButton) exportPdfButton.style.display = 'none';
            }
        }
    }

    function displayMessage(message, type = 'info') { // type can be 'info', 'success', 'warning', 'error'
        messageArea.textContent = String(message); // Ensure message is always a string

        switch (type) {
            case 'error':
                messageArea.style.color = '#FF6B6B'; // Red
                messageArea.style.backgroundColor = 'rgba(255, 107, 107, 0.1)';
                messageArea.style.border = '1px solid rgba(255, 107, 107, 0.3)';
                break;
            case 'warning':
                messageArea.style.color = '#FFA500'; // Orange
                messageArea.style.backgroundColor = 'rgba(255, 165, 0, 0.1)';
                messageArea.style.border = '1px solid rgba(255, 165, 0, 0.3)';
                break;
            case 'success':
                messageArea.style.color = '#6BFF6B'; // Green
                messageArea.style.backgroundColor = 'rgba(107, 255, 107, 0.1)';
                messageArea.style.border = '1px solid rgba(107, 255, 107, 0.3)';
                break;
            case 'info':
            default:
                messageArea.style.color = '#ADD8E6'; // Light Blue for info
                messageArea.style.backgroundColor = 'rgba(173, 216, 230, 0.1)';
                messageArea.style.border = '1px solid rgba(173, 216, 230, 0.3)';
                break;
        }
        messageArea.style.padding = '0.8rem';
        messageArea.style.borderRadius = '4px';
    }

    function updateNav(isLoggedIn) {
        if (isLoggedIn) {
            navLoginSignup.style.display = 'none';
            navCreateStory.style.display = 'inline-block';
            navBrowseStories.style.display = 'inline-block';
            navLogout.style.display = 'inline-block';
        } else {
            navLoginSignup.style.display = 'inline-block';
            navCreateStory.style.display = 'none';
            navBrowseStories.style.display = 'none';
            navLogout.style.display = 'none';
            showSection(authSection);
        }
    }

    // --- API CALLS ---
    async function apiRequest(endpoint, method = 'GET', body = null, isFormData = false) {
        // console.log('<<<<< SCRIPT_JS_VERSION_DEBUG_A - apiRequest - START >>>>>');
        try {
            // console.log('[apiRequest] Received body parameter (cleaned):', body === null ? null : JSON.parse(JSON.stringify(body)));
        } catch (e) {
            console.error('[apiRequest] Could not stringify/parse received body param for logging:', e, body);
        }
        // console.log('[apiRequest] Received endpoint:', endpoint, 'Method:', method, 'isFormData:', isFormData);

        const token = localStorage.getItem('authToken'); // Corrected: Use 'authToken'
        const headers = {
            'Authorization': `Bearer ${token}`
        };
        if (!isFormData) {
            headers['Content-Type'] = 'application/json';
        }

        const options = {
            method: method,
            headers: headers
        };

        if (body !== null && !isFormData) {
            // console.log('<<<<< SCRIPT_JS_VERSION_DEBUG_A - apiRequest - STEP 1 - Stringifying body for options.body >>>>>');
            try {
                options.body = JSON.stringify(body);
                // console.log('<<<<< SCRIPT_JS_VERSION_DEBUG_A - apiRequest - STEP 2 - options.body after stringify >>>>>');
                // console.log('[apiRequest] options.body (this is the string that will be sent):', options.body);
            } catch (e) {
                // console.error('<<<<< SCRIPT_JS_VERSION_DEBUG_A - apiRequest - ERROR STRINGIFYING BODY >>>>>', e);
                console.error('[apiRequest] Body object that failed to stringify:', body);
                // Display error to user and stop
                displayMessage('Error preparing data for the server. See console for details.', 'error');
                hideSpinner();
                throw e;
            }
        } else if (body !== null && isFormData) {
            options.body = body;
            console.log('[apiRequest] options.body is FormData.');
        }

        // console.log('<<<<< SCRIPT_JS_VERSION_DEBUG_A - apiRequest - STEP 3 - Final options object before fetch >>>>>');
        // console.log('[apiRequest] Final options object structure (logged directly):', options);
        try {
            // console.log('[apiRequest] Final options object (cleaned for inspection):', JSON.parse(JSON.stringify(options)));
        } catch (e) {
            console.error('[apiRequest] Could not stringify/parse final options for logging:', e, options);
        }

        // console.log('[apiRequest] Attempting to fetch URL:', `${API_BASE_URL}${endpoint}`);
        try {
            const response = await fetch(`${API_BASE_URL}${endpoint}`, options);
            // console.log('<<<<< SCRIPT_JS_VERSION_DEBUG_A - apiRequest - STEP 4 - Fetch returned >>>>>');
            // console.log('[apiRequest] Response status:', response.status, 'Response ok:', response.ok);

            let responseData;

            if (!response.ok) {
                // console.log('<<<<< SCRIPT_JS_VERSION_DEBUG_A - apiRequest - STEP 5A - Response NOT OK >>>>>');
                try {
                    responseData = await response.json();
                    // console.log('[apiRequest] Error response data (JSON):', responseData);
                } catch (e) {
                    // console.log('[apiRequest] Error response data (not JSON or failed to parse):', e);
                    const errorText = await response.text().catch(() => response.statusText);
                    responseData = { detail: errorText || `HTTP error! Status: ${response.status}` };
                }
                const errorDetail = responseData && responseData.detail ? responseData.detail : `Unknown error. Status: ${response.status}`;
                console.error(`[apiRequest] API Error: ${errorDetail}`, responseData);
                // Avoid duplicate displayMessage if one was already set by a more specific handler
                if (!messageArea.textContent.includes('Failed') && !messageArea.textContent.includes('error')) {
                    displayMessage(String(errorDetail), 'error');
                }
                throw new Error(String(errorDetail));
            }

            // If response.ok is true
            // console.log('<<<<< SCRIPT_JS_VERSION_DEBUG_A - apiRequest - STEP 5B - Response OK, processing body >>>>>');
            try {
                const contentType = response.headers.get("content-type");
                if (response.status === 204 || response.headers.get("content-length") === "0") {
                    responseData = null;
                    // console.log('[apiRequest] Success response data (No Content / Empty Body)');
                } else if (contentType && contentType.indexOf("application/json") !== -1) {
                    responseData = await response.json();
                    // console.log('[apiRequest] Success response data (JSON):', responseData);
                } else {
                    responseData = await response.text();
                    // console.log('[apiRequest] Success response data (Text):', responseData);
                }
            } catch (e) {
                // console.error('<<<<< SCRIPT_JS_VERSION_DEBUG_A - apiRequest - ERROR PARSING SUCCESS RESPONSE BODY >>>>>', e);
                displayMessage('Error processing server response. See console.', 'error');
                throw e;
            }

            // console.log('<<<<< SCRIPT_JS_VERSION_DEBUG_A - apiRequest - STEP 6 - Returning responseData >>>>>');
            return responseData;
        } catch (error) {
            // console.error('<<<<< SCRIPT_JS_VERSION_DEBUG_A - apiRequest - FETCH FAILED or error in response handling >>>>>', error);
            hideSpinner();
            if (!messageArea.textContent.includes('Failed') && !messageArea.textContent.includes('error')) {
                displayMessage(error.message || 'An unexpected error occurred. Please check the console.', 'error');
            }
            throw error;
        }
    }

    // New function to update story title
    async function updateStoryTitle(storyId, newTitle, titleTextElement, editIconElement, editFormElement) {
        showSpinner();
        try {
            const updatedStory = await apiRequest(`/stories/${storyId}/title`, 'PUT', { title: newTitle });
            if (updatedStory && updatedStory.title) {
                titleTextElement.textContent = updatedStory.title;
                displayMessage('Story title updated successfully!', 'success');
                // Also update the title on the title page if it's rendered
                const titlePageTitleElem = storyPreviewContent.querySelector('.title-page-story-title');
                if (titlePageTitleElem && parseInt(titlePageTitleElem.closest('.story-title-page-preview').dataset.pageNumber, 10) === 0) {
                    titlePageTitleElem.textContent = updatedStory.title;
                }

            } else {
                displayMessage('Failed to update title: No updated story data returned.', 'error');
            }
        } catch (error) {
            console.error('Failed to update story title:', error);
            // Error message is already displayed by apiRequest
            // displayMessage(`Error updating title: ${error.message || 'Unknown error'}`, 'error');
        } finally {
            hideSpinner();
            // Reset UI
            titleTextElement.style.display = 'inline'; // Or 'block' or 'initial'
            editIconElement.style.display = 'inline';
            editFormElement.style.display = 'none';
        }
    }


    // --- POPULATE DYNAMIC FORM ELEMENTS ---
    async function populateGenreDropdown() {
        const genreSelect = storyCreationForm.genre;
        if (!genreSelect) {
            console.error('Genre select element not found.');
            return;
        }

        try {
            const genres = await apiRequest('/genres/'); // No token needed for public genres
            genreSelect.innerHTML = ''; // Clear existing options
            if (genres && genres.length > 0) {
                genres.forEach(genre => {
                    const option = document.createElement('option');
                    option.value = genre;
                    option.textContent = genre;
                    genreSelect.appendChild(option);
                });
            } else {
                displayMessage('Could not load story genres.', 'error');
            }
        } catch (error) {
            displayMessage('Failed to load story genres. Please try refreshing.', 'error');
        }
    }

    // Event listeners for switching between login and signup views
    if (showSignupLink) {
        showSignupLink.addEventListener('click', (e) => {
            e.preventDefault();
            if (loginForm && signupForm && authSection) {
                loginForm.style.display = 'none';
                signupForm.style.display = 'block';
                const authSectionHeading = authSection.querySelector('h2');
                if (authSectionHeading) {
                    authSectionHeading.textContent = 'Sign Up';
                }
            }
        });
    }

    if (showLoginLink) {
        showLoginLink.addEventListener('click', (e) => {
            e.preventDefault();
            if (loginForm && signupForm && authSection) {
                signupForm.style.display = 'none';
                loginForm.style.display = 'block';
                const authSectionHeading = authSection.querySelector('h2');
                if (authSectionHeading) {
                    authSectionHeading.textContent = 'Login';
                }
            }
        });
    }

    // Event listeners for navigation
    if (navCreateStory) {
        navCreateStory.addEventListener('click', () => {
            showSection(storyCreationSection);
            storyCreationForm.reset();
            currentStoryId = null;
            currentStoryIsDraft = false; // Reset draft state
            if (generateStoryButton) {
                generateStoryButton.textContent = 'Generate Story'; // Reset button text
            }
            // Clear dynamic characters, leave the first one
            const characterEntries = document.querySelectorAll('#main-characters-fieldset .character-entry');
            characterEntries.forEach((entry, index) => {
                if (index > 0) { // Keep the first entry (index 0)
                    entry.remove();
                }
            });
            characterCount = 1; // Reset character count
            // Ensure the first character's details toggle is correctly initialized if it was hidden
            const firstCharToggle = document.querySelector('.character-details-toggle');
            if (firstCharToggle) {
                const firstCharDetails = document.getElementById('char-details-1');
                if (firstCharDetails) {
                    // Assuming default is expanded or handled by initializeCharacterDetailsToggle
                    // firstCharDetails.style.display = 'none'; 
                    // firstCharToggle.textContent = 'Show Details'; 
                }
            }
            document.getElementById('story-title').value = ''; // Clear title explicitly
            exportPdfButton.style.display = 'none';
        });
    }

    if (navBrowseStories) {
        navBrowseStories.addEventListener('click', async () => {
            showSection(browseStoriesSection);
            await loadAndDisplayUserStories(); // Fetches all (including drafts by default)
        });
    }

    // --- AUTHENTICATION --- 
    signupForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = signupForm.username.value;
        const email = signupForm.email.value; // Get email value
        const password = signupForm.password.value;
        try {
            await apiRequest('/users/', 'POST', { username, email, password }); // Add email to payload
            displayMessage('Signup successful! Please login.', 'success');
            signupForm.reset();
            loginForm.style.display = 'block';
            signupForm.style.display = 'none';
        } catch (error) {
        }
    });

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = loginForm.username.value;
        const password = loginForm.password.value;

        const formData = new URLSearchParams();
        formData.append('username', username);
        formData.append('password', password);

        try {
            const response = await fetch(`${API_BASE_URL}/token`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: formData
            });
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: response.statusText }));
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            authToken = data.access_token;
            localStorage.setItem('authToken', authToken); // Persist token
            displayMessage('Login successful!', 'success');
            updateNav(true);
            showSection(storyCreationSection); // Or browse stories
            loginForm.reset();
        } catch (error) {
            displayMessage(error.message || 'Login failed.', 'error');
        }
    });

    navLogout.addEventListener('click', () => {
        authToken = null;
        localStorage.removeItem('authToken');
        updateNav(false);
        displayMessage('Logged out.', 'info');
        currentStoryId = null;
        exportPdfButton.style.display = 'none';
    });

    // --- STORY CREATION / DRAFT HANDLING ---

    // Function to gather form data
    function getStoryDataFromForm() {
        const mainCharacters = Array.from(document.querySelectorAll('#main-characters-fieldset .character-entry')).map(entry => {
            const nameInput = entry.querySelector('input[id^="char-name-"]');
            const ageInput = entry.querySelector('input[id^="char-age-"]');
            const genderInput = entry.querySelector('input[id^="char-gender-"]');
            const physicalTextarea = entry.querySelector('textarea[id^="char-physical-appearance-"]');
            const clothingTextarea = entry.querySelector('textarea[id^="char-clothing-style-"]');
            const traitsTextarea = entry.querySelector('textarea[id^="char-key-traits-"]');

            const ageValue = ageInput ? ageInput.value.trim() : '';

            return {
                name: nameInput ? nameInput.value.trim() : '',
                age: ageValue !== '' ? parseInt(ageValue, 10) : null, // Parse to int or send null
                gender: genderInput ? genderInput.value.trim() : '',
                physical_appearance: physicalTextarea ? physicalTextarea.value.trim() : '',
                clothing_style: clothingTextarea ? clothingTextarea.value.trim() : '',
                key_traits: traitsTextarea ? traitsTextarea.value.trim() : '',
            };
        });

        const numPagesValue = document.getElementById('story-num-pages').value; // Corrected ID
        let numPagesAsInt = parseInt(numPagesValue);

        // Ensure num_pages is a positive integer, defaulting to 1 if empty, NaN, or <= 0.
        // This is to satisfy StoryCreate's requirement for num_pages: int and downstream AI logic.
        if (!numPagesValue.trim() || isNaN(numPagesAsInt) || numPagesAsInt <= 0) {
            numPagesAsInt = 1;
            // Optionally, update the form field to reflect the default:
            // document.getElementById('numPages').value = "1";
        }

        return {
            title: document.getElementById('story-title').value, // Corrected ID
            genre: document.getElementById('story-genre').value, // Corrected ID
            story_outline: document.getElementById('story-outline').value, // Corrected ID
            main_characters: mainCharacters,
            num_pages: numPagesAsInt, 
            tone: document.getElementById('story-tone').value, // Corrected ID
            setting: document.getElementById('story-setting').value, // Corrected ID
            word_to_picture_ratio: document.getElementById('story-word-to-picture-ratio').value, // Corrected ID
            text_density: document.getElementById('story-text-density').value, // Corrected ID
            image_style: document.getElementById('story-image-style').value // Corrected ID
            // is_draft will be handled by the endpoint/payload structure
        };
    }

    // Event listener for "Save Draft" button
    if (saveDraftButton) {
        saveDraftButton.addEventListener('click', async function (event) {
            event.preventDefault();
            displayMessage('Saving draft...', 'info');
            showSpinner();

            const storyData = getStoryDataFromForm();
            console.log('[SaveDraft] Story data for draft:', storyData);

            if (!storyData.genre || !storyData.story_outline) {
                displayMessage('Genre and Story Outline are required to save a draft.', 'warning');
                hideSpinner();
                return;
            }

            try {
                let savedDraft;
                if (currentStoryId && currentStoryIsDraft) {
                    console.log(`[SaveDraft] Updating existing draft ID: ${currentStoryId}`);
                    savedDraft = await apiRequest(`/stories/drafts/${currentStoryId}`, 'PUT', storyData);
                } else {
                    console.log('[SaveDraft] Creating new draft.');
                    savedDraft = await apiRequest('/stories/drafts/', 'POST', storyData);
                }

                if (savedDraft && savedDraft.id) {
                    currentStoryId = savedDraft.id;
                    currentStoryIsDraft = true;
                    document.getElementById('story-title').value = savedDraft.title || '';
                    if (generateStoryButton) {
                        generateStoryButton.textContent = 'Finalize & Generate Story';
                    }
                    displayMessage(`Draft "${savedDraft.title || 'Untitled Draft'}" saved successfully!`, 'success');
                    console.log('[SaveDraft] Draft saved/updated:', savedDraft);
                } else {
                    displayMessage('Failed to save draft. Response was not in the expected format.', 'error');
                    console.warn('[SaveDraft] Save draft response issue:', savedDraft);
                }
            } catch (error) {
                console.error('[SaveDraft] Error saving draft:', error);
                if (!messageArea.textContent.includes('Failed') && !messageArea.textContent.includes('error')) {
                    displayMessage(`Draft saving failed: ${error.message || 'Unknown error'}`, 'error');
                }
            } finally {
                hideSpinner();
            }
        });
    }

    // Modified Event listener for the main story creation/finalization form submission
    if (generateStoryButton) {
        generateStoryButton.addEventListener('click', async function (event) {
            event.preventDefault();
            // console.log('<<<<< SCRIPT_JS_VERSION_DEBUG_A - generateStoryButton - START >>>>>');
            // console.log('[FormSubmit] currentStoryId:', currentStoryId, 'currentStoryIsDraft:', currentStoryIsDraft);

            displayMessage('Generating story...', 'info');
            showSpinner();

            const storyData = getStoryDataFromForm();
            // console.log('<<<<< SCRIPT_JS_VERSION_DEBUG_A - generateStoryButton - STEP 0 - storyDataFromForm obtained >>>>>');
            try {
                // console.log('[FormSubmit] storyData from form (cleaned):', JSON.parse(JSON.stringify(storyData)));
            } catch (e) {
                // This specific try-catch for logging can be removed if it causes issues or is not needed.
                // console.error('[FormSubmit] Could not stringify/parse storyData for logging (initial log):', e, storyData);
            }
            // console.log('<<<<< SCRIPT_JS_VERSION_DEBUG_A - generateStoryButton - STEP 1 - After getting storyData >>>>>');

            let payload;
            let endpoint;
            let method;

            if (currentStoryId && currentStoryIsDraft) {
                console.log('[FormSubmit] Finalizing draft. currentStoryId:', currentStoryId);
                payload = {
                    story_input: storyData,
                    draft_id: parseInt(currentStoryId)
                };
                endpoint = `/stories/`;
                method = 'POST';
            } else if (currentStoryId && !currentStoryIsDraft) {
                console.warn('[FormSubmit] Form was populated from a finalized story, but "Generate Story" was clicked. Treating as new story creation.');
                payload = { story_input: storyData };
                endpoint = '/stories/';
                method = 'POST';
                currentStoryId = null; 
                currentStoryIsDraft = false;
            } else {
                console.log('[FormSubmit] Creating a new story from scratch.');
                payload = { story_input: storyData };
                endpoint = '/stories/';
                method = 'POST';
            }

            // console.log('<<<<< SCRIPT_JS_VERSION_DEBUG_A - generateStoryButton - STEP 2 - Payload constructed >>>>>');
            try {
                // console.log('[FormSubmit] Payload to be sent to apiRequest (cleaned):', JSON.parse(JSON.stringify(payload)));
            } catch (e) {
                // This specific try-catch for logging can be removed.
                // console.error('[FormSubmit] Could not stringify/parse payload for logging:', e, payload);
            }
            // console.log('[FormSubmit] Endpoint:', endpoint, 'Method:', method);

            try { // Main try for API call and processing
                // console.log('<<<<< SCRIPT_JS_VERSION_DEBUG_A - generateStoryButton - STEP 3 - Calling apiRequest >>>>>');
                const result = await apiRequest(endpoint, method, payload);
                // console.log('<<<<< SCRIPT_JS_VERSION_DEBUG_A - generateStoryButton - STEP 4 - apiRequest returned >>>>>');
                // console.log('[FormSubmit] API Result (type):', typeof result, 'Is null?', result === null, 'Content:', result);


                if (result && typeof result === 'object' && result.id) {
                    // console.log('<<<<< SCRIPT_JS_VERSION_DEBUG_A - generateStoryButton - STEP 4.1 - Result has ID:', result.id, 'Title:', result.title);
                    displayMessage('Story generated successfully!', 'success'); // This message will be briefly visible
                    showSection(storyPreviewSection); // This clears the messageArea

                    try {
                        displayStory(result);
                        // console.log('<<<<< SCRIPT_JS_VERSION_DEBUG_A - generateStoryButton - STEP 5 - Story processed, displayStory called >>>>>');
                    } catch (displayError) {
                        console.error("Error during displayStory:", displayError);
                        // Display a message to the user that story display failed, but generation might have succeeded.
                        displayMessage(`Error displaying story content: ${displayError.message}. The story might have been created; check 'Browse Stories'.`, 'error');
                        // The spinner will be hidden by the finally block.
                    }

                    currentStoryId = result.id;
                    currentStoryIsDraft = false; 
                    console.log('[FormSubmit] Story generation successful. Current story ID:', currentStoryId, 'Is Draft:', currentStoryIsDraft);
                    // console.log('<<<<< SCRIPT_JS_VERSION_DEBUG_A - generateStoryButton - STEP 7 - State updated >>>>>');
                } else {
                    // console.log('<<<<< SCRIPT_JS_VERSION_DEBUG_A - generateStoryButton - STEP 4.X - Result is null, undefined, not an object, or lacks id.');
                    console.error('[FormSubmit] Story generation/finalization failed or returned invalid/unexpected data:', result);
                    displayMessage('Failed to generate story. The server response was not as expected. Please check console.', 'error');
                }

            } catch (error) { // Catches errors from apiRequest itself or issues before it (e.g. payload stringify if uncommented)
                // console.error('<<<<< SCRIPT_JS_VERSION_DEBUG_A - generateStoryButton - ERROR IN API REQUEST CALL OR SUBSEQUENT HANDLING >>>>>', error);
                console.error('[FormSubmit] Error during story generation process:', error);
                // apiRequest usually displays a message on failure. This is a fallback or for more context.
                if (!messageArea.textContent.includes('Failed') && 
                    !messageArea.textContent.includes('error') && 
                    !messageArea.textContent.includes('Error generating story')) {
                    displayMessage(`Error generating story: ${error.message || 'Unknown error'}. Please check console.`, 'error');
                }
            } finally {
                hideSpinner();
                // console.log('<<<<< SCRIPT_JS_VERSION_DEBUG_A - generateStoryButton - FINALLY - Spinner hidden >>>>>');
            }
        });
    } else {
        console.error('Generate Story button (ID: generate-story-button) not found.');
    }

    // --- STORY BROWSING ---
    async function loadAndDisplayUserStories() {
        if (!userStoriesList) {
            console.error("[loadAndDisplayUserStories] userStoriesList element not found.");
            displayMessage("Cannot display stories area.", "error");
            return;
        }
        userStoriesList.innerHTML = ''; // Clear previous list
        showSpinner();
        displayMessage("Loading your stories...", "info");

        try {
            // Backend now returns drafts by default, and they are ordered by created_at desc.
            // The 'include_drafts=true' is the default on backend, so no query param needed here for that.
            const stories = await apiRequest('/stories/');
            if (stories && stories.length > 0) {
                const ul = document.createElement('ul');
                ul.classList.add('stories-list');
                stories.forEach(story => {
                    const li = document.createElement('li');
                    li.classList.add('story-item');
                    if (story.is_draft) {
                        li.classList.add('story-item-draft');
                    }

                    const titleDiv = document.createElement('div');
                    titleDiv.classList.add('story-item-title');
                    titleDiv.textContent = story.title || "Untitled Story";
                    if (story.is_draft) {
                        const draftLabel = document.createElement('span');
                        draftLabel.textContent = ' (Draft)';
                        draftLabel.classList.add('draft-label');
                        titleDiv.appendChild(draftLabel);
                    }

                    const dateDiv = document.createElement('div');
                    dateDiv.classList.add('story-item-date');
                    // Display generated_at if it's not a draft and available, otherwise created_at
                    let dateToDisplay = story.created_at;
                    let dateLabel = "Created:";
                    if (!story.is_draft && story.generated_at) {
                        dateToDisplay = story.generated_at;
                        dateLabel = "Generated:";
                    } else if (story.is_draft && story.updated_at) { // Assuming updated_at might be available for drafts
                        dateToDisplay = story.updated_at;
                        dateLabel = "Last Saved:";
                    } else {
                        dateToDisplay = story.created_at;
                        dateLabel = "Created:";
                    }
                    dateDiv.textContent = `${dateLabel} ${formatDate(dateToDisplay)}`;

                    const buttonsDiv = document.createElement('div');
                    buttonsDiv.classList.add('story-item-buttons');

                    if (story.is_draft) {
                        const editDraftButton = document.createElement('button');
                        editDraftButton.textContent = "Edit Draft";
                        editDraftButton.classList.add('button-small', 'button-primary');
                        editDraftButton.addEventListener('click', () => {
                            // Populate form with draft data for editing
                            populateCreateFormWithStoryData(story, true); // true for isEditingDraft
                            showSection(storyCreationSection);
                        });
                        buttonsDiv.appendChild(editDraftButton);
                    } else {
                        const viewButton = document.createElement('button');
                        viewButton.textContent = "View Story";
                        viewButton.classList.add('button-small');
                        viewButton.addEventListener('click', async () => {
                            displayMessage(`Loading story '${story.title}'...`, "info");
                            showSpinner();
                            try {
                                const fullStory = await apiRequest(`/stories/${story.id}`);
                                if (fullStory) {
                                    showSection(storyPreviewSection);
                                    displayStory(fullStory);
                                    displayMessage("Story loaded.", "success");
                                } else {
                                    displayMessage("Could not load story details.", "error");
                                }
                            } catch (err) {
                                console.error("[ViewStoryClick] Error loading story details:", err);
                                // displayMessage is handled by apiRequest
                            } finally {
                                hideSpinner();
                            }
                        });
                        buttonsDiv.appendChild(viewButton);
                    }

                    const useAsTemplateButton = document.createElement('button');
                    useAsTemplateButton.textContent = "Use as Template";
                    useAsTemplateButton.classList.add('button-small', 'button-secondary');
                    useAsTemplateButton.style.marginLeft = '10px';
                    useAsTemplateButton.addEventListener('click', async () => {
                        // Fetch full story details before populating, as list might be partial
                        displayMessage(`Loading template from '${story.title}'...`, "info");
                        showSpinner();
                        try {
                            const fullStoryForTemplate = await apiRequest(`/stories/${story.id}`);
                            if (fullStoryForTemplate) {
                                populateCreateFormWithStoryData(fullStoryForTemplate, false); // false for isEditingDraft
                                showSection(storyCreationSection);
                                displayMessage(`Form populated with template from "${fullStoryForTemplate.title}". Remember to give your new story a unique title.`, 'success');
                            } else {
                                displayMessage("Could not load story details for template.", "error");
                            }
                        } catch (err) {
                            console.error("[UseAsTemplateClick] Error loading story for template:", err);
                        } finally {
                            hideSpinner();
                        }
                    });
                    buttonsDiv.appendChild(useAsTemplateButton);

                    li.appendChild(titleDiv);
                    li.appendChild(dateDiv);
                    li.appendChild(buttonsDiv); // Add buttons container
                    ul.appendChild(li);
                });
                userStoriesList.appendChild(ul);
                displayMessage(stories.length > 0 ? "Stories loaded." : "No stories found.", stories.length > 0 ? "success" : "info");
            } else {
                userStoriesList.innerHTML = '<p>You haven\'t created any stories yet.</p>';
                displayMessage("No stories found.", "info");
            }
        } catch (error) {
            console.error("[loadAndDisplayUserStories] Error fetching stories:", error);
            // displayMessage already handled by apiRequest usually
            if (!messageArea.textContent.includes('Failed') && !messageArea.textContent.includes('error')) {
                displayMessage(`Failed to load stories: ${error.message}`, "error");
            }
            userStoriesList.innerHTML = '<p>Could not load stories. Please try again later.</p>';
        } finally {
            hideSpinner();
        }
    }

    // --- PDF EXPORT ---
    if (exportPdfButton) {
        exportPdfButton.addEventListener('click', async () => {
            if (!currentStoryId) {
                displayMessage('No story selected or story ID is missing. Cannot export PDF.', 'error');
                return;
            }

            displayMessage('Exporting PDF... Please wait.', 'info');
            showSpinner();

            try {
                const token = localStorage.getItem('authToken');
                const response = await fetch(`${API_BASE_URL}/stories/${currentStoryId}/pdf`, { // Changed endpoint to /pdf
                    method: 'GET',
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                });

                if (!response.ok) {
                    let errorDetail = "Unknown error";
                    try {
                        const errorData = await response.json();
                        errorDetail = errorData.detail || JSON.stringify(errorData);
                    } catch (e) {
                        errorDetail = await response.text();
                    }
                    throw new Error(`PDF export failed: ${response.status} ${response.statusText}. Detail: ${errorDetail}`);
                }

                const blob = await response.blob();
                const contentDisposition = response.headers.get('content-disposition');
                let filename = 'story.pdf'; // Default filename
                if (contentDisposition) {
                    const filenameMatch = contentDisposition.match(/filename="?(.+)"?/i);
                    if (filenameMatch && filenameMatch.length > 1) {
                        filename = filenameMatch[1];
                    }
                }

                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = url;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);

                displayMessage('PDF exported successfully!', 'success');

            } catch (error) {
                console.error('[PDFExport] Error exporting PDF:', error);
                displayMessage(`Error exporting PDF: ${error.message}`, 'error');
            } finally {
                hideSpinner();
            }
        });
    } else {
        console.error("Export PDF button not found during event listener setup.");
    }

    // --- HELPER FUNCTION TO POPULATE CREATE FORM ---
    function populateCreateFormWithStoryData(storyData, isEditingDraft = false) { // Added isEditingDraft
        console.log("[populateCreateFormWithStoryData] Populating form. isEditingDraft:", isEditingDraft, "Story:", storyData);

        // Call the global reset function first to clear the form and basic state
        resetFormAndState();
        // resetFormAndState will set currentStoryId = null and currentStoryIsDraft = false.
        // We need to override this if we are editing a draft or using a template.

        document.getElementById('story-title').value = storyData.title || '';
        document.getElementById('story-genre').value = storyData.genre || '';
        document.getElementById('story-outline').value = storyData.story_outline || '';
        document.getElementById('story-num-pages').value = storyData.num_pages || 5; // Default to 5 if not set
        document.getElementById('story-tone').value = storyData.tone || '';
        document.getElementById('story-setting').value = storyData.setting || '';
        document.getElementById('story-word-to-picture-ratio').value = storyData.word_to_picture_ratio || 'One image per page';
        document.getElementById('story-text-density').value = storyData.text_density || 'Concise (~30-50 words)';
        document.getElementById('story-image-style').value = storyData.image_style || 'Default';

        // Clear existing characters (resetFormAndState already does this, but good to be sure for characterCount)
        const fieldset = document.getElementById('main-characters-fieldset');
        const existingEntries = fieldset.querySelectorAll('.character-entry');
        existingEntries.forEach((entry, index) => {
            if (index > 0) entry.remove(); // Remove all but the first
        });
        characterCount = 0; // Will be incremented by addCharacterEntry

        if (storyData.main_characters && storyData.main_characters.length > 0) {
            storyData.main_characters.forEach((char, index) => {
                if (index > 0) { // If more than one character, add new entries
                    addCharacterEntry(); // This increments characterCount
                } else {
                    characterCount = 1; // Ensure first character is counted
                }
                // Populate the (newly added or existing first) character entry
                document.getElementById(`char-name-${characterCount}`).value = char.name || '';

                const ageEl = document.getElementById(`char-age-${characterCount}`);
                if (ageEl) ageEl.value = char.age || '';

                const genderEl = document.getElementById(`char-gender-${characterCount}`);
                if (genderEl) genderEl.value = char.gender || '';

                const physicalEl = document.getElementById(`char-physical-appearance-${characterCount}`);
                if (physicalEl) physicalEl.value = char.physical_appearance || '';

                const clothingEl = document.getElementById(`char-clothing-style-${characterCount}`);
                if (clothingEl) clothingEl.value = char.clothing_style || '';

                const traitsEl = document.getElementById(`char-key-traits-${characterCount}`);
                if (traitsEl) traitsEl.value = char.key_traits || '';

                // Ensure details are hidden initially for all populated characters
                const detailsDiv = document.getElementById(`char-details-${characterCount}`);
                const toggleButton = document.getElementById(`char-details-toggle-${characterCount}`);
                if (detailsDiv) detailsDiv.style.display = 'none';
                if (toggleButton) toggleButton.textContent = 'Show Details';
            });
        } else {
            // If no characters in storyData, ensure at least one blank character entry exists
            if (characterCount === 0) { // Should be 1 after reset, but as a safeguard
                addCharacterEntry(); // This sets characterCount to 1
            }
            // Ensure fields of the first character entry are blank (resetFormAndState should handle this)
        }

        if (isEditingDraft) {
            currentStoryId = storyData.id;
            currentStoryIsDraft = true;
            if (generateStoryButton) {
                generateStoryButton.textContent = 'Finalize & Generate Story';
            }
            displayMessage(`Editing draft: "${storyData.title || 'Untitled Draft'}". Make your changes and click "Save Draft" or "Finalize & Generate Story".`, 'info');
        } else { // Using as template
            currentStoryId = null; // New story, so no ID yet
            currentStoryIsDraft = false; // Not a draft being edited
            if (generateStoryButton) {
                generateStoryButton.textContent = 'Generate Story';
            }
            displayMessage(`Form populated with template from "${storyData.title || 'Untitled Story'}". Review and modify as needed. This will create a new story.`, 'info');
        }

        showSection(storyCreationSection); // Ensure the form is visible
        console.log("[populateCreateFormWithStoryData] Form population complete. currentStoryId:", currentStoryId, "currentStoryIsDraft:", currentStoryIsDraft);
    }

    // Removed the local resetFormAndState function from here.
});
