let API_BASE_URL;
if (
    window.location.hostname === "localhost" ||
    window.location.hostname === "127.0.0.1"
) {
    API_BASE_URL = "http://127.0.0.1:8000"; // Local development
} else {
    API_BASE_URL = "https://story-gen-for-work.onrender.com"; // Deployed environment
}
console.log("script.js file loaded and parsed by the browser.");

document.addEventListener("DOMContentLoaded", function () {
    // console.log('<<<<< SCRIPT_JS_VERSION_DEBUG_A - DOMContentLoaded >>>>>');
    // Variable declarations
    const navLoginSignup = document.getElementById("nav-login-signup");
    const navCreateStory = document.getElementById("nav-create-story");
    const navBrowseStories = document.getElementById("nav-browse-stories");
    const navLogout = document.getElementById("nav-logout");
    const navAdminPanel = document.getElementById("nav-admin-panel");

    // Sections
    const authSection = document.getElementById("auth-section");
    const storyCreationSection = document.getElementById(
        "story-creation-section",
    );
    const storyPreviewSection = document.getElementById("story-preview-section");
    const browseStoriesSection = document.getElementById(
        "browse-stories-section",
    );
    const adminPanelContainer = document.getElementById("adminPanelContainer"); // ENSURED DECLARATION
    const messageArea = document.getElementById("api-message");

    // Forms
    const loginForm = document.getElementById("login-form");
    const signupForm = document.getElementById("signup-form");
    const storyCreationForm = document.getElementById("story-creation-form");

    // Auth view toggle links
    const showSignupLink = document.getElementById("show-signup-link");
    const showLoginLink = document.getElementById("show-login-link");

    // Buttons
    const addCharacterButton = document.getElementById("add-character-button");
    const exportPdfButton = document.getElementById("export-pdf-button");
    const generateStoryButton = document.getElementById("generate-story-button");
    const saveDraftButton = document.getElementById("save-draft-button");

    let authToken = localStorage.getItem("authToken");

    // State variables for draft editing
    let currentStoryId = null;
    let currentStoryIsDraft = false;

    // Content Areas
    const storyPreviewContent = document.getElementById("story-preview-content");
    const userStoriesList = document.getElementById("user-stories-list");

    // Admin panel specific elements
    const adminUserTableBody = document.getElementById("adminUserTableBody"); // ENSURED DECLARATION (MOVED HERE)

    let characterCount = 1;

    // Spinner Elements
    const spinner = document.getElementById("spinner");

    // --- DYNAMIC DROPDOWN POPULATION ---
    async function populateDropdown(selectElementId, listName) {
        const selectElement = document.getElementById(selectElementId);
        if (!selectElement) {
            console.error(
                `[populateDropdown] Select element with ID '${selectElementId}' not found.`,
            );
            return;
        }

        try {
            const response = await fetch(
                `${API_BASE_URL}/api/v1/dynamic-lists/${listName}/items`,
            );
            if (!response.ok) {
                throw new Error(
                    `Failed to fetch ${listName}: ${response.status} ${response.statusText}`,
                );
            }
            const items = await response.json();

            // Clear existing options (except for a potential placeholder)
            selectElement.innerHTML = '';

            // Add a default, disabled option
            const defaultOption = document.createElement("option");
            defaultOption.value = "";
            defaultOption.textContent = "Select...";
            defaultOption.disabled = true;
            defaultOption.selected = true;
            selectElement.appendChild(defaultOption);

            // Populate with fetched items
            items.forEach(item => {
                const option = document.createElement("option");
                option.value = item.item_value; // Corrected from item.value
                option.textContent = item.item_label; // Corrected from item.label
                selectElement.appendChild(option);
            });
        } catch (error) {
            console.error(`[populateDropdown] Error populating ${listName}:`, error);
            // Optionally, display an error message to the user in the dropdown
            selectElement.innerHTML = '<option value="">Error loading options</option>';
        }
    }

    function populateAllDropdowns() {
        console.log("[populateAllDropdowns] Starting to populate all dropdowns.");
        populateDropdown("story-genre", "story_genres");
        populateDropdown("story-image-style", "image_styles_app");
        populateDropdown(
            "story-word-to-picture-ratio",
            "word_to_picture_ratio",
        );
        populateDropdown("story-text-density", "text_density");
    }


    // --- RESET FUNCTION (MOVED HERE) ---
    function resetFormAndState() {
        console.log("[resetFormAndState] Attempting to reset form and state.");
        if (storyCreationForm) {
            storyCreationForm.reset();
            console.log("[resetFormAndState] storyCreationForm reset called.");
        } else {
            console.error("[resetFormAndState] storyCreationForm is null!");
        }

        // Clear existing dynamic characters (beyond the first one if it's static or part of the template)
        const characterEntries = document.querySelectorAll(
            "#main-characters-fieldset .character-entry",
        );
        console.log(
            `[resetFormAndState] Found ${characterEntries.length} character entries.`,
        );
        characterEntries.forEach((entry, index) => {
            if (index > 0) {
                // Keep the first entry (index 0)
                entry.remove();
                console.log(
                    `[resetFormAndState] Removed character entry ${index + 1}.`,
                );
            } else {
                // Reset fields of the first character entry
                const firstCharacterEntry = characterEntries[0]; // Get the first entry directly

                const nameInput = firstCharacterEntry.querySelector("#char-name-1");
                if (nameInput) nameInput.value = "";
                const ageInput = firstCharacterEntry.querySelector("#char-age-1");
                if (ageInput) ageInput.value = "";
                const genderInput = firstCharacterEntry.querySelector("#char-gender-1");
                if (genderInput) genderInput.value = "";
                const physicalTextarea = firstCharacterEntry.querySelector(
                    "#char-physical-appearance-1",
                );
                if (physicalTextarea) physicalTextarea.value = "";
                const clothingInput = firstCharacterEntry.querySelector(
                    "#char-clothing-style-1",
                );
                if (clothingInput) clothingInput.value = "";
                const traitsTextarea =
                    firstCharacterEntry.querySelector("#char-key-traits-1");
                if (traitsTextarea) traitsTextarea.value = "";

                // Use document.getElementById for elements known by unique ID for the first character
                const detailsDiv = document.getElementById("char-details-1");
                const toggleButton = document.getElementById("char-details-toggle-1");

                if (detailsDiv) {
                    detailsDiv.style.display = "none";
                } else {
                    console.warn(
                        "[resetFormAndState] First character details div (#char-details-1) not found using getElementById.",
                    );
                }
                if (toggleButton) {
                    toggleButton.textContent = "Show Details";
                } else {
                    console.warn(
                        "[resetFormAndState] First character toggle button (#char-details-toggle-1) not found using getElementById.",
                    );
                }
                console.log(
                    "[resetFormAndState] Reset fields and state for first character entry.",
                );
            }
        });
        characterCount = 1; // Reset character count
        console.log("[resetFormAndState] characterCount reset to 1.");

        // Reset draft-specific state
        currentStoryId = null;
        currentStoryIsDraft = false;
        console.log(
            "[resetFormAndState] currentStoryId and currentStoryIsDraft reset.",
        );

        if (generateStoryButton) {
            generateStoryButton.textContent = "Generate Story"; // Reset button text for new story
            console.log("[resetFormAndState] generateStoryButton text reset.");
        }

        // Explicitly clear the title field
        const storyTitleInput = document.getElementById("story-title");
        if (storyTitleInput) {
            storyTitleInput.value = "";
            console.log("[resetFormAndState] Story title input cleared.");
        }

        // Hide PDF button as no story is actively being previewed after a reset from creation
        if (exportPdfButton) {
            exportPdfButton.style.display = "none";
            console.log("[resetFormAndState] exportPdfButton hidden.");
        }

        showSection(storyCreationSection); // Ensure the creation form is visible
        displayMessage("Form cleared. Ready for a new story.", "info");
        console.log(
            "[resetFormAndState] Form fields and draft state reset. Navigated to story creation section.",
        );
    }

    // --- INITIALIZATION ---
    // initializeCharacterDetailsToggle(document.querySelector('.character-details-toggle')); // Moved to after first entry ensure
    updateNav(!!authToken);
    if (!!authToken) {
        if (window.location.hash === "#browse") {
            showSection(browseStoriesSection);
            loadAndDisplayUserStories();
        } else {
            showSection(storyCreationSection);
            populateAllDropdowns(); // Populate all dropdowns on load if logged in
        }
        // Add first character entry if not already present by HTML
        if (
            document.querySelectorAll("#main-characters-fieldset .character-entry")
                .length === 0
        ) {
            // addCharacterEntry(); // This was one place it was called, but addCharacterEntry itself is for *additional* characters.
            // The first character is expected to be in the HTML or handled by reset.
            // For now, let's assume resetFormAndState or initial HTML handles the first one.
        } else {
            // If the first character entry is already in HTML, ensure its state is correct (handled by event delegation now)
            // const firstCharToggle = document.querySelector('#main-characters-fieldset .character-entry .character-details-toggle');
            // if (firstCharToggle) {
            //     initializeCharacterDetailsToggle(firstCharToggle);
            // }
        }
    } else {
        showSection(authSection);
    }

    // --- UTILITY FUNCTIONS ---
    function showSpinner() {
        if (spinner) spinner.style.display = "block";
    }
    function hideSpinner() {
        if (spinner) spinner.style.display = "none";
    }
    // Function to add a new character entry to the form
    function addCharacterEntry() {
        console.log(
            "'Add Character' button clicked. addCharacterEntry function started.",
        );
        characterCount++;
        const fieldset = document.getElementById("main-characters-fieldset");
        if (!fieldset) {
            console.error(
                "CRITICAL ERROR: Main characters fieldset (id: main-characters-fieldset) not found! Cannot add new character entry.",
            );
            return;
        }
        console.log(
            "Main characters fieldset found. Proceeding to add new character entry.",
        );

        const newCharacterEntry = document.createElement("div");
        newCharacterEntry.classList.add("character-entry");
        newCharacterEntry.innerHTML = `
            <hr>
            <h4>Character ${characterCount} <button type="button" class="character-details-toggle" id="char-details-toggle-${characterCount}" data-target="char-details-${characterCount}">Show Details</button></h4>
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
    }

    // Event listener for the "Add Another Character" button
    if (addCharacterButton) {
        addCharacterButton.addEventListener("click", addCharacterEntry);
        console.log(
            "Event listener for 'Add Character' button (add-character-button) attached successfully.",
        );
    } else {
        console.error(
            "CRITICAL ERROR: 'Add Character' button (id: add-character-button) not found in the DOM. This feature will not work.",
        );
    }

    // --- UTILITY FUNCTIONS ---
    function formatDate(dateString) {
        if (!dateString) return "N/A";

        let processedDateString = dateString;
        // Check if the date string looks like an ISO string without timezone information
        // e.g., "2023-10-27T10:30:00" or "2023-10-27T10:30:00.123456"
        // If so, append 'Z' to treat it as UTC.
        // This regex checks for "T" and no "Z" at the end, and no explicit offset like +05:00 or -0800.
        if (
            processedDateString.includes("T") &&
            !processedDateString.endsWith("Z") &&
            !/[+-]\\d{2}:?\\d{2}$/.test(processedDateString)
        ) {
            processedDateString += "Z";
        }

        const date = new Date(processedDateString);

        // Check if the date is valid after processing
        if (isNaN(date.getTime())) {
            console.warn(
                `[formatDate] Could not parse date string: ${dateString} (processed as ${processedDateString}). Returning original.`,
            );
            return dateString; // Or 'Invalid Date' or 'N/A'
        }

        const options = {
            year: "numeric",
            month: "long",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
            // timeZoneName: 'short' // Optional: to show timezone like PST, EST if desired
        };
        return date.toLocaleString(undefined, options); // Using toLocaleString for date and time
    }

    // Function to render the story preview
    function displayStory(story) {
        if (!storyPreviewContent || !story) {
            console.error(
                "[displayStory] Story preview content area or story data is missing.",
            );
            displayMessage("Could not display story preview.", "error");
            if (exportPdfButton) exportPdfButton.style.display = "none";
            return;
        }

        console.log(
            "[displayStory] Story object received:",
            JSON.parse(JSON.stringify(story)),
        );
        currentStoryId = story.id; // Store current story ID for reuse

        storyPreviewContent.innerHTML = ""; // Clear previous content

        // --- Main Story Title with Edit Functionality ---
        const titleContainer = document.createElement("div");
        titleContainer.classList.add("story-main-title-container");

        const mainStoryTitleElement = document.createElement("h2");
        mainStoryTitleElement.textContent = story.title || "Untitled Story";
        mainStoryTitleElement.classList.add("story-main-title");
        mainStoryTitleElement.id = `story-title-text-${story.id}`; // ID for easy access
        mainStoryTitleElement.style.display = "inline"; // Ensure it's inline from the start

        const editTitleIcon = document.createElement("span");
        editTitleIcon.textContent = " ✏️"; // Pencil emoji for edit
        editTitleIcon.classList.add("edit-title-icon");
        editTitleIcon.style.cursor = "pointer";
        editTitleIcon.title = "Edit title";
        editTitleIcon.id = `edit-title-icon-${story.id}`;

        const titleEditForm = document.createElement("div");
        titleEditForm.classList.add("title-edit-form");
        titleEditForm.style.display = "none"; // Hidden by default
        titleEditForm.id = `title-edit-form-${story.id}`;

        const titleInput = document.createElement("input");
        titleInput.type = "text";
        titleInput.classList.add("title-edit-input");
        titleInput.value = story.title || "Untitled Story";

        const saveTitleButton = document.createElement("button");
        saveTitleButton.textContent = "Save";
        saveTitleButton.classList.add("save-title-button");

        const cancelTitleButton = document.createElement("button");
        cancelTitleButton.textContent = "Cancel";
        cancelTitleButton.classList.add("cancel-title-button");

        titleEditForm.appendChild(titleInput);
        titleEditForm.appendChild(saveTitleButton);
        titleEditForm.appendChild(cancelTitleButton);

        titleContainer.appendChild(mainStoryTitleElement);
        titleContainer.appendChild(editTitleIcon);
        titleContainer.appendChild(titleEditForm);
        storyPreviewContent.appendChild(titleContainer);

        editTitleIcon.addEventListener("click", () => {
            mainStoryTitleElement.style.display = "none";
            editTitleIcon.style.display = "none";
            titleEditForm.style.display = "inline-block"; // Or 'flex' if using flexbox for layout
            titleInput.value = mainStoryTitleElement.textContent; // Ensure current value
            titleInput.focus();
        });

        saveTitleButton.addEventListener("click", async () => {
            const newTitle = titleInput.value.trim();
            if (newTitle && newTitle !== mainStoryTitleElement.textContent) {
                await updateStoryTitle(
                    story.id,
                    newTitle,
                    mainStoryTitleElement,
                    editTitleIcon,
                    titleEditForm,
                );
            } else if (!newTitle) {
                displayMessage("Title cannot be empty.", "warning");
            } else {
                // No change
                mainStoryTitleElement.style.display = "inline";
                editTitleIcon.style.display = "inline";
                titleEditForm.style.display = "none";
            }
        });

        cancelTitleButton.addEventListener("click", () => {
            mainStoryTitleElement.style.display = "inline"; // Or 'block' or 'initial' based on original display
            editTitleIcon.style.display = "inline";
            titleEditForm.style.display = "none";
            // Optionally reset input value if needed: titleInput.value = mainStoryTitleElement.textContent;
        });
        // --- End Main Story Title with Edit Functionality ---

        if (story.pages && story.pages.length > 0) {
            console.log("[displayStory] story.pages.length:", story.pages.length);

            // Sort pages to ensure title page (page_number 0) is first, then others by page_number
            const sortedPages = story.pages.sort((a, b) => {
                // Ensure page_number is treated as a number for sorting, even if it's a string like "0" or "Title" (which becomes 0)
                const pageNumA = parseInt(a.page_number, 10);
                const pageNumB = parseInt(b.page_number, 10);
                return pageNumA - pageNumB;
            });

            sortedPages.forEach((page, index) => {
                console.log(
                    `[displayStory] Processing page data (Page Number: ${page.page_number}):`,
                    JSON.parse(JSON.stringify(page)),
                );

                const pageContainer = document.createElement("div");

                // Check if it's the title page (page_number 0)
                // The backend converts "Title" to 0, so we check for numeric 0.
                if (parseInt(page.page_number, 10) === 0) {
                    pageContainer.classList.add("story-title-page-preview");

                    // Title from page.text (should be the story title for page 0)
                    if (page.text) {
                        const titlePageTitleElement = document.createElement("h3"); // Title on the title page
                        titlePageTitleElement.classList.add("title-page-story-title");
                        titlePageTitleElement.textContent = page.text;
                        pageContainer.appendChild(titlePageTitleElement);
                    }

                    // Cover image for title page
                    if (page.image_path) {
                        const imageElement = document.createElement("img");
                        imageElement.classList.add("title-page-cover-image");
                        // Ensure the path is correctly formed for static content
                        if (page.image_path.startsWith("data/")) {
                            imageElement.src =
                                "/static_content/" + page.image_path.substring("data/".length);
                        } else if (page.image_path.startsWith("/static_content/")) {
                            imageElement.src = page.image_path; // Already correctly prefixed
                        } else {
                            // Assuming it might be a relative path that needs the prefix
                            imageElement.src = "/static_content/" + page.image_path;
                        }
                        imageElement.alt = story.title
                            ? `Cover image for ${story.title}`
                            : "Cover image";
                        // Basic styling for preview - can be enhanced with CSS
                        imageElement.style.maxWidth = "80%";
                        imageElement.style.maxHeight = "400px";
                        imageElement.style.display = "block";
                        imageElement.style.margin = "20px auto"; // Center it a bit
                        pageContainer.appendChild(imageElement);
                    } else if (page.image_description) {
                        // Fallback to description if no image
                        const descElement = document.createElement("p");
                        descElement.style.fontStyle = "italic";
                        descElement.textContent = `Cover Image Description: ${page.image_description}`;
                        pageContainer.appendChild(descElement);
                    }
                } else {
                    // Regular content page
                    pageContainer.classList.add("story-content-page-preview");

                    const pageNumberElement = document.createElement("h4");
                    pageNumberElement.textContent = `Page ${page.page_number}`;
                    pageContainer.appendChild(pageNumberElement);

                    if (page.text) {
                        const textElement = document.createElement("p");
                        textElement.textContent = page.text;
                        pageContainer.appendChild(textElement);
                    }

                    if (page.image_path) {
                        const imageElement = document.createElement("img");
                        imageElement.classList.add("content-page-image");
                        // Ensure the path is correctly formed for static content
                        if (page.image_path.startsWith("data/")) {
                            imageElement.src =
                                "/static_content/" + page.image_path.substring("data/".length);
                        } else if (page.image_path.startsWith("/static_content/")) {
                            imageElement.src = page.image_path; // Already correctly prefixed
                        } else {
                            // Assuming it might be a relative path that needs the prefix
                            imageElement.src = "/static_content/" + page.image_path;
                        }
                        imageElement.alt = `Image for page ${page.page_number}`;
                        imageElement.style.maxWidth = "300px";
                        imageElement.style.maxHeight = "300px";
                        imageElement.style.display = "block";
                        imageElement.style.marginTop = "10px";
                        imageElement.style.marginBottom = "10px";
                        pageContainer.appendChild(imageElement);
                    } else if (page.image_description) {
                        const descElement = document.createElement("p");
                        descElement.style.fontStyle = "italic";
                        descElement.textContent = `Image Description: ${page.image_description}`;
                        pageContainer.appendChild(descElement);
                    }
                }

                storyPreviewContent.appendChild(pageContainer);
                // Add a separator if not the last page (considering sortedPages)
                if (index < sortedPages.length - 1) {
                    storyPreviewContent.appendChild(document.createElement("hr"));
                }
            });
        } else {
            const noPagesElement = document.createElement("p");
            noPagesElement.textContent =
                "This story has no pages or page data is missing.";
            storyPreviewContent.appendChild(noPagesElement);
        }

        if (exportPdfButton) {
            const shouldShowButton = story.pages && story.pages.length > 0;
            console.log(
                "[displayStory] Condition (story.pages && story.pages.length > 0):",
                shouldShowButton,
            );
            exportPdfButton.style.display = shouldShowButton
                ? "inline-block"
                : "none"; // Changed to inline-block
            exportPdfButton.classList.add("action-button-secondary"); // Add class for styling
            console.log(
                "[displayStory] exportPdfButton display set to:",
                exportPdfButton.style.display,
            );
        } else {
            console.error(
                "[displayStory] exportPdfButton element is NULL or undefined!",
            );
        }
    }

    function showSection(sectionToShow) {
        // Clear message area when changing sections
        if (messageArea) {
            messageArea.textContent = "";
            messageArea.style.backgroundColor = "transparent"; // Reset background
            messageArea.style.border = "none"; // Reset border
        }
        // Ensure adminPanelContainer is part of this array
        [
            authSection,
            storyCreationSection,
            storyPreviewSection,
            browseStoriesSection,
            adminPanelContainer,
        ].forEach((section) => {
            if (section) section.style.display = "none";
        });
        if (sectionToShow) {
            sectionToShow.style.display = "block";
            // If showing auth section, ensure login form is visible and signup is hidden by default
            if (sectionToShow === authSection) {
                loginForm.style.display = "block";
                signupForm.style.display = "none";
                const authSectionHeading = authSection.querySelector("h2");
                if (authSectionHeading) {
                    authSectionHeading.textContent = "Login";
                }
            }
            // When navigating TO storyPreviewSection directly (e.g. from browse),
            // we don't know if a story is loaded yet, so PDF button should be hidden.
            // displayStory will manage its visibility based on actual content.
            if (sectionToShow === storyPreviewSection) {
                if (exportPdfButton) exportPdfButton.style.display = "none";
            }
        }
    }

    function displayMessage(message, type = "info") {
        // type can be 'info', 'success', 'warning', 'error'
        messageArea.textContent = String(message); // Ensure message is always a string

        switch (type) {
            case "error":
                messageArea.style.color = "#FF6B6B"; // Red
                messageArea.style.backgroundColor = "rgba(255, 107, 107, 0.1)";
                messageArea.style.border = "1px solid rgba(255, 107, 107, 0.3)";
                break;
            case "warning":
                messageArea.style.color = "#FFA500"; // Orange
                messageArea.style.backgroundColor = "rgba(255, 165, 0, 0.1)";
                messageArea.style.border = "1px solid rgba(255, 165, 0, 0.3)";
                break;
            case "success":
                messageArea.style.color = "#6BFF6B"; // Green
                messageArea.style.backgroundColor = "rgba(107, 255, 107, 0.1)";
                messageArea.style.border = "1px solid rgba(107, 255, 107, 0.3)";
                break;
            case "info":
            default:
                messageArea.style.color = "#ADD8E6"; // Light Blue for info
                messageArea.style.backgroundColor = "rgba(173, 216, 230, 0.1)";
                messageArea.style.border = "1px solid rgba(173, 216, 230, 0.3)";
                break;
        }
        messageArea.style.padding = "0.8rem";
        messageArea.style.borderRadius = "4px";
    }

    function updateNav(isLoggedIn) {
        if (isLoggedIn) {
            navLoginSignup.style.display = "none";
            navCreateStory.style.display = "inline-block";
            navBrowseStories.style.display = "inline-block";
            navLogout.style.display = "inline-block";
            // Show admin link only if user is admin
            fetchAndSetUserRole(); // Call this to determine if admin link should be shown
        } else {
            navLoginSignup.style.display = "inline-block";
            navCreateStory.style.display = "none";
            navBrowseStories.style.display = "none";
            navLogout.style.display = "none";
            if (navAdminPanel) navAdminPanel.style.display = "none"; // Hide admin panel link on logout
            showSection(authSection);
        }
    }

    async function fetchAndSetUserRole() {
        if (!localStorage.getItem("authToken")) {
            if (navAdminPanel) navAdminPanel.style.display = "none";
            return;
        }
        try {
            const user = await apiRequest("/users/me/");
            if (user && user.role === "admin") {
                if (navAdminPanel) navAdminPanel.style.display = "inline-block";
            } else {
                if (navAdminPanel) navAdminPanel.style.display = "none";
            }
        } catch (error) {
            console.error("Error fetching user details for role:", error);
            if (navAdminPanel) navAdminPanel.style.display = "none";
        }
    }

    // --- API CALLS ---
    async function apiRequest(
        endpoint,
        method = "GET",
        body = null,
        isFormData = false,
    ) {
        // console.log('<<<<< SCRIPT_JS_VERSION_DEBUG_A - apiRequest - START >>>>>');
        try {
            // console.log('[apiRequest] Received body parameter (cleaned):', body === null ? null : JSON.parse(JSON.stringify(body)));
        } catch (e) {
            console.error(
                "[apiRequest] Could not stringify/parse received body param for logging:",
                e,
                body,
            );
        }
        // console.log('[apiRequest] Received endpoint:', endpoint, 'Method:', method, 'isFormData:', isFormData);

        const token = localStorage.getItem("authToken"); // Corrected: Use 'authToken'
        const headers = {
            Authorization: `Bearer ${token}`,
        };
        if (!isFormData) {
            headers["Content-Type"] = "application/json";
        }

        const options = {
            method: method,
            headers: headers,
        };

        if (body !== null && !isFormData) {
            // console.log('<<<<< SCRIPT_JS_VERSION_DEBUG_A - apiRequest - STEP 1 - Stringifying body for options.body >>>>>');
            try {
                options.body = JSON.stringify(body);
                // console.log('<<<<< SCRIPT_JS_VERSION_DEBUG_A - apiRequest - STEP 2 - options.body after stringify >>>>>');
                // console.log('[apiRequest] options.body (this is the string that will be sent):', options.body);
            } catch (e) {
                // console.error('<<<<< SCRIPT_JS_VERSION_DEBUG_A - apiRequest - ERROR STRINGIFYING BODY >>>>>', e);
                console.error(
                    "[apiRequest] Body object that failed to stringify:",
                    body,
                );
                // Display error to user and stop
                displayMessage(
                    "Error preparing data for the server. See console for details.",
                    "error",
                );
                hideSpinner();
                throw e;
            }
        } else if (body !== null && isFormData) {
            options.body = body;
            console.log("[apiRequest] options.body is FormData.");
        }

        // console.log('<<<<< SCRIPT_JS_VERSION_DEBUG_A - apiRequest - STEP 3 - Final options object before fetch >>>>>');
        // console.log('[apiRequest] Final options object structure (logged directly):', options);
        try {
            // console.log('[apiRequest] Final options object (cleaned for inspection):', JSON.parse(JSON.stringify(options)));
        } catch (e) {
            console.error(
                "[apiRequest] Could not stringify/parse final options for logging:",
                e,
                options,
            );
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
                } catch (e) {
                    const errorText = await response
                        .text()
                        .catch(() => response.statusText);
                    responseData = {
                        detail: errorText || `HTTP error! Status: ${response.status}`,
                    };
                }
                const errorDetail =
                    responseData && responseData.detail
                        ? responseData.detail
                        : `Unknown error. Status: ${response.status}`;
                console.error(`[apiRequest] API Error: ${errorDetail}`, responseData);
                // Handle expired/invalid token (401)
                if (
                    response.status === 401 &&
                    errorDetail &&
                    errorDetail.toLowerCase().includes("token")
                ) {
                    displayMessage(
                        "Your session has expired. Please log in again.",
                        "error",
                    );
                    localStorage.removeItem("authToken");
                    // Optionally, redirect to login or show login modal
                    if (typeof showLoginForm === "function") showLoginForm();
                } else if (
                    !messageArea.textContent.includes("Failed") &&
                    !messageArea.textContent.includes("error")
                ) {
                    displayMessage(String(errorDetail), "error");
                }
                throw new Error(String(errorDetail));
            }

            // If response.ok is true
            // console.log('<<<<< SCRIPT_JS_VERSION_DEBUG_A - apiRequest - STEP 5B - Response OK, processing body >>>>>');
            try {
                const contentType = response.headers.get("content-type");
                if (
                    response.status === 204 ||
                    response.headers.get("content-length") === "0"
                ) {
                    responseData = null;
                    // console.log('[apiRequest] Success response data (No Content / Empty Body)');
                } else if (
                    contentType &&
                    contentType.indexOf("application/json") !== -1
                ) {
                    responseData = await response.json();
                    // console.log('[apiRequest] Success response data (JSON):', responseData);
                } else {
                    responseData = await response.text();
                    // console.log('[apiRequest] Success response data (Text):', responseData);
                }
            } catch (e) {
                // console.error('<<<<< SCRIPT_JS_VERSION_DEBUG_A - apiRequest - ERROR PARSING SUCCESS RESPONSE BODY >>>>>', e);
                displayMessage(
                    "Error processing server response. See console.",
                    "error",
                );
                throw e;
            }

            // console.log('<<<<< SCRIPT_JS_VERSION_DEBUG_A - apiRequest - STEP 6 - Returning responseData >>>>>');
            return responseData;
        } catch (error) {
            // console.error('<<<<< SCRIPT_JS_VERSION_DEBUG_A - apiRequest - FETCH FAILED or error in response handling >>>>>', error);
            hideSpinner();
            if (
                !messageArea.textContent.includes("Failed") &&
                !messageArea.textContent.includes("error")
            ) {
                displayMessage(
                    error.message ||
                    "An unexpected error occurred. Please check the console.",
                    "error",
                );
            }
            throw error;
        }
    }

    // New function to update story title
    async function updateStoryTitle(
        storyId,
        newTitle,
        titleTextElement,
        editIconElement,
        editFormElement,
    ) {
        showSpinner();
        try {
            const updatedStory = await apiRequest(
                `/stories/${storyId}/title`,
                "PUT",
                { title: newTitle },
            );
            if (updatedStory && updatedStory.title) {
                titleTextElement.textContent = updatedStory.title;
                displayMessage("Story title updated successfully!", "success");
                // Also update the title on the title page if it's rendered
                const titlePageTitleElem = storyPreviewContent.querySelector(
                    ".title-page-story-title",
                );
                if (
                    titlePageTitleElem &&
                    parseInt(
                        titlePageTitleElem.closest(".story-title-page-preview").dataset
                            .pageNumber,
                        10,
                    ) === 0
                ) {
                    titlePageTitleElem.textContent = updatedStory.title;
                }
            } else {
                displayMessage(
                    "Failed to update title: No updated story data returned.",
                    "error",
                );
            }
        } catch (error) {
            console.error("Failed to update story title:", error);
            // Error message is already displayed by apiRequest
            // displayMessage(`Error updating title: ${error.message || 'Unknown error'}`, 'error');
        } finally {
            hideSpinner();
            // Reset UI
            titleTextElement.style.display = "inline"; // Or 'block' or 'initial'
            editIconElement.style.display = "inline";
            editFormElement.style.display = "none";
        }
    }

    // --- POPULATE DYNAMIC FORM ELEMENTS ---
    async function populateDropdown(selectElementName, listName) {
        const selectElement = storyCreationForm[selectElementName];
        if (!selectElement) {
            console.error(`Select element with name '${selectElementName}' not found.`);
            return;
        }

        try {
            const items = await apiRequest(`/dynamic-lists/${listName}/active-items`);

            selectElement.innerHTML = '<option value="">Select an option</option>'; // Clear and add a placeholder

            if (items && items.length > 0) {
                items.forEach(item => {
                    const option = document.createElement("option");
                    option.value = item.item_value; // Corrected from item.value
                    option.textContent = item.item_label; // Corrected from item.label
                    selectElement.appendChild(option);
                });
            } else {
                console.warn(`No items found for list: ${listName}`);
            }
        } catch (error) {
            console.error(`Failed to load dynamic list ${listName}:`, error);
            selectElement.innerHTML = '<option value="" disabled>Error loading options</option>';
            // apiRequest function is expected to display the error message.
        }
    }

    function populateAllDropdowns() {
        console.log("[populateAllDropdowns] Starting to populate all dropdowns.");
        populateDropdown("story-genre", "story_genres");
        populateDropdown("story-image-style", "image_styles_app");
        populateDropdown(
            "story-word-to-picture-ratio",
            "word_to_picture_ratio",
        );
        populateDropdown("story-text-density", "text_density");
    }

    // --- END POPULATE DYNAMIC FORM ELEMENTS (Placeholder for correct positioning) ---
    // --- STORY ACTION FUNCTIONS (View/Edit, Template, Delete) ---
    async function viewOrEditStory(storyId, isDraft) {
        console.log(
            `[viewOrEditStory] Called with storyId: ${storyId}, isDraft: ${isDraft}`,
        );
        showSpinner();
        try {
            let storyData;
            if (isDraft) {
                console.log(`[viewOrEditStory] Fetching draft story ID: ${storyId}`);
                storyData = await apiRequest(`/stories/drafts/${storyId}`);
                if (storyData) {
                    populateCreateFormWithStoryData(storyData, true); // true for isEditingDraft
                    showSection(storyCreationSection);
                } else {
                    displayMessage("Could not load draft details.", "error");
                }
            } else {
                console.log(
                    `[viewOrEditStory] Fetching finalized story ID: ${storyId}`,
                );
                storyData = await apiRequest(`/stories/${storyId}`);
                if (storyData) {
                    showSection(storyPreviewSection);
                    displayStory(storyData);
                } else {
                    displayMessage("Could not load story details.", "error");
                }
            }
        } catch (error) {
            console.error("[viewOrEditStory] Error:", error);
            // displayMessage is usually handled by apiRequest
            if (
                !messageArea.textContent.includes("Failed") &&
                !messageArea.textContent.includes("error")
            ) {
                displayMessage(`Error loading story: ${error.message}`, "error");
            }
        } finally {
            hideSpinner();
        }
    }

    async function useStoryAsTemplate(storyId) {
        console.log(`[useStoryAsTemplate] Called with storyId: ${storyId}`);
        showSpinner();
        try {
            // Fetch the story data (can be draft or finalized, endpoint should give input params)
            // We use /stories/{story_id} as it returns the full story object including input params.
            // If it was a draft, its input params are what we want.
            // If it was a full story, its input params are also what we want.
            const storyData = await apiRequest(`/stories/${storyId}`);
            if (storyData) {
                populateCreateFormWithStoryData(storyData, false); // false for isEditingDraft, it's a template
                showSection(storyCreationSection);
                // currentStoryId will be set to null by populateCreateFormWithStoryData when not editing draft
                displayMessage(
                    `Form populated using "${storyData.title || "Selected Story"}" as a template. This will create a new story.`,
                    "info",
                );
            } else {
                displayMessage(
                    "Could not load story data to use as template.",
                    "error",
                );
            }
        } catch (error) {
            console.error("[useStoryAsTemplate] Error:", error);
            if (
                !messageArea.textContent.includes("Failed") &&
                !messageArea.textContent.includes("error")
            ) {
                displayMessage(
                    `Error using story as template: ${error.message}`,
                    "error",
                );
            }
        } finally {
            hideSpinner();
        }
    }

    async function deleteStory(storyId, listItemElement) {
        console.log(`[deleteStory] Called with storyId: ${storyId}`);
        showSpinner();
        try {
            await apiRequest(`/stories/${storyId}`, "DELETE");
            displayMessage("Story deleted successfully.", "success");
            if (listItemElement) {
                listItemElement.remove();
            }
            // If the deleted story was being previewed, clear the preview
            if (currentStoryId === storyId) {
                storyPreviewContent.innerHTML =
                    "<p>The story you were viewing has been deleted.</p>";
                if (exportPdfButton) exportPdfButton.style.display = "none";
                currentStoryId = null;
            }
            // Optionally, refresh the list if other stories might be affected or for consistency
            // await loadAndDisplayUserStories(); // Uncomment if a full refresh is desired
        } catch (error) {
            console.error("[deleteStory] Error:", error);
            // displayMessage is usually handled by apiRequest
            if (
                !messageArea.textContent.includes("Failed") &&
                !messageArea.textContent.includes("error")
            ) {
                displayMessage(`Error deleting story: ${error.message}`, "error");
            }
        } finally {
            hideSpinner();
        }
    }

    // Event listeners for switching between login and signup views
    if (showSignupLink) {
        showSignupLink.addEventListener("click", (e) => {
            e.preventDefault();
            if (loginForm && signupForm && authSection) {
                loginForm.style.display = "none";
                signupForm.style.display = "block";
                const authSectionHeading = authSection.querySelector("h2");
                if (authSectionHeading) {
                    authSectionHeading.textContent = "Sign Up";
                }
            }
        });
    }

    if (showLoginLink) {
        showLoginLink.addEventListener("click", (e) => {
            e.preventDefault();
            if (loginForm && signupForm && authSection) {
                signupForm.style.display = "none";
                loginForm.style.display = "block";
                const authSectionHeading = authSection.querySelector("h2");
                if (authSectionHeading) {
                    authSectionHeading.textContent = "Login";
                }
            }
        });
    }

    // Event listeners for navigation
    if (navCreateStory) {
        navCreateStory.addEventListener("click", () => {
            showSection(storyCreationSection);
            resetFormAndState();
            populateAllDropdowns(); // Populate dropdowns when navigating to the create form
            showSection(storyCreationSection);
        });
    }

    if (navBrowseStories) {
        navBrowseStories.addEventListener("click", async () => {
            showSection(browseStoriesSection);
            await loadAndDisplayUserStories();
        });
    }

    // --- AUTHENTICATION ---
    signupForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const username = signupForm.username.value;
        const email = signupForm.email.value; // Get email value
        const password = signupForm.password.value;
        try {
            await apiRequest("/users/", "POST", { username, email, password }); // Add email to payload
            displayMessage("Signup successful! Please login.", "success");
            signupForm.reset();
            loginForm.style.display = "block";
            signupForm.style.display = "none";
        } catch (error) { }
    });

    loginForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const username = loginForm.username.value;
        const password = loginForm.password.value;

        const formData = new URLSearchParams();
        formData.append("username", username);
        formData.append("password", password);

        try {
            const response = await fetch(`${API_BASE_URL}/token`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                body: formData,
            });
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: "Login failed" }));
                throw new Error(errorData.detail || "Login failed");
            }
            const data = await response.json();
            authToken = data.access_token;
            localStorage.setItem("authToken", authToken);
            updateNav(true);
            showSection(storyCreationSection); // Show creation form first
            populateAllDropdowns(); // Populate dropdowns
            loadAndDisplayUserStories(); // Then load stories
            displayMessage("Login successful!", "success");

            // Check for admin role and update UI
            await fetchAndSetUserRole();
        } catch (error) {
            displayMessage(error.message || "Login failed.", "error");
        }
    });

    navLogout.addEventListener("click", () => {
        authToken = null;
        localStorage.removeItem("authToken");
        updateNav(false);
        displayMessage("Logged out.", "info");
        currentStoryId = null;
        exportPdfButton.style.display = "none";
    });

    // --- STORY CREATION / DRAFT HANDLING ---

    // Function to gather form data
    function getStoryDataFromForm() {
        const mainCharacters = Array.from(
            document.querySelectorAll("#main-characters-fieldset .character-entry"),
        ).map((entry) => {
            const nameInput = entry.querySelector('input[id^="char-name-"]');
            const ageInput = entry.querySelector('input[id^="char-age-"]');
            const genderInput = entry.querySelector('input[id^="char-gender-"]');
            const physicalTextarea = entry.querySelector(
                'textarea[id^="char-physical-appearance-"]',
            );
            const clothingTextarea = entry.querySelector(
                'textarea[id^="char-clothing-style-"]',
            );
            const traitsTextarea = entry.querySelector(
                'textarea[id^="char-key-traits-"]',
            );

            const ageValue = ageInput ? ageInput.value.trim() : "";

            return {
                name: nameInput ? nameInput.value.trim() : "",
                age: ageValue !== "" ? parseInt(ageValue, 10) : null, // Parse to int or send null
                gender: genderInput ? genderInput.value.trim() : "",
                physical_appearance: physicalTextarea
                    ? physicalTextarea.value.trim()
                    : "",
                clothing_style: clothingTextarea ? clothingTextarea.value.trim() : "",
                key_traits: traitsTextarea ? traitsTextarea.value.trim() : "",
            };
        });

        const numPagesValue = document.getElementById("story-num-pages").value; // Corrected ID
        let numPagesAsInt = parseInt(numPagesValue, 10);

        // Ensure num_pages is a positive integer, defaulting to 1 if empty, NaN, or <= 0.
        // This is to satisfy StoryCreate's requirement for num_pages: int and downstream AI logic.
        if (isNaN(numPagesAsInt) || numPagesAsInt <= 0) {
            numPagesAsInt = 1; // Default to 1 if not a valid positive number
        }

        return {
            title: document.getElementById("story-title").value, // FR-FE-DRAFT-01: Add title
            genre: document.getElementById("story-genre").value, // Corrected ID
            story_outline: document.getElementById("story-outline").value, // Corrected ID
            main_characters: mainCharacters,
            num_pages: numPagesAsInt,
            tone: document.getElementById("story-tone").value, // Corrected ID
            setting: document.getElementById("story-setting").value, // Corrected ID
            word_to_picture_ratio: document.getElementById(
                "story-word-to-picture-ratio",
            ).value, // Corrected ID
            text_density: document.getElementById("story-text-density").value, // Corrected ID
            image_style: document.getElementById("story-image-style").value, // Corrected ID
            // is_draft will be handled by the endpoint/payload structure
        };
    }

    // Event listener for "Save Draft" button
    if (saveDraftButton) {
        saveDraftButton.addEventListener("click", async function (event) {
            event.preventDefault();
            displayMessage("Saving draft...", "info");
            showSpinner();

            const storyData = getStoryDataFromForm();
            console.log("[SaveDraft] Story data for draft:", storyData);

            if (!storyData.genre || !storyData.story_outline) {
                displayMessage(
                    "Genre and Story Outline are required to save a draft.",
                    "warning",
                );
                hideSpinner();
                return;
            }

            try {
                let savedDraft;
                if (currentStoryId && currentStoryIsDraft) {
                    console.log(
                        `[SaveDraft] Updating existing draft ID: ${currentStoryId}`,
                    );
                    savedDraft = await apiRequest(
                        `/stories/drafts/${currentStoryId}`,
                        "PUT",
                        storyData,
                    );
                } else {
                    console.log("[SaveDraft] Creating new draft.");
                    savedDraft = await apiRequest("/stories/drafts/", "POST", storyData);
                }

                if (savedDraft && savedDraft.id) {
                    currentStoryId = savedDraft.id;
                    currentStoryIsDraft = true;
                    document.getElementById("story-title").value = savedDraft.title || "";
                    if (generateStoryButton) {
                        generateStoryButton.textContent = "Finalize & Generate Story";
                    }
                    displayMessage(
                        `Draft "${savedDraft.title || "Untitled Draft"}" saved successfully!`,
                        "success",
                    );
                    console.log("[SaveDraft] Draft saved/updated:", savedDraft);
                } else {
                    displayMessage(
                        "Failed to save draft. Response was not in the expected format.",
                        "error",
                    );
                    console.warn("[SaveDraft] Save draft response issue:", savedDraft);
                }
            } catch (error) {
                console.error("[SaveDraft] Error saving draft:", error);
                if (
                    !messageArea.textContent.includes("Failed") &&
                    !messageArea.textContent.includes("error")
                ) {
                    displayMessage(
                        `Draft saving failed: ${error.message || "Unknown error"}`,
                        "error",
                    );
                }
            } finally {
                hideSpinner();
            }
        });
    }

    // Modified Event listener for the main story creation/finalization form submission
    if (generateStoryButton) {
        generateStoryButton.addEventListener("click", async function (event) {
            event.preventDefault();
            updateStoryGenerationStatus("Generating story outline and text...");
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
                console.log(
                    "[FormSubmit] Finalizing draft. currentStoryId:",
                    currentStoryId,
                );
                payload = {
                    story_input: storyData,
                    draft_id: parseInt(currentStoryId),
                };
                endpoint = `/stories/`;
                method = "POST";
            } else if (currentStoryId && !currentStoryIsDraft) {
                console.warn(
                    '[FormSubmit] Form was populated from a finalized story, but "Generate Story" was clicked. Treating as new story creation.',
                );
                payload = { story_input: storyData };
                endpoint = "/stories/";
                method = "POST";
                currentStoryId = null;
                currentStoryIsDraft = false;
            } else {
                console.log("[FormSubmit] Creating a new story from scratch.");
                payload = { story_input: storyData };
                endpoint = "/stories/";
                method = "POST";
            }

            // console.log('<<<<< SCRIPT_JS_VERSION_DEBUG_A - generateStoryButton - STEP 2 - Payload constructed >>>>>');
            try {
                // console.log('[FormSubmit] Payload to be sent to apiRequest (cleaned):', JSON.parse(JSON.stringify(payload)));
            } catch (e) {
                // This specific try-catch for logging can be removed.
                // console.error('[FormSubmit] Could not stringify/parse payload for logging:', e, payload);
            }
            // console.log('[FormSubmit] Endpoint:', endpoint, 'Method:', method);

            try {
                // Main try for API call and processing
                // console.log('<<<<< SCRIPT_JS_VERSION_DEBUG_A - generateStoryButton - STEP 3 - Calling apiRequest >>>>>');
                const result = await apiRequest(endpoint, method, payload);
                // console.log('<<<<< SCRIPT_JS_VERSION_DEBUG_A - generateStoryButton - STEP 4 - apiRequest returned >>>>>');
                // console.log('[FormSubmit] API Result (type):', typeof result, 'Is null?', result === null, 'Content:', result);

                if (result && typeof result === "object" && result.id) {
                    // console.log('<<<<< SCRIPT_JS_VERSION_DEBUG_A - generateStoryButton - STEP 4.1 - Result has ID:', result.id, 'Title:', result.title);
                    displayMessage("Story generated successfully!", "success"); // This message will be briefly visible
                    showSection(storyPreviewSection); // This clears the messageArea

                    try {
                        displayStory(result);
                        // console.log('<<<<< SCRIPT_JS_VERSION_DEBUG_A - generateStoryButton - STEP 5 - Story processed, displayStory called >>>>>');
                    } catch (displayError) {
                        console.error("Error during displayStory:", displayError);
                        // Display a message to the user that story display failed, but generation might have succeeded.
                        displayMessage(
                            `Error displaying story content: ${displayError.message}. The story might have been created; check 'Browse Stories'.`,
                            "error",
                        );
                        // The spinner will be hidden by the finally block.
                    }

                    currentStoryId = result.id;
                    currentStoryIsDraft = false;
                    console.log(
                        "[FormSubmit] Story generation successful. Current story ID:",
                        currentStoryId,
                        "Is Draft:",
                        currentStoryIsDraft,
                    );
                    // console.log('<<<<< SCRIPT_JS_VERSION_DEBUG_A - generateStoryButton - STEP 7 - State updated >>>>>');
                } else {
                    // console.log('<<<<< SCRIPT_JS_VERSION_DEBUG_A - generateStoryButton - STEP 4.X - Result is null, undefined, not an object, or lacks id.');
                    console.error(
                        "[FormSubmit] Story generation/finalization failed or returned invalid/unexpected data:",
                        result,
                    );
                    displayMessage(
                        "Failed to generate story. The server response was not as expected. Please check console.",
                        "error",
                    );
                }
            } catch (error) {
                // Catches errors from apiRequest itself or issues before it (e.g. payload stringify if uncommented)
                // console.error('<<<<< SCRIPT_JS_VERSION_DEBUG_A - generateStoryButton - ERROR IN API REQUEST CALL OR SUBSEQUENT HANDLING >>>>>', error);
                console.error(
                    "[FormSubmit] Error during story generation process:",
                    error,
                );
                // apiRequest usually displays a message on failure. This is a fallback or for more context.
                if (
                    !messageArea.textContent.includes("Failed") &&
                    !messageArea.textContent.includes("error") &&
                    !messageArea.textContent.includes("Error generating story")
                ) {
                    displayMessage(
                        `Error generating story: ${error.message || "Unknown error"}. Please check console.`,
                        "error",
                    );
                }
            } finally {
                hideSpinner();
            }
        });
    }

    // --- PROGRESS BAR UI ---
    let progressBar = document.getElementById("story-progress-bar");
    if (!progressBar) {
        progressBar = document.createElement("div");
        progressBar.id = "story-progress-bar";
        progressBar.style.display = "none";
        progressBar.style.width = "100%";
        progressBar.style.background = "#eee";
        progressBar.style.borderRadius = "6px";
        progressBar.style.margin = "10px 0";
        progressBar.innerHTML =
            '<div id="story-progress-bar-inner" style="width:0%;height:18px;background:#4caf50;border-radius:6px;transition:width 0.4s;"></div>';
        if (messageArea && messageArea.parentNode) {
            messageArea.parentNode.insertBefore(progressBar, messageArea.nextSibling);
        }
    }
    function showProgressBar() {
        progressBar.style.display = "block";
        updateProgressBar(0);
    }
    function hideProgressBar() {
        progressBar.style.display = "none";
        updateProgressBar(0);
    }
    function updateProgressBar(percent) {
        const inner = document.getElementById("story-progress-bar-inner");
        if (inner) inner.style.width = percent + "%";
    }

    // --- STORY GENERATION PROGRESS FEEDBACK ---
    function updateStoryGenerationStatus(message, percent) {
        displayMessage(message, "info");
        if (typeof percent === "number") updateProgressBar(percent);
    }

    // Patch: Simulate progress while waiting for backend
    async function simulateStoryGenerationProgress(mainCharacters, numPages) {
        showProgressBar();
        let steps = [];
        steps.push({ msg: "Generating story outline and text...", pct: 5 });
        if (mainCharacters && mainCharacters.length > 0) {
            mainCharacters.forEach((char, idx) => {
                steps.push({
                    msg: `Creating reference image for '${char.name || "character"}'...`,
                    pct: 10 + idx * 10,
                });
            });
        }
        steps.push({ msg: "Creating cover page image...", pct: 30 });
        let totalPages = numPages || 3;
        for (let i = 1; i <= totalPages; i++) {
            steps.push({
                msg: `Creating image for page ${i}...`,
                pct: 30 + Math.floor((i / totalPages) * 60),
            });
        }
        steps.push({ msg: "Finalizing story...", pct: 98 });
        for (let i = 0; i < steps.length; i++) {
            updateStoryGenerationStatus(steps[i].msg, steps[i].pct);
            await new Promise((r) => setTimeout(r, 1000));
        }
        updateProgressBar(100);
    }

    // --- STORY BROWSING ---
    async function loadAndDisplayUserStories(includeDrafts = true) {
        showSpinner();
        if (!userStoriesList) {
            console.error(
                "[loadAndDisplayUserStories] userStoriesList element not found.",
            );
            displayMessage("Cannot display stories: List area missing.", "error");
            hideSpinner();
            return;
        }
        userStoriesList.innerHTML = ""; // Clear previous stories

        try {
            const stories = await apiRequest(
                `/stories/?include_drafts=${includeDrafts}&skip=0&limit=100`,
            );
            if (stories && stories.length > 0) {
                stories.forEach((story) => {
                    const listItem = document.createElement("li");
                    listItem.classList.add("story-item");
                    listItem.dataset.storyId = story.id;

                    const title = document.createElement("h3");
                    title.textContent = story.title || "Untitled Story";
                    if (story.is_draft) {
                        title.textContent += " (Draft)";
                    }
                    listItem.appendChild(title);

                    const date = document.createElement("p");
                    date.classList.add("story-date");
                    date.textContent = `Last updated: ${formatDate(story.updated_at || story.created_at)}`;
                    listItem.appendChild(date);

                    if (story.story_outline) {
                        const snippet = document.createElement("p");
                        snippet.classList.add("story-snippet");
                        snippet.textContent =
                            story.story_outline.substring(0, 150) +
                            (story.story_outline.length > 150 ? "..." : "");
                        listItem.appendChild(snippet);
                    }

                    // Action buttons container
                    const actionsContainer = document.createElement("div");
                    actionsContainer.classList.add("story-item-actions");

                    // View Story Button
                    const viewButton = document.createElement("button");
                    viewButton.textContent = story.is_draft ? "Edit Draft" : "View Story";
                    viewButton.classList.add("action-button-secondary"); // Apply new class
                    viewButton.addEventListener("click", (e) => {
                        e.stopPropagation(); // Prevent triggering click on listItem
                        viewOrEditStory(story.id, story.is_draft);
                    });
                    actionsContainer.appendChild(viewButton);

                    // Use as Template Button
                    const useAsTemplateButton = document.createElement("button");
                    useAsTemplateButton.textContent = "Use as Template";
                    useAsTemplateButton.classList.add("action-button-secondary"); // Apply new class
                    useAsTemplateButton.addEventListener("click", (e) => {
                        e.stopPropagation();
                        useStoryAsTemplate(story.id);
                    });
                    actionsContainer.appendChild(useAsTemplateButton);

                    // Delete Story Button
                    const deleteButton = document.createElement("button");
                    deleteButton.textContent = "Delete";
                    deleteButton.classList.add(
                        "admin-action-button",
                        "admin-delete-user",
                    ); // MODIFIED: Apply new class for delete button
                    deleteButton.addEventListener("click", async (e) => {
                        e.stopPropagation();
                        if (
                            confirm(
                                `Are you sure you want to delete "${story.title || "this story"}"? This cannot be undone.`,
                            )
                        ) {
                            await deleteStory(story.id, listItem);
                        }
                    });
                    actionsContainer.appendChild(deleteButton);

                    listItem.appendChild(actionsContainer);

                    // Click on list item to view/edit
                    listItem.addEventListener("click", () => {
                        viewOrEditStory(story.id, story.is_draft);
                    });

                    userStoriesList.appendChild(listItem);
                });
            } else {
                userStoriesList.innerHTML =
                    "<p>You haven't created any stories yet.</p>";
                displayMessage("No stories found.", "info");
            }
        } catch (error) {
            console.error(
                "[loadAndDisplayUserStories] Error fetching stories:",
                error,
            );
            // displayMessage already handled by apiRequest usually
            if (
                !messageArea.textContent.includes("Failed") &&
                !messageArea.textContent.includes("error")
            ) {
                displayMessage(`Failed to load stories: ${error.message}`, "error");
            }
            userStoriesList.innerHTML =
                "<p>Could not load stories. Please try again later.</p>";
        } finally {
            hideSpinner();
        }
    }

    // --- PDF EXPORT ---
    if (exportPdfButton) {
        exportPdfButton.addEventListener("click", async () => {
            if (!currentStoryId) {
                displayMessage(
                    "No story selected or story ID is missing. Cannot export PDF.",
                    "error",
                );
                return;
            }

            displayMessage("Exporting PDF... Please wait.", "info");
            showSpinner();

            try {
                const token = localStorage.getItem("authToken");
                const response = await fetch(
                    `${API_BASE_URL}/stories/${currentStoryId}/pdf`,
                    {
                        // Changed endpoint to /pdf
                        method: "GET",
                        headers: {
                            Authorization: `Bearer ${token}`,
                        },
                    },
                );

                if (!response.ok) {
                    let errorDetail = "Unknown error";
                    try {
                        const errorData = await response.json();
                        errorDetail = errorData.detail || JSON.stringify(errorData);
                    } catch (e) {
                        errorDetail = await response.text();
                    }
                    throw new Error(
                        `PDF export failed: ${response.status} ${response.statusText}. Detail: ${errorDetail}`,
                    );
                }

                const blob = await response.blob();
                const contentDisposition = response.headers.get("content-disposition");
                let filename = "story.pdf"; // Default filename
                if (contentDisposition) {
                    const filenameMatch = contentDisposition.match(/filename="?(.+)"?/i);
                    if (filenameMatch && filenameMatch.length > 1) {
                        filename = filenameMatch[1];
                    }
                }

                const url = window.URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.style.display = "none";
                a.href = url;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);

                displayMessage("PDF exported successfully!", "success");
            } catch (error) {
                console.error("[PDFExport] Error exporting PDF:", error);
                displayMessage(`Error exporting PDF: ${error.message}`, "error");
            } finally {
                hideSpinner();
            }
        }); // This closes the event listener
    } else {
        console.error("Export PDF button not found during event listener setup.");
    }

    // --- HELPER FUNCTION TO POPULATE CREATE FORM ---
    function populateCreateFormWithStoryData(storyData, isEditingDraft = false) {
        // Added isEditingDraft
        console.log(
            "[populateCreateFormWithStoryData] Populating form. isEditingDraft:",
            isEditingDraft,
            "Story:",
            storyData,
        );

        resetFormAndState();

        document.getElementById("story-title").value = storyData.title || "";
        document.getElementById("story-genre").value = storyData.genre || "";
        document.getElementById("story-outline").value =
            storyData.story_outline || "";
        document.getElementById("story-num-pages").value = storyData.num_pages || 5;
        document.getElementById("story-tone").value = storyData.tone || "";
        document.getElementById("story-setting").value = storyData.setting || "";
        document.getElementById("story-word-to-picture-ratio").value =
            storyData.word_to_picture_ratio || "One image per page";
        document.getElementById("story-text-density").value =
            storyData.text_density || "Concise (~30-50 words)";
        document.getElementById("story-image-style").value =
            storyData.image_style || "Default";

        const fieldset = document.getElementById("main-characters-fieldset");
        const existingEntries = fieldset.querySelectorAll(".character-entry");
        existingEntries.forEach((entry, index) => {
            if (index > 0) entry.remove();
        });
        characterCount = 0;

        if (storyData.main_characters && storyData.main_characters.length > 0) {
            storyData.main_characters.forEach((char, index) => {
                if (index > 0) {
                    addCharacterEntry();
                } else {
                    characterCount = 1;
                }
                document.getElementById(`char-name-${characterCount}`).value =
                    char.name || "";
                const ageEl = document.getElementById(`char-age-${characterCount}`);
                if (ageEl) ageEl.value = char.age || "";
                const genderEl = document.getElementById(
                    `char-gender-${characterCount}`,
                );
                if (genderEl) genderEl.value = char.gender || "";
                const physicalEl = document.getElementById(
                    `char-physical-appearance-${characterCount}`,
                );
                if (physicalEl) physicalEl.value = char.physical_appearance || "";
                const clothingEl = document.getElementById(
                    `char-clothing-style-${characterCount}`,
                );
                if (clothingEl) clothingEl.value = char.clothing_style || "";
                const traitsEl = document.getElementById(
                    `char-key-traits-${characterCount}`,
                );
                if (traitsEl) traitsEl.value = char.key_traits || "";

                const detailsDiv = document.getElementById(
                    `char-details-${characterCount}`,
                );
                const toggleButton = document.getElementById(
                    `char-details-toggle-${characterCount}`,
                ); // Changed from querySelector to getElementById
                if (detailsDiv) detailsDiv.style.display = "none";
                if (toggleButton) {
                    toggleButton.textContent = "Show Details";
                    // REMOVED: initializeCharacterDetailsToggle(toggleButton);
                }
            });
        } else {
            characterCount = 1;
            const firstCharToggle = document.getElementById("char-details-toggle-1"); // Changed from querySelector to getElementById
            const firstCharDetails = document.getElementById("char-details-1");
            if (firstCharDetails) firstCharDetails.style.display = "none";
            if (firstCharToggle) {
                firstCharToggle.textContent = "Show Details";
                // REMOVED: initializeCharacterDetailsToggle(firstCharToggle);
            }
        }

        if (isEditingDraft) {
            currentStoryId = storyData.id;
            currentStoryIsDraft = true;
            if (generateStoryButton) {
                generateStoryButton.textContent = "Finalize & Generate Story";
            }
            displayMessage(
                `Editing draft: "${storyData.title || "Untitled Draft"}". Make your changes and click "Save Draft" or "Finalize & Generate Story".`,
                "info",
            );
        } else {
            // Using as template
            currentStoryId = null; // New story, so no ID yet
            currentStoryIsDraft = false; // Not a draft being edited
            if (generateStoryButton) {
                generateStoryButton.textContent = "Generate Story";
            }
            displayMessage(
                `Form populated with template from "${storyData.title || "Untitled Story"}". Review and modify as needed. This will create a new story.`,
                "info",
            );
        }

        showSection(storyCreationSection); // Ensure the form is visible
        console.log(
            "[populateCreateFormWithStoryData] Form population complete. currentStoryId:",
            currentStoryId,
            "currentStoryIsDraft:",
            currentStoryIsDraft,
        );
    }

    // REMOVED: The local initializeCharacterDetailsToggle function comment block
    /*
      function initializeCharacterDetailsToggle(characterEntryDiv, characterIndex) { ... }
      */

    // Event delegation for toggling character details (This should be the only one active)
    const mainCharactersFieldset = document.getElementById(
        "main-characters-fieldset",
    );
    if (mainCharactersFieldset) {
        mainCharactersFieldset.addEventListener("click", function (event) {
            if (event.target.classList.contains("character-details-toggle")) {
                console.log(
                    "[Toggle Click] Button clicked:",
                    event.target,
                    "ID:",
                    event.target.id,
                );
                const targetId = event.target.dataset.target;
                console.log("[Toggle Click] Data-target ID:", targetId);
                const detailsDiv = document.getElementById(targetId);
                console.log("[Toggle Click] Details div found:", detailsDiv);

                if (detailsDiv) {
                    const isHidden =
                        window.getComputedStyle(detailsDiv).display === "none";
                    console.log(
                        `[Toggle Click] Details div (${targetId}) isHidden (computed): ${isHidden}, current style.display: '${detailsDiv.style.display}'`,
                    );
                    detailsDiv.style.display = isHidden ? "block" : "none";
                    event.target.textContent = isHidden ? "Hide Details" : "Show Details";
                    console.log(
                        `[Toggle Click] Set detailsDiv.style.display to '${detailsDiv.style.display}', button text to '${event.target.textContent}'`,
                    );
                } else {
                    console.error(
                        "[Toggle Click] Details div not found for targetId:",
                        targetId,
                    );
                }
            }
        });
    } else {
        console.error(
            "CRITICAL: main-characters-fieldset not found for event delegation!",
        );
    }

    // --- ADMIN PANEL USER EDITING ---
    if (adminUserTableBody) {
        adminUserTableBody.addEventListener("click", async function (e) {
            const target = e.target;
            if (target.classList.contains("admin-edit-user")) {
                // Only allow one edit at a time
                const editingRow = adminUserTableBody.querySelector("tr.editing");
                if (editingRow)
                    return displayMessage(
                        "Finish editing the current user first.",
                        "warning",
                    );
                const row = target.closest("tr");
                if (!row) return;
                row.classList.add("editing");
                // Get current values
                const id = row.children[0].textContent.trim();
                const username = row.children[1].textContent.trim();
                const email = row.children[2].textContent.trim();
                const role = row.children[3].textContent.trim();
                const active = row.children[4].textContent.trim() === "true";
                // Store original values as data attributes for change detection
                row.setAttribute("data-orig-email", email);
                row.setAttribute("data-orig-role", role);
                row.setAttribute("data-orig-active", active ? "true" : "false");
                // Determine if editing self (current user)
                let currentUserId = localStorage.getItem('currentUserId');
                if (!currentUserId) {
                    // Try to fetch and cache current user id
                    try {
                        const me = await apiRequest('/users/me/');
                        if (me && me.id) {
                            currentUserId = String(me.id);
                            localStorage.setItem('currentUserId', currentUserId);
                        }
                    } catch (err) {
                        // fallback: don't block UI, just don't allow self role change
                        currentUserId = null;
                    }
                }
                const isSelf = currentUserId && id === currentUserId;
                // Replace cells with inputs, email now editable for all users
                row.children[2].innerHTML = `<input type="email" value="${email}" style="width: 95%">`;
                row.children[3].innerHTML = `
                <select name="role" ${isSelf ? 'disabled' : ''}>
                    <option value="user" ${role === 'user' ? 'selected' : ''}>user</option>
                    <option value="editor" ${role === 'editor' ? 'selected' : ''}>editor</option>
                    <option value="admin" ${role === 'admin' ? 'selected' : ''}>admin</option>
                </select>`;
                row.children[4].innerHTML = `
                <select name="active">
                    <option value="true" ${active ? 'selected' : ''}>true</option>
                    <option value="false" ${!active ? 'selected' : ''}>false</option>
                </select>`;

                // Replace "Edit" with "Save" and "Cancel"
                target.style.display = 'none';
                const actionsCell = row.children[5];
                actionsCell.innerHTML = `<button class="admin-save-user-changes">Save</button> <button class="admin-cancel-user-edit">Cancel</button>`;
            } else if (target.classList.contains("admin-cancel-user-edit")) {
                const row = target.closest("tr");
                if (!row) return;
                // Reload users to reset row
                if (typeof loadAdminUsers === "function") await loadAdminUsers();
            }
            if (target.classList.contains("admin-save-user")) {
                const row = target.closest("tr");
                if (!row) return;
                const id = row.children[0].textContent.trim();
                // Read original values from data attributes
                const prevEmail = row.getAttribute("data-orig-email") || "";
                const prevRole = row.getAttribute("data-orig-role") || "";
                const prevActive = row.getAttribute("data-orig-active") === "true";
                // Get new values


                const emailInput = row.children[2].querySelector("input");
                const email = emailInput ? emailInput.value.trim() : prevEmail;
                const roleSelect = row.children[3].querySelector("select");
                const role = roleSelect ? roleSelect.value : prevRole;
                const active = row.children[4].querySelector('input[type="checkbox"]').checked;
                // Determine if editing self (current user)
                let currentUserId = localStorage.getItem('currentUserId');
                if (!currentUserId) {
                    try {
                        const me = await apiRequest('/users/me/');
                        if (me && me.id) {
                            currentUserId = String(me.id);
                            localStorage.setItem('currentUserId', currentUserId);
                        }
                    } catch (err) {
                        currentUserId = null;
                    }
                }
                const isSelf = currentUserId && id === currentUserId;
                // Disable buttons
                target.disabled = true;
                row.querySelector(".admin-cancel-edit").disabled = true;
                let updateErrors = [];
                let updateCount = 0;
                let updateSuccess = 0;
                try {
                    // Role update (skip if editing self)
                    if (!isSelf && role !== prevRole) {
                        updateCount++;
                        try {
                            await apiRequest(`/admin/users/${id}/role`, "PUT", { role });
                            updateSuccess++;
                        } catch (err) {
                            updateErrors.push("role");
                        }
                    }
                    // Status update
                    if (active !== prevActive) {
                        updateCount++;
                        try {
                            await apiRequest(`/admin/users/${id}/status`, "PUT", {
                                is_active: active,
                            });
                            updateSuccess++;
                        } catch (err) {
                            updateErrors.push("active status");
                        }
                    }
                    // Email update (now supported for all users)
                    if (email !== prevEmail) {
                        updateCount++;
                        try {
                            await apiRequest(`/admin/users/${id}`, "PATCH", { email });
                            updateSuccess++;
                        } catch (err) {
                            updateErrors.push("email");
                        }
                    }
                    if (updateCount === 0) {
                        displayMessage("No changes to save.", "info");
                    } else if (updateErrors.length === 0) {
                        displayMessage("User updated successfully.", "success");
                    } else {
                        displayMessage(
                            "Failed to update: " + updateErrors.join(", "),
                            "error",
                        );
                    }
                    if (typeof loadAdminUsers === "function") await loadAdminUsers();
                } catch (error) {
                    displayMessage(
                        "Failed to update user: " + (error.message || "Unknown error"),
                        "error",
                    );
                    target.disabled = false;
                    row.querySelector(".admin-cancel-edit").disabled = false;
                }
            }
        });
    }

    // --- ADMIN PANEL TABS ---
    const adminTabUserMgmt = document.getElementById("adminTabUserMgmt");
    const adminTabDynamicLists = document.getElementById("adminTabDynamicLists");
    const adminUserManagementSection = document.getElementById("adminUserManagementSection");
    const adminDynamicListsSection = document.getElementById("adminDynamicListsSection");
    const dynamicListsContainer = document.getElementById("dynamicListsContainer");

    if (adminTabUserMgmt && adminTabDynamicLists && adminUserManagementSection && adminDynamicListsSection) {
        adminTabUserMgmt.addEventListener("click", function () {
            adminUserManagementSection.style.display = "block";
            adminDynamicListsSection.style.display = "none";
            adminTabUserMgmt.classList.add("active");
            adminTabDynamicLists.classList.remove("active");
        });
        adminTabDynamicLists.addEventListener("click", function () {
            adminUserManagementSection.style.display = "none";
            adminDynamicListsSection.style.display = "block";
            adminTabUserMgmt.classList.remove("active");
            adminTabDynamicLists.classList.add("active");
            loadAdminDynamicLists();
        });
    }

    // --- ADMIN PANEL: LOAD USERS FUNCTION ---
    async function loadAdminUsers() {
        if (!adminUserTableBody) return;
        adminUserTableBody.innerHTML = '<tr><td colspan="6">Loading users...</td></tr>';
        try {
            const users = await apiRequest("/admin/users");
            if (!users || users.length === 0) {
                adminUserTableBody.innerHTML = '<tr><td colspan="6">No users found.</td></tr>';
                return;
            }
            let html = '';
            users.forEach(user => {
                html += `<tr>
                    <td>${user.id}</td>
                    <td>${user.username}</td>
                    <td>${user.email}</td>
                    <td>${user.role}</td>
                    <td>${user.is_active}</td>
                    <td>
                        <button class="admin-action-button admin-edit-user">Edit</button>
                    </td>
                </tr>`;
            });
            adminUserTableBody.innerHTML = html;
        } catch (err) {
            adminUserTableBody.innerHTML = '<tr><td colspan="6">Error loading users.</td></tr>';
        }
    }

    // --- ADMIN DYNAMIC LISTS MANAGEMENT ---
    async function loadAdminDynamicLists() {
        if (!dynamicListsContainer) return;
        dynamicListsContainer.innerHTML = '<div>Loading dynamic lists...</div>';
        try {
            const lists = await apiRequest("/admin/dynamic-lists/");
            if (!lists || lists.length === 0) {
                dynamicListsContainer.innerHTML = '<div>No dynamic lists found.</div>';
                return;
            }
            let html = '<div class="dynamic-lists-list">';
            lists.forEach(list => {
                html += `<div class="dynamic-list-block" style="background: #23272f; border: 2px solid #4f8cff; border-radius: 12px; margin-bottom: 32px; padding: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.10);">
                    <h4 style="color: #e5eaf2; margin-bottom: 10px;">${list.list_name}</h4>
                    <div id="dynamicListItems_${list.list_name}">Loading items...</div>
                    <button class="add-dynamic-list-item-btn action-button-primary" data-list="${list.list_name}" style="margin-top: 10px;">Add Item</button>
                </div>`;
            });
            html += '</div>';
            dynamicListsContainer.innerHTML = html;
            // Now load items for each list
            lists.forEach(list => loadDynamicListItems(list.list_name));
            // Attach add item event listeners
            document.querySelectorAll('.add-dynamic-list-item-btn').forEach(btn => {
                btn.addEventListener('click', function () {
                    const listName = btn.getAttribute('data-list');
                    showAddItemInput(listName);
                });
            });
        } catch (err) {
            console.error('Error loading dynamic lists:', err);
            dynamicListsContainer.innerHTML = '<div class="admin-error-message">Error loading dynamic lists.</div>';
        }
    }

    // --- ADMIN: LOAD DYNAMIC LIST ITEMS ---
    async function loadDynamicListItems(listName) {
        const itemsDiv = document.getElementById(`dynamicListItems_${listName}`);
        if (!itemsDiv) return;
        itemsDiv.innerHTML = '<div>Loading items...</div>';
        try {
            const items = await apiRequest(`/admin/dynamic-lists/${listName}/items`);
            if (!items || items.length === 0) {
                itemsDiv.innerHTML = '<div style="color:#aaa;">No items found.</div>';
                return;
            }
            let html = `<table class="dynamic-list-items" style="width:100%;border-collapse:collapse;">
            <thead><tr>
                <th style="color:#4f8cff;text-align:left;padding:0.75rem 0.5rem;">Label</th>
                <th style="color:#4f8cff;text-align:left;padding:0.75rem 0.5rem;">Value</th>
                <th style="color:#4f8cff;text-align:right;padding:0.75rem 0.5rem;">Actions</th>
            </tr></thead>
            <tbody>`;
            items.forEach(item => {
                html += `<tr style="background:#23272f;">
                <td style="color:#e5eaf2;padding:0.75rem 0.5rem;">${item.item_label} ${item.is_active ? '' : '<span style=\'color:#ff6b6b;font-size:0.9em;\'>(inactive)</span>'}</td>
                <td style="color:#888;padding:0.75rem 0.5rem;">${item.item_value}</td>
                <td style="text-align:right;padding:0.75rem 0.5rem;">
                    <button class="admin-action-button action-button-primary" data-id="${item.id}" data-list="${listName}" onclick="showEditItemInput('${listName}', ${item.id})">Edit</button>
                    <button class="admin-action-button action-button-danger" data-id="${item.id}" data-list="${listName}" onclick="deleteDynamicListItem('${listName}', ${item.id})">Delete</button>
                    <button class="admin-action-button action-button-secondary" data-id="${item.id}" data-list="${listName}" onclick="toggleDynamicListItemActive('${listName}', ${item.id}, ${item.is_active})">${item.is_active ? 'Deactivate' : 'Activate'}</button>
                </td>
            </tr>`;
            });
            html += '</tbody></table>';
            itemsDiv.innerHTML = html;
        } catch (err) {
            console.error('Error loading items for', listName, err);
            itemsDiv.innerHTML = '<div class="admin-error-message">Error loading items.</div>';
        }
    }

    // --- ADMIN: SHOW ADD ITEM INPUT ---
    window.showAddItemInput = function (listName) {
        const itemsDiv = document.getElementById(`dynamicListItems_${listName}`);
        if (!itemsDiv || itemsDiv.querySelector('.add-item-form')) return;
        const form = document.createElement('form');
        form.className = 'add-item-form';
        form.innerHTML = `<input type="text" placeholder="Item Value" style="padding:6px 10px;border-radius:4px;border:1px solid #bbb;width:30%;margin-right:8px;" required> <input type="text" placeholder="Item Label" style="padding:6px 10px;border-radius:4px;border:1px solid #bbb;width:30%;margin-right:8px;" required> <button type="submit" class="action-button-primary">Add</button> <button type="button" class="action-button-secondary cancel-add-item">Cancel</button>`;
        itemsDiv.prepend(form);
        form.querySelector('input').focus();
        form.addEventListener('submit', async function (e) {
            e.preventDefault();
            const value = form.querySelectorAll('input')[0].value.trim();
            const label = form.querySelectorAll('input')[1].value.trim();
            if (!value || !label) return;
            try {
                await apiRequest(`/admin/dynamic-lists/${listName}/items`, 'POST', { item_value: value, item_label: label, list_name: listName });
                displayMessage('Item added!', 'success');
                loadDynamicListItems(listName);
            } catch (err) {
                displayMessage('Failed to add item.', 'error');
            }
        });
        form.querySelector('.cancel-add-item').addEventListener('click', function () {
            form.remove();
        });
    };

    // --- ADMIN: SHOW EDIT ITEM INPUT ---
    window.showEditItemInput = function (listName, itemId) {
        const itemsDiv = document.getElementById(`dynamicListItems_${listName}`);
        if (!itemsDiv) return;
        const li = itemsDiv.querySelector(`button[data-id="${itemId}"]`).closest('li');
        if (!li || li.querySelector('.edit-item-form')) return;
        const currentValue = li.querySelector('span').textContent.match(/\(([^)]+)\)/)?.[1] || '';
        const currentLabel = li.querySelector('span').childNodes[0].textContent.trim();
        const form = document.createElement('form');
        form.className = 'edit-item-form';
        form.innerHTML = `<input type="text" value="${currentValue}" style="padding:6px 10px;border-radius:4px;border:1px solid #bbb;width:30%;margin-right:8px;" required> <input type="text" value="${currentLabel}" style="padding:6px 10px;border-radius:4px;border:1px solid #bbb;width:30%;margin-right:8px;" required> <button type="submit" class="action-button-primary">Save</button> <button type="button" class="action-button-secondary cancel-edit-item">Cancel</button>`;
        li.innerHTML = '';
        li.appendChild(form);
        form.querySelector('input').focus();
        form.addEventListener('submit', async function (e) {
            e.preventDefault();
            const value = form.querySelectorAll('input')[0].value.trim();
            const label = form.querySelectorAll('input')[1].value.trim();
            if (!value || !label) return;
            try {
                await apiRequest(`/admin/dynamic-lists/items/${itemId}`, 'PUT', { item_value: value, item_label: label });
                displayMessage('Item updated!', 'success');
                loadDynamicListItems(listName);
            } catch (err) {
                displayMessage('Failed to update item.', 'error');
            }
        });
        form.querySelector('.cancel-edit-item').addEventListener('click', function () {
            loadDynamicListItems(listName);
        });
    };

    // --- ADMIN: DELETE DYNAMIC LIST ITEM ---
    window.deleteDynamicListItem = async function (listName, itemId) {
        if (!confirm('Are you sure you want to delete this item?')) return;
        try {
            await apiRequest(`/admin/dynamic-lists/items/${itemId}`, 'DELETE');
            displayMessage('Item deleted!', 'success');
            loadDynamicListItems(listName);
        } catch (err) {
            displayMessage('Failed to delete item.', 'error');
        }
    };

    // --- ADMIN: TOGGLE ACTIVE/INACTIVE ---
    window.toggleDynamicListItemActive = async function (listName, itemId, isActive) {
        try {
            await apiRequest(`/admin/dynamic-lists/items/${itemId}`, 'PUT', { is_active: !isActive });
            displayMessage('Item status updated!', 'success');
            loadDynamicListItems(listName);
        } catch (err) {
            displayMessage('Failed to update item status.', 'error');
        }
    };

    // --- ADMIN PANEL FULL DARK THEME PATCH ---
    (function patchAdminPanelBackground() {
        const style = document.createElement('style');
        style.innerHTML = `
        body, html {
            background: #18191a !important;
        }
        #adminPanelContainer {
            background: #23272f !important;
            color: #e5eaf2 !important;
            border-radius: 16px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.12);
            padding: 32px 28px;
            margin-top: 32px;
        }
        #adminPanelContainer h2, #adminPanelContainer h3, #adminPanelContainer h4 {
            color: #e5eaf2 !important;
        }
        .admin-action-button, .action-button-primary, .action-button-secondary, .action-button-danger {
            border: none;
            border-radius: 4px;
            padding: 6px 16px;
            font-size: 1em;
            margin: 0 2px;
            cursor: pointer;
            transition: background 0.2s, color 0.2s;
        }
        .action-button-primary {
            background: #4f8cff;
            color: #fff;
        }
        .action-button-primary:hover {
            background: #2563eb;
        }
        .action-button-secondary {
            background: #e5eaf2;
            color: #23272f;
        }
        .action-button-secondary:hover {
            background: #cbd5e1;
        }
        .action-button-danger {
            background: #ff4d4f;
            color: #fff;
        }
        .action-button-danger:hover {
            background: #c00;
        }
        .dynamic-list-block {
            border: 2px solid #4f8cff !important;
            background: #23272f !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.10);
            margin-bottom: 32px;
        }
        .dynamic-list-items {
            width: 100%;
            border-collapse: collapse;
        }
        .dynamic-list-items th {
            color: #4f8cff;
            text-align: left;
            padding: 0.75rem 0.5rem;
        }
        .dynamic-list-items td {
            color: #e5eaf2;
            padding: 0.75rem 0.5rem;
            border-bottom: 1px solid #4f8cff;
        }
        .dynamic-list-items tr {
            background: #23272f;
        }
        #adminTabUserMgmt.active, #adminTabDynamicLists.active {
            background: #4f8cff;
            color: #fff;
            border-radius: 4px 4px 0 0;
        }
        #adminTabUserMgmt, #adminTabDynamicLists {
            background: #23272f;
            color: #e5eaf2;
            border-radius: 4px 4px 0 0;
            margin-right: 4px;
            padding: 8px 18px;
            font-weight: 500;
            cursor: pointer;
            border: none;
        }
        #adminTabUserMgmt:hover:not(.active), #adminTabDynamicLists:hover:not(.active) {
            background: #18191a;
        }
        `;
        document.head.appendChild(style);
    })();
});
