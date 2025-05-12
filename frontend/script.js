document.addEventListener('DOMContentLoaded', () => {
    const API_BASE_URL = 'http://localhost:8000'; // Assuming backend runs on port 8000
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

    // Content Areas
    const storyPreviewContent = document.getElementById('story-preview-content');
    const userStoriesList = document.getElementById('user-stories-list');

    let characterCount = 1;

    // --- UTILITY FUNCTIONS ---
    function formatDate(dateString) {
        if (!dateString) return 'N/A';
        const options = { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' };
        return new Date(dateString).toLocaleDateString(undefined, options);
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
        }
    }

    function displayMessage(message, isError = false) {
        messageArea.textContent = message;
        messageArea.style.color = isError ? '#FF6B6B' : '#6BFF6B'; // Brighter error/success colors for dark theme
        // Add background and border for visibility on dark theme
        if (isError) {
            messageArea.style.backgroundColor = 'rgba(255, 107, 107, 0.1)';
            messageArea.style.border = '1px solid rgba(255, 107, 107, 0.3)';
        } else {
            messageArea.style.backgroundColor = 'rgba(107, 255, 107, 0.1)';
            messageArea.style.border = '1px solid rgba(107, 255, 107, 0.3)';
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
    async function apiRequest(endpoint, method = 'GET', body = null, token = null) {
        const headers = {
            'Content-Type': 'application/json'
        };
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const config = {
            method: method,
            headers: headers
        };

        if (body && (method === 'POST' || method === 'PUT')) {
            config.body = JSON.stringify(body);
        }

        try {
            const response = await fetch(`${API_BASE_URL}${endpoint}`, config);
            if (!response.ok) {
                if (response.status === 401 && token) { // Check for 401 and if a token was used
                    authToken = null;
                    localStorage.removeItem('authToken');
                    updateNav(false); // This will show the auth section (login form)
                    // The error thrown here will be caught by the catch block below
                    // and its message will be displayed by displayMessage.
                    throw new Error('Your session has timed out. Please log in again.');
                }
                const errorData = await response.json().catch(() => ({ detail: response.statusText }));
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }
            if (response.status === 204) { // No Content
                return null;
            }
            // For PDF, response might not be JSON
            if (response.headers.get("content-type") && response.headers.get("content-type").includes("application/pdf")) {
                return response.blob();
            }
            return response.json();
        } catch (error) {
            console.error('API Request Error:', error);
            displayMessage(error.message || 'An unexpected error occurred.', true);
            throw error;
        }
    }

    // --- AUTHENTICATION --- 
    signupForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = signupForm.username.value;
        const email = signupForm.email.value; // Get email value
        const password = signupForm.password.value;
        try {
            await apiRequest('/users/', 'POST', { username, email, password }); // Add email to payload
            displayMessage('Signup successful! Please login.', false);
            signupForm.reset();
            // Switch to login form
            loginForm.style.display = 'block';
            signupForm.style.display = 'none';
        } catch (error) {
            // Error displayed by apiRequest
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
            // Login uses form data, not JSON
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
            displayMessage('Login successful!', false);
            updateNav(true);
            showSection(storyCreationSection); // Or browse stories
            loginForm.reset();
        } catch (error) {
            displayMessage(error.message || 'Login failed.', true);
        }
    });

    navLogout.addEventListener('click', () => {
        authToken = null;
        localStorage.removeItem('authToken');
        updateNav(false);
        displayMessage('Logged out.', false);
        currentStoryId = null;
        exportPdfButton.style.display = 'none';
    });

    // --- STORY CREATION ---
    addCharacterButton.addEventListener('click', () => {
        characterCount++;
        const fieldset = document.getElementById('main-characters-fieldset');
        const newEntry = document.createElement('div');
        newEntry.classList.add('character-entry');
        newEntry.innerHTML = `
            <hr>
            <label for="char-name-${characterCount}">Name:</label>
            <input type="text" id="char-name-${characterCount}" name="char_name_${characterCount}" class="char-name" required>
            <label for="char-desc-${characterCount}">Description:</label>
            <input type="text" id="char-desc-${characterCount}" name="char_desc_${characterCount}" class="char-desc" required>
            <label for="char-personality-${characterCount}">Personality (optional):</label>
            <input type="text" id="char-personality-${characterCount}" name="char_personality_${characterCount}" class="char-personality">
            <label for="char-background-${characterCount}">Background (optional):</label>
            <input type="text" id="char-background-${characterCount}" name="char_background_${characterCount}" class="char-background">
        `;
        fieldset.appendChild(newEntry);
    });

    storyCreationForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (!authToken) {
            displayMessage('Please login to create a story.', true);
            return;
        }

        const mainCharacters = [];
        const characterEntries = document.querySelectorAll('.character-entry');
        characterEntries.forEach((entry, index) => {
            const name = entry.querySelector(`.char-name`).value;
            const description = entry.querySelector(`.char-desc`).value;
            const personality = entry.querySelector(`.char-personality`).value;
            const background = entry.querySelector(`.char-background`).value;
            if (name && description) {
                mainCharacters.push({
                    name,
                    description,
                    personality: personality || null,
                    background: background || null
                });
            }
        });

        if (mainCharacters.length === 0) {
            displayMessage('Please add at least one character.', true);
            return;
        }

        const storyData = {
            genre: storyCreationForm.genre.value,
            story_outline: storyCreationForm.story_outline.value,
            main_characters: mainCharacters,
            num_pages: parseInt(storyCreationForm.num_pages.value),
            tone: storyCreationForm.tone.value || null,
            setting: storyCreationForm.setting.value || null,
        };

        displayMessage('Generating story... This may take a moment.', false);
        try {
            const generatedStory = await apiRequest('/stories/', 'POST', storyData, authToken);
            displayMessage('Story generated successfully!', false);
            renderStoryPreview(generatedStory);
            currentStoryId = generatedStory.id;
            exportPdfButton.style.display = 'block';
            showSection(storyPreviewSection);
            storyCreationForm.reset(); // This clears all form fields, including the first character's.

            // Remove dynamically added character entries, keeping the first one.
            const fieldset = document.getElementById('main-characters-fieldset');
            const characterEntries = fieldset.querySelectorAll('.character-entry');
            // Start from the second entry (index 1) and remove them.
            // Iterate backwards to avoid issues if characterEntries were a live list (though querySelectorAll returns a static one).
            for (let i = characterEntries.length - 1; i > 0; i--) {
                characterEntries[i].remove();
            }
            characterCount = 1; // Reset counter

        } catch (error) {
            // Error displayed by apiRequest or specific message if needed
            displayMessage(error.message || 'Failed to generate story.', true);
        }
    });

    function renderStoryPreview(story) {
        storyPreviewContent.innerHTML = ''; // Clear previous preview
        const titleElement = document.createElement('h3');
        titleElement.textContent = story.title;
        storyPreviewContent.appendChild(titleElement);

        story.pages.forEach(page => {
            const pageDiv = document.createElement('div');
            pageDiv.classList.add('story-page-preview');

            const pageNumElement = document.createElement('h4');
            pageNumElement.textContent = `Page ${page.page_number}`;
            pageDiv.appendChild(pageNumElement);

            const textElement = document.createElement('p');
            textElement.textContent = page.text;
            pageDiv.appendChild(textElement);

            if (page.image_path) {
                const imageElement = document.createElement('img');
                imageElement.src = `${API_BASE_URL}/static_content/${page.image_path.replace(/^data\//, '')}`;
                imageElement.alt = page.image_description || `Image for page ${page.page_number}`;
                imageElement.style.maxWidth = '300px'; // Simple styling
                pageDiv.appendChild(imageElement);
            } else {
                const noImageElement = document.createElement('p');
                noImageElement.textContent = '[No image generated for this page]';
                noImageElement.style.fontStyle = 'italic';
                pageDiv.appendChild(noImageElement);
            }
            storyPreviewContent.appendChild(pageDiv);
            storyPreviewContent.appendChild(document.createElement('hr'));
        });
    }

    // --- PDF EXPORT ---
    exportPdfButton.addEventListener('click', async () => {
        if (!authToken || !currentStoryId) {
            displayMessage('No story selected or not logged in.', true);
            return;
        }
        displayMessage('Generating PDF...', false);
        try {
            const pdfBlob = await apiRequest(`/stories/${currentStoryId}/pdf`, 'GET', null, authToken);
            const url = window.URL.createObjectURL(pdfBlob);
            const a = document.createElement('a');
            a.href = url;
            const storyTitle = storyPreviewContent.querySelector('h3')?.textContent || 'story';
            const safeTitle = storyTitle.replace(/[^a-z0-9_\-]/gi, '_').toLowerCase();
            a.download = `${safeTitle}_${currentStoryId}.pdf`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);
            displayMessage('PDF downloaded.', false);
        } catch (error) {
            displayMessage(error.message || 'Failed to download PDF.', true);
        }
    });

    // --- NAVIGATION HANDLERS ---
    navLoginSignup.addEventListener('click', () => {
        showSection(authSection);
        // Ensure login form is visible and signup is hidden when navigating to auth section
        loginForm.style.display = 'block';
        signupForm.style.display = 'none';
    });
    navCreateStory.addEventListener('click', () => showSection(storyCreationSection));
    navBrowseStories.addEventListener('click', () => {
        showSection(browseStoriesSection);
        fetchAndDisplayUserStories();
    });

    // --- STORY BROWSING ---
    async function fetchAndDisplayUserStories() {
        if (!authToken) {
            displayMessage('Please login to view your stories.', true);
            userStoriesList.innerHTML = '<p>Please login to view your stories.</p>';
            return;
        }

        displayMessage('Loading your stories...', false);
        userStoriesList.innerHTML = '<p>Loading...</p>'; // Placeholder while fetching

        try {
            const stories = await apiRequest('/stories/', 'GET', null, authToken);
            if (stories && stories.length > 0) {
                userStoriesList.innerHTML = ''; // Clear loading message
                const ul = document.createElement('ul');
                ul.className = 'story-items-list'; // Added class for styling
                stories.forEach(story => {
                    const li = document.createElement('li');
                    li.className = 'story-item'; // Added class for styling
                    li.setAttribute('data-story-id', story.id);

                    const titleElement = document.createElement('h3');
                    titleElement.textContent = story.title || 'Untitled Story';

                    const dateElement = document.createElement('p');
                    dateElement.className = 'story-date';
                    dateElement.textContent = `Created: ${formatDate(story.created_at)}`;

                    // Add a snippet of the first page if available
                    const snippetElement = document.createElement('p');
                    snippetElement.className = 'story-snippet';
                    if (story.pages && story.pages.length > 0 && story.pages[0].text) {
                        snippetElement.textContent = story.pages[0].text.substring(0, 100) + (story.pages[0].text.length > 100 ? '...' : '');
                    } else {
                        snippetElement.textContent = 'No content preview available.';
                    }

                    li.appendChild(titleElement);
                    li.appendChild(dateElement);
                    li.appendChild(snippetElement);

                    li.addEventListener('click', () => {
                        currentStoryId = story.id;
                        renderStoryPreview(story); // story object from /stories/ includes pages
                        showSection(storyPreviewSection);
                        exportPdfButton.style.display = 'block'; // Show PDF button, though functionality is limited
                    });
                    ul.appendChild(li);
                });
                userStoriesList.appendChild(ul);
                displayMessage('Stories loaded.', false);
            } else {
                userStoriesList.innerHTML = '<p>You haven\'t created any stories yet.</p>';
                displayMessage('No stories found.', false);
            }
        } catch (error) {
            userStoriesList.innerHTML = '<p>Could not load stories. Please try again later.</p>';
            // Error is displayed by apiRequest, but we can add a specific one if needed
            displayMessage(error.message || 'Failed to load stories.', true);
        }
    }

    // --- AUTH FORM TOGGLING ---
    if (showSignupLink) {
        showSignupLink.addEventListener('click', (e) => {
            e.preventDefault();
            loginForm.style.display = 'none';
            signupForm.style.display = 'block';
            const authSectionHeading = authSection.querySelector('h2');
            if (authSectionHeading) {
                authSectionHeading.textContent = 'Sign Up';
            }
            displayMessage(''); // Clear any previous messages
        });
    }

    if (showLoginLink) {
        showLoginLink.addEventListener('click', (e) => {
            e.preventDefault();
            signupForm.style.display = 'none';
            loginForm.style.display = 'block';
            const authSectionHeading = authSection.querySelector('h2');
            if (authSectionHeading) {
                authSectionHeading.textContent = 'Login';
            }
            displayMessage(''); // Clear any previous messages
        });
    }

    // --- INITIALIZATION ---
    const storedToken = localStorage.getItem('authToken');
    if (storedToken) {
        authToken = storedToken;
        updateNav(true);
        showSection(storyCreationSection); // Default to create story if logged in
    } else {
        updateNav(false);
    }
});
