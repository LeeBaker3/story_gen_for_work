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
                displayMessage('Could not load story genres.', true);
            }
        } catch (error) {
            displayMessage('Failed to load story genres. Please try refreshing.', true);
            // Keep existing or default options in the dropdown as a fallback
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
        fieldset.appendChild(newEntry);
        // Initialize toggle for the new character entry
        const newToggle = newEntry.querySelector('.character-details-toggle');
        if (newToggle) {
            initializeCharacterDetailsToggle(newToggle);
        }
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
            // New detailed fields
            const ageInput = entry.querySelector(`.char-age`);
            const age = ageInput && ageInput.value ? parseInt(ageInput.value) : null;
            const genderInput = entry.querySelector(`.char-gender`);
            const gender = genderInput ? genderInput.value : null;
            const physicalAppearanceInput = entry.querySelector(`.char-physical-appearance`);
            const physical_appearance = physicalAppearanceInput ? physicalAppearanceInput.value : null;
            const clothingStyleInput = entry.querySelector(`.char-clothing-style`);
            const clothing_style = clothingStyleInput ? clothingStyleInput.value : null;
            const keyTraitsInput = entry.querySelector(`.char-key-traits`);
            const key_traits = keyTraitsInput ? keyTraitsInput.value : null;

            if (name) { // Only name is strictly required on the frontend for a character entry
                mainCharacters.push({
                    name,
                    age,
                    gender: gender || null,
                    physical_appearance: physical_appearance || null,
                    clothing_style: clothing_style || null,
                    key_traits: key_traits || null
                });
            }
        });

        if (mainCharacters.length === 0) {
            displayMessage('Please add at least one character with a name.', true);
            return;
        }

        const storyData = {
            genre: storyCreationForm.genre.value,
            story_outline: storyCreationForm.story_outline.value,
            main_characters: mainCharacters,
            num_pages: parseInt(storyCreationForm.num_pages.value),
            tone: storyCreationForm.tone.value || null,
            setting: storyCreationForm.setting.value || null,
            image_style: storyCreationForm.image_style.value, // Existing field
            word_to_picture_ratio: storyCreationForm.word_to_picture_ratio.value, // FR13: Added word_to_picture_ratio
            text_density: storyCreationForm.text_density.value // New Req: Added text_density
        };

        displayMessage('Generating story... This may take a moment.', false);
        try {
            const generatedStory = await apiRequest('/stories/', 'POST', storyData, authToken);
            displayMessage('Story generated successfully!', false);
            renderStoryPreview(generatedStory);
            currentStoryId = generatedStory.id;
            exportPdfButton.style.display = 'block';
            showSection(storyPreviewSection);

            // Reset form fields, including dynamic character entries and their details
            storyCreationForm.reset();

            const fieldset = document.getElementById('main-characters-fieldset');
            const allCharacterEntries = fieldset.querySelectorAll('.character-entry');

            // Remove dynamically added character entries (all except the first one)
            for (let i = allCharacterEntries.length - 1; i > 0; i--) {
                allCharacterEntries[i].remove();
            }
            characterCount = 1; // Reset counter

            // Reset the first character's details section
            const firstCharDetails = document.getElementById('char-details-1');
            const firstCharToggleButton = document.querySelector('.character-details-toggle[data-target="char-details-1"]');
            if (firstCharDetails) {
                firstCharDetails.style.display = 'none'; // Hide details
            }
            if (firstCharToggleButton) {
                firstCharToggleButton.textContent = 'Show Details'; // Reset button text
            }

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
    populateGenreDropdown(); // Populate genres on page load
});
