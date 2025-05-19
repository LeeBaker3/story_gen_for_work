console.log("script.js file loaded and parsed by the browser.");

document.addEventListener('DOMContentLoaded', () => {
    console.log("DOMContentLoaded event fired. Initializing script...");
    const API_BASE_URL = window.location.origin; // Updated to use window.location.origin
    // TODO: Consider if API_BASE_URL should be configurable
    let authToken = null;
    let currentStoryId = null;

    // Navigation Elements
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
    console.log("Attempting to find 'add-character-button':", addCharacterButton); // Log the button element itself

    // Content Areas
    const storyPreviewContent = document.getElementById('story-preview-content');
    const userStoriesList = document.getElementById('user-stories-list');

    let characterCount = 1;

    // Spinner Elements
    const loadingSpinner = document.getElementById('loading-spinner');

    function showSpinner() {
        if (loadingSpinner) {
            loadingSpinner.style.display = 'block';
        }
    }

    function hideSpinner() {
        if (loadingSpinner) {
            loadingSpinner.style.display = 'none';
        }
    }

    // Function to initialize a character details toggle
    function initializeCharacterDetailsToggle(toggleButton) {
        toggleButton.addEventListener('click', () => {
            const targetId = toggleButton.dataset.target;
            const targetContent = document.getElementById(targetId);
            if (targetContent) {
                const isHidden = targetContent.style.display === 'none';
                targetContent.style.display = isHidden ? 'block' : 'none';
                toggleButton.textContent = isHidden ? 'Hide Details' : 'Show Details';
            }
        });
    }

    // Initialize toggle for the first character
    const firstCharToggle = document.querySelector('.character-details-toggle');
    if (firstCharToggle) {
        initializeCharacterDetailsToggle(firstCharToggle);
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
            <div>
                <label for="char-name-${characterCount}">Name:</label>
                <input type="text" id="char-name-${characterCount}" name="char_name_${characterCount}" class="char-name" required>
            </div>
            <button type="button" class="character-details-toggle" data-target="char-details-${characterCount}">Show Details</button>
            <div id="char-details-${characterCount}" class="character-details-content" style="display:none;">
                <div>
                    <label for="char-age-${characterCount}">Age (optional):</label>
                    <input type="number" id="char-age-${characterCount}" name="char_age_${characterCount}" class="char-age" placeholder="e.g., 30">
                </div>
                <div>
                    <label for="char-gender-${characterCount}">Gender (optional):</label>
                    <input type="text" id="char-gender-${characterCount}" name="char_gender_${characterCount}" class="char-gender" placeholder="e.g., female, male, non-binary">
                </div>
                <div>
                    <label for="char-physical-appearance-${characterCount}">Physical Appearance (optional):</label>
                    <textarea id="char-physical-appearance-${characterCount}" name="char_physical_appearance_${characterCount}" class="char-physical-appearance" rows="3" placeholder="e.g., tall, brown hair, blue eyes, athletic build"></textarea>
                </div>
                <div>
                    <label for="char-clothing-style-${characterCount}">Clothing Style (optional):</label>
                    <input type="text" id="char-clothing-style-${characterCount}" name="char_clothing_style_${characterCount}" class="char-clothing-style" placeholder="e.g., casual, formal, bohemian">
                </div>
                <div>
                    <label for="char-key-traits-${characterCount}">Key Personality Traits (optional):</label>
                    <textarea id="char-key-traits-${characterCount}" name="char_key_traits_${characterCount}" class="char-key-traits" rows="3" placeholder="e.g., brave, curious, kind"></textarea>
                </div>
            </div>
        `;
        // Corrected line: Append the new character entry directly to the fieldset
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
        const options = { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' };
        return new Date(dateString).toLocaleDateString(undefined, options);
    }

    // Function to render the story preview
    function renderStoryPreview(story) {
        if (!storyPreviewContent || !story) {
            console.error('[renderStoryPreview] Story preview content area or story data is missing.');
            displayMessage('Could not display story preview.', 'error');
            if (exportPdfButton) exportPdfButton.style.display = 'none';
            return;
        }

        console.log('[renderStoryPreview] Story object received:', JSON.parse(JSON.stringify(story)));
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
            console.log('[renderStoryPreview] story.pages.length:', story.pages.length);

            // Sort pages to ensure title page (page_number 0) is first, then others by page_number
            const sortedPages = story.pages.sort((a, b) => {
                // Ensure page_number is treated as a number for sorting, even if it's a string like "0" or "Title" (which becomes 0)
                const pageNumA = parseInt(a.page_number, 10);
                const pageNumB = parseInt(b.page_number, 10);
                return pageNumA - pageNumB;
            });

            sortedPages.forEach((page, index) => {
                console.log(`[renderStoryPreview] Processing page data (Page Number: ${page.page_number}):`, JSON.parse(JSON.stringify(page)));

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
            console.log('[renderStoryPreview] Condition (story.pages && story.pages.length > 0):', shouldShowButton);
            exportPdfButton.style.display = shouldShowButton ? 'block' : 'none';
            console.log('[renderStoryPreview] exportPdfButton display set to:', exportPdfButton.style.display);
        } else {
            console.error('[renderStoryPreview] exportPdfButton element is NULL or undefined!');
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
            // renderStoryPreview will manage its visibility based on actual content.
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
    async function apiRequest(endpoint, method = 'GET', body = null, isFormDataType = false) {
        console.log(`[apiRequest] Called with endpoint: "${endpoint}", method: "${method}", isFormDataType (parameter value): ${isFormDataType}`);

        const token = localStorage.getItem('authToken'); // Changed 'jwtToken' to 'authToken'
        console.log('[apiRequest] Token from localStorage (inside apiRequest):', token);

        const headers = {};

        if (isFormDataType) {
            console.log('[apiRequest] FormData request, Content-Type will be set by browser.');
        } else {
            headers['Content-Type'] = 'application/json';
        }

        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        } else {
            console.log('[apiRequest] No token found (inside apiRequest), Authorization header not set.');
        }

        const options = {
            method,
            headers,
        };

        if (body && method !== 'GET' && method !== 'HEAD') {
            options.body = isFormDataType ? body : JSON.stringify(body);
        }

        const urlToFetch = `${API_BASE_URL}${endpoint}`;

        console.log('[apiRequest] Attempting to fetch URL:', urlToFetch);
        console.log('[apiRequest] Options being sent (stringified for brevity, headers may differ for FormData):', JSON.stringify({ ...options, body: body ? (isFormDataType ? '[FormData]' : typeof options.body) : undefined }, null, 2));

        try {
            const response = await fetch(urlToFetch, options);

            console.log(`[apiRequest] Response for ${method} ${urlToFetch}: Status ${response.status} ${response.statusText}`);

            if (!response.ok) {
                let errorBodyText = "[Could not read response text]";
                try {
                    errorBodyText = await response.text();
                    console.error(`[apiRequest] Error response body for ${urlToFetch} (text):`, errorBodyText);
                } catch (textError) {
                    console.error(`[apiRequest] Failed to read error response text for ${urlToFetch}:`, textError);
                }

                let errorData;
                try {
                    errorData = JSON.parse(errorBodyText);
                } catch (e) {
                    errorData = { message: "Failed to parse error response as JSON.", raw_body: errorBodyText };
                }

                const error = new Error(`HTTP error! Status: ${response.status} (${response.statusText}) for ${method} ${urlToFetch}. Body: ${errorBodyText.substring(0, 100)}...`);
                error.response = response;
                error.status = response.status;
                error.data = errorData;

                console.error('[apiRequest] Constructed error object:', error);

                let displayErrorMessage = `Server error: ${response.status} (${response.statusText}) when calling ${method} ${endpoint}. `;
                if (errorData && errorData.detail) {
                    if (typeof errorData.detail === 'string') {
                        displayErrorMessage += errorData.detail;
                    } else if (Array.isArray(errorData.detail) && errorData.detail.length > 0 && errorData.detail[0].msg) {
                        displayErrorMessage += errorData.detail.map(d => `${d.loc.join('->')}: ${d.msg}`).join('; ');
                    } else {
                        displayErrorMessage += JSON.stringify(errorData.detail);
                    }
                } else if (errorData && errorData.message && errorData.message !== "Failed to parse error response as JSON.") {
                    displayErrorMessage += errorData.message;
                } else if (errorBodyText !== "[Could not read response text]" && errorBodyText.trim() !== "") {
                    const previewText = errorBodyText.length > 150 ? errorBodyText.substring(0, 150) + "..." : errorBodyText;
                    displayErrorMessage += "Details: " + previewText;
                }

                displayMessage(displayErrorMessage, 'error');
                throw error;
            }

            if (response.status === 204) {
                console.log(`[apiRequest] Received 204 No Content for ${urlToFetch}`);
                return null;
            }

            const contentType = response.headers.get("content-type");
            if (contentType && contentType.indexOf("application/json") !== -1) {
                return await response.json();
            } else {
                return await response.text();
            }

        } catch (error) {
            console.error(`[apiRequest] Catch block triggered for ${method} ${urlToFetch}. Error message: ${error.message}`, error);

            if (!error.response) {
                let finalErrorMessage = `API Request Failed for ${method} ${endpoint}. `;
                if (error.message) {
                    finalErrorMessage += error.message;
                } else {
                    finalErrorMessage += "An unknown network error occurred."
                }
                displayMessage(finalErrorMessage, 'error');
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
            // Optionally, clear the form or reset story ID if needed
            // storyCreationForm.reset(); 
            // currentStoryId = null;
            // exportPdfButton.style.display = 'none';
        });
    }

    if (navBrowseStories) {
        navBrowseStories.addEventListener('click', async () => {
            showSection(browseStoriesSection);
            await loadAndDisplayUserStories(); // Function to fetch and render stories
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

    // --- STORY CREATION ---
    storyCreationForm.addEventListener('submit', async function (event) {
        event.preventDefault();
        displayMessage('Generating story... This may take a moment.', 'info');
        showSpinner();

        const mainCharacters = [];
        for (let i = 1; i <= characterCount; i++) {
            const name = document.getElementById(`char-name-${i}`)?.value;
            if (name) {
                mainCharacters.push({
                    name: name,
                    age: document.getElementById(`char-age-${i}`)?.value || null,
                    gender: document.getElementById(`char-gender-${i}`)?.value || null,
                    physical_appearance: document.getElementById(`char-physical-appearance-${i}`)?.value || null,
                    clothing_style: document.getElementById(`char-clothing-style-${i}`)?.value || null,
                    key_traits: document.getElementById(`char-key-traits-${i}`)?.value || null,
                });
            }
        }

        const storyData = {
            title: document.getElementById('story-title').value, // Added this line
            genre: document.getElementById('story-genre').value,
            story_outline: document.getElementById('story-outline').value,
            main_characters: mainCharacters,
            num_pages: parseInt(document.getElementById('story-num-pages').value, 10),
            tone: document.getElementById('story-tone').value,
            setting: document.getElementById('story-setting').value,
            word_to_picture_ratio: document.getElementById('story-word-to-picture-ratio').value,
            text_density: document.getElementById('story-text-density').value,
            image_style: document.getElementById('story-image-style').value
        };

        console.log('[FormSubmit] storyData before API call (raw object):', storyData);
        const tokenForStoryCreation = localStorage.getItem('authToken');
        if (!tokenForStoryCreation) {
            displayMessage('Authentication token is missing. Please log in again.', 'error');
            hideSpinner();
            return;
        }

        try {
            const createdStory = await apiRequest('/stories/', 'POST', storyData, false);

            if (createdStory && createdStory.id && createdStory.title && createdStory.pages) {
                currentStoryId = createdStory.id;

                showSection(storyPreviewSection); // CALL FIRST: Make the section visible (this will hide PDF button by default)
                renderStoryPreview(createdStory); // CALL SECOND: Render content (this will show PDF button if pages exist)
                displayMessage(`Story "${createdStory.title}" created and loaded successfully!`, 'success');

            } else {
                let errorMessage = 'Story creation completed, but the response was not in the expected format.';
                if (createdStory && createdStory.title) {
                    errorMessage = `Story "${createdStory.title}" created, but failed to load full details for preview. You may find it in 'Browse Stories'.`;
                } else if (createdStory && createdStory.id) {
                    errorMessage = `Story (ID: ${createdStory.id}) created, but failed to load full details for preview. You may find it in 'Browse Stories'.`;
                }
                console.warn('[FormSubmit] Story creation response issue:', createdStory);
                displayMessage(errorMessage, 'warning');
            }
        } catch (error) {
            console.error('[FormSubmit] Error during story creation:', error);
            if (!messageArea.textContent.includes('Failed') && !messageArea.textContent.includes('error')) {
                const errMessage = error && error.message ? String(error.message) : 'An unexpected error occurred during story creation.';
                displayMessage(`Story creation failed: ${errMessage}`, 'error');
            }
        } finally {
            hideSpinner();
        }
    });

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
            const stories = await apiRequest('/stories/'); // GET request
            if (stories && stories.length > 0) {
                const ul = document.createElement('ul');
                ul.classList.add('stories-list');
                stories.forEach(story => {
                    const li = document.createElement('li');
                    li.classList.add('story-item');

                    const titleDiv = document.createElement('div');
                    titleDiv.classList.add('story-item-title');
                    titleDiv.textContent = story.title || "Untitled Story";

                    const dateDiv = document.createElement('div');
                    dateDiv.classList.add('story-item-date');
                    dateDiv.textContent = `Created: ${formatDate(story.created_at)}`;

                    const viewButton = document.createElement('button');
                    viewButton.textContent = "View Story";
                    viewButton.classList.add('button-small');
                    viewButton.addEventListener('click', async () => {
                        displayMessage(`Loading story '${story.title}'...`, "info");
                        showSpinner();
                        try {
                            // We need to fetch the full story details again, as /stories/ might return a summary
                            const fullStory = await apiRequest(`/stories/${story.id}`);
                            if (fullStory) {
                                currentStoryId = fullStory.id;
                                showSection(storyPreviewSection);
                                renderStoryPreview(fullStory);
                                displayMessage(`Story '${fullStory.title}' loaded.`, "success");
                            } else {
                                displayMessage(`Could not load details for story '${story.title}'.`, "error");
                            }
                        } catch (err) {
                            displayMessage(`Error loading story: ${err.message}`, "error");
                        } finally {
                            hideSpinner();
                        }
                    });

                    li.appendChild(titleDiv);
                    li.appendChild(dateDiv);
                    li.appendChild(viewButton);
                    ul.appendChild(li);
                });
                userStoriesList.appendChild(ul);
                displayMessage("Stories loaded.", "success");
            } else {
                userStoriesList.innerHTML = '<p>You haven\'t created any stories yet.</p>';
                displayMessage("No stories found.", "info");
            }
        } catch (error) {
            console.error("[loadAndDisplayUserStories] Error fetching stories:", error);
            displayMessage(`Failed to load stories: ${error.message}`, "error");
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

});
