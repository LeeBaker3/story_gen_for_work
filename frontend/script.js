function resolveApiBaseUrl() {
    if (typeof window.resolveStoryGeneratorApiBaseUrl === "function") {
        return window.resolveStoryGeneratorApiBaseUrl();
    }

    if (
        window.location.hostname === "localhost" ||
        window.location.hostname === "127.0.0.1"
    ) {
        return "http://127.0.0.1:8000";
    }

    return window.location.origin.replace(/\/$/, "");
}

let API_BASE_URL = resolveApiBaseUrl();

function staticContentUrl(path) {
    if (!path) return "";
    const p = String(path).trim();
    if (!p) return "";
    if (p.startsWith("http://") || p.startsWith("https://")) return p;

    const base = API_BASE_URL.replace(/\/$/, "");
    if (p.startsWith("/static_content/")) return `${base}${p}`;
    if (p.startsWith("static_content/")) return `${base}/${p}`;
    return `${base}/static_content/${p.replace(/^\/+/, "")}`;
}
console.log("script.js file loaded and parsed by the browser.");

document.addEventListener("DOMContentLoaded", function () {
    // console.log('<<<<< SCRIPT_JS_VERSION_DEBUG_A - DOMContentLoaded >>>>>');
    // Variable declarations
    const navLoginSignup = document.getElementById("nav-login-signup");
    const navCreateStory = document.getElementById("nav-create-story");
    const navBrowseStories = document.getElementById("nav-browse-stories");
    const navCharacters = document.getElementById("nav-characters");
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
    const charactersSection = document.getElementById("characters-section");
    const adminPanelContainer = document.getElementById("adminPanelContainer"); // ENSURED DECLARATION
    const snackbarEl = document.getElementById("snackbar");

    // Forms
    const loginForm = document.getElementById("login-form");
    const signupForm = document.getElementById("signup-form");
    const forgotPasswordForm = document.getElementById("forgot-password-form");
    const resetPasswordForm = document.getElementById("reset-password-form");
    const storyCreationForm = document.getElementById("story-creation-form");

    // Auth view toggle links
    const showSignupLink = document.getElementById("show-signup-link");
    const showLoginLink = document.getElementById("show-login-link");
    const showForgotPasswordLink = document.getElementById("show-forgot-password-link");
    const showResetPasswordLink = document.getElementById("show-reset-password-link");
    const forgotPasswordBackToLoginLink = document.getElementById("forgot-password-back-to-login-link");
    const resetPasswordBackToLoginLink = document.getElementById("reset-password-back-to-login-link");
    const resetPasswordRequestLink = document.getElementById("reset-password-request-link");

    // Buttons
    const addCharacterButton = document.getElementById("add-character-button");
    const previewPdfButton = document.getElementById("preview-pdf-button");
    const exportPdfButton = document.getElementById("export-pdf-button");
    const generateStoryButton = document.getElementById("generate-story-button");
    const saveDraftButton = document.getElementById("save-draft-button");
    const pdfPreviewBackdrop = document.getElementById("pdf-preview-backdrop");
    const pdfPreviewModal = document.getElementById("pdf-preview-modal");
    const pdfPreviewCloseButton = document.getElementById("pdf-preview-close");
    const pdfPreviewStatus = document.getElementById("pdf-preview-status");
    const pdfPreviewFrameContainer = document.getElementById(
        "pdf-preview-frame-container",
    );
    const pdfPreviewFrame = document.getElementById("pdf-preview-frame");
    const pdfPreviewError = document.getElementById("pdf-preview-error");
    const pdfPreviewDownloadButton = document.getElementById(
        "pdf-preview-download",
    );

    // Generation Progress Elements
    const generationProgressArea = document.getElementById("generation-progress-area");
    const generationProgressBar = document.getElementById("generation-progress-bar");
    const generationStatusMessage = document.getElementById("generation-status-message");

    let authToken = localStorage.getItem("authToken");
    let pdfPreviewObjectUrl = null;
    let pdfPreviewFilename = "story.pdf";

    // State variables for draft editing
    let currentStoryId = null;
    let currentStoryIsDraft = false;
    const storyEditorState = {
        story: null,
        autosaveTimer: null,
        isSaving: false,
        saveRequested: false,
        historyPast: [],
        historyFuture: [],
        saveStatus: {
            state: "saved",
            message: "Saved",
            showRetry: false,
        },
        pageImageObjectUrls: new Map(),
        pageImageFetches: new Map(),
    };
    let nextStoryEditorTempPageId = -1;
    const STORY_EDITOR_DEFAULTS = {
        font_family: "storybook",
        font_size: 28,
        font_color: "#ffffff",
        text_position: "bottom-center",
        text_alignment: "center",
        text_box_opacity: 0.6,
        page_format: "letter",
        layout_mode: "full-page-overlay",
        readability_treatment: "",
    };
    const STORY_EDITOR_HISTORY_LIMIT = 50;
    const STORY_EDITOR_PAGE_OVERRIDE_FIELDS = [
        "text_position",
        "text_alignment",
        "font_size",
        "font_color",
        "text_box_opacity",
    ];
    const STORY_EDITOR_LAYOUT_OPTIONS = [
        { value: "full-page-overlay", label: "Full-page overlay" },
        { value: "horizontal-split", label: "Horizontal split" },
        { value: "vertical-split", label: "Vertical split" },
    ];
    const STORY_EDITOR_FONT_OPTIONS = [
        { value: "storybook", label: "Storybook" },
        { value: "classic", label: "Classic" },
        { value: "modern", label: "Modern" },
        { value: "handwritten", label: "Handwritten" },
        { value: "dyslexia-friendly", label: "Dyslexia-friendly" },
        { value: "large print", label: "Large print" },
    ];
    const STORY_EDITOR_TEXT_POSITIONS_V = ["top", "middle", "bottom"];
    const STORY_EDITOR_TEXT_POSITIONS_H = ["left", "center", "right"];
    const STORY_EDITOR_POSITION_LABELS_V = { top: "Top", middle: "Middle", bottom: "Bottom" };
    const STORY_EDITOR_POSITION_LABELS_H = { left: "Left", center: "Centre", right: "Right" };
    const STORY_EDITOR_TEXT_ALIGNMENT_OPTIONS = [
        { value: "left", label: "Left" },
        { value: "center", label: "Centre" },
        { value: "right", label: "Right" },
    ];
    const STORY_EDITOR_READABILITY_OPTIONS = [
        { value: "", label: "Default readability treatment" },
        { value: "High-contrast box", label: "High-contrast box" },
        { value: "Soft shadow", label: "Soft shadow" },
        { value: "Subtle gradient band", label: "Subtle gradient band" },
    ];
    const STORY_EDITOR_COLOR_SWATCHES = [
        "#ffffff",
        "#f8e16c",
        "#ffe1c6",
        "#d6f5ff",
        "#1f2937",
        "#8b1e3f",
    ];

    function normalizeLayoutMode(layoutMode) {
        const normalized = String(layoutMode || STORY_EDITOR_DEFAULTS.layout_mode)
            .trim()
            .toLowerCase();
        if (STORY_EDITOR_LAYOUT_OPTIONS.some((option) => option.value === normalized)) {
            return normalized;
        }
        return STORY_EDITOR_DEFAULTS.layout_mode;
    }

    function getLayoutModeLabel(layoutMode) {
        const normalized = normalizeLayoutMode(layoutMode);
        return STORY_EDITOR_LAYOUT_OPTIONS.find((option) => option.value === normalized)?.label
            || STORY_EDITOR_LAYOUT_OPTIONS[0].label;
    }

    function getLayoutModeDescription(layoutMode) {
        const normalized = normalizeLayoutMode(layoutMode);
        if (normalized === "horizontal-split") {
            return "Image panel above with text panel below";
        }
        if (normalized === "vertical-split") {
            return "Image panel on the left with text panel on the right";
        }
        return "Full-page image with editable text overlay";
    }

    function setPdfActionButtonsVisibility(isVisible) {
        const displayValue = isVisible ? "inline-block" : "none";
        [previewPdfButton, exportPdfButton].forEach((button) => {
            if (!button) {
                return;
            }
            button.style.display = displayValue;
        });
        if (exportPdfButton) {
            exportPdfButton.classList.add("action-button-info");
        }
    }

    function revokePdfPreviewUrl() {
        if (!pdfPreviewObjectUrl || !window.URL?.revokeObjectURL) {
            pdfPreviewObjectUrl = null;
            return;
        }
        try {
            window.URL.revokeObjectURL(pdfPreviewObjectUrl);
        } catch (error) {
            console.warn("[PDFPreview] Failed to revoke preview URL.", error);
        }
        pdfPreviewObjectUrl = null;
    }

    function closePdfPreviewModal() {
        if (pdfPreviewFrame) {
            pdfPreviewFrame.removeAttribute("src");
        }
        if (pdfPreviewModal) {
            pdfPreviewModal.classList.remove("open");
            pdfPreviewModal.setAttribute("aria-hidden", "true");
        }
        if (pdfPreviewBackdrop) {
            pdfPreviewBackdrop.classList.remove("open");
            pdfPreviewBackdrop.setAttribute("aria-hidden", "true");
        }
        revokePdfPreviewUrl();
    }

    function openPdfPreviewModal() {
        if (pdfPreviewModal) {
            pdfPreviewModal.classList.add("open");
            pdfPreviewModal.setAttribute("aria-hidden", "false");
        }
        if (pdfPreviewBackdrop) {
            pdfPreviewBackdrop.classList.add("open");
            pdfPreviewBackdrop.setAttribute("aria-hidden", "false");
        }
    }

    function setPdfPreviewLoadingState(message) {
        if (pdfPreviewStatus) {
            pdfPreviewStatus.hidden = false;
            pdfPreviewStatus.textContent = message;
        }
        if (pdfPreviewFrameContainer) {
            pdfPreviewFrameContainer.hidden = true;
        }
        if (pdfPreviewError) {
            pdfPreviewError.hidden = true;
            pdfPreviewError.textContent = "";
        }
        if (pdfPreviewDownloadButton) {
            pdfPreviewDownloadButton.disabled = true;
        }
    }

    function setPdfPreviewReadyState(objectUrl) {
        if (pdfPreviewStatus) {
            pdfPreviewStatus.hidden = false;
            pdfPreviewStatus.textContent = "PDF preview ready.";
        }
        if (pdfPreviewError) {
            pdfPreviewError.hidden = true;
            pdfPreviewError.textContent = "";
        }
        if (pdfPreviewFrameContainer) {
            pdfPreviewFrameContainer.hidden = false;
        }
        if (pdfPreviewFrame) {
            pdfPreviewFrame.src = objectUrl;
        }
        if (pdfPreviewDownloadButton) {
            pdfPreviewDownloadButton.disabled = false;
        }
    }

    function setPdfPreviewErrorState(message) {
        if (pdfPreviewStatus) {
            pdfPreviewStatus.hidden = true;
        }
        if (pdfPreviewFrameContainer) {
            pdfPreviewFrameContainer.hidden = true;
        }
        if (pdfPreviewFrame) {
            pdfPreviewFrame.removeAttribute("src");
        }
        if (pdfPreviewError) {
            pdfPreviewError.hidden = false;
            pdfPreviewError.textContent = message;
        }
        if (pdfPreviewDownloadButton) {
            pdfPreviewDownloadButton.disabled = true;
        }
    }

    function getPdfFilenameFromDisposition(contentDisposition) {
        let filename = "story.pdf";
        if (!contentDisposition) {
            return filename;
        }
        const filenameMatch = contentDisposition.match(/filename="?([^";]+)"?/i);
        if (filenameMatch && filenameMatch.length > 1) {
            filename = filenameMatch[1];
        }
        return filename;
    }

    function triggerPdfDownload(url, filename) {
        const anchor = document.createElement("a");
        anchor.style.display = "none";
        anchor.href = url;
        anchor.download = filename;
        document.body.appendChild(anchor);
        anchor.click();
        document.body.removeChild(anchor);
    }

    async function fetchStoryPdfBlob(disposition = "attachment") {
        const token = localStorage.getItem("authToken");
        const response = await fetch(
            `${API_BASE_URL}/api/v1/stories/${currentStoryId}/pdf?disposition=${encodeURIComponent(disposition)}`,
            {
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
        return {
            blob,
            filename: getPdfFilenameFromDisposition(
                response.headers.get("content-disposition"),
            ),
        };
    }

    // Content Areas
    const storyPreviewContent = document.getElementById("story-preview-content");
    const userStoriesList = document.getElementById("user-stories-list");

    // Admin panel specific elements
    const adminUserTableBody = document.getElementById("adminUserTableBody"); // ENSURED DECLARATION (MOVED HERE)

    let characterCount = 1;

    // --- Character Library State (Phase 3) ---
    const characterLibraryState = {
        page: 1,
        pageSize: 12,
        q: '',
        total: 0,
        items: [],
        selectedByIndex: new Map(),
        activeIndex: 1,
        restoreFocusEl: null,
        initialized: false,
    };

    function getLibraryEls() {
        const stepPanel = document.getElementById('step-1-characters');
        if (!stepPanel) return {};
        const elements = {
            chipBar: stepPanel.querySelector('#selected-characters-chipbar'),
            createFromCurrentBtn: stepPanel.querySelector('#character-create-from-current-btn'),
            modal: stepPanel.querySelector('#character-picker-modal'),
            backdrop: stepPanel.querySelector('#character-picker-backdrop'),
            close: stepPanel.querySelector('#character-picker-close'),
            title: stepPanel.querySelector('#character-picker-title'),
            search: stepPanel.querySelector('#character-search'),
            syncBtn: stepPanel.querySelector('#character-sync-btn'),
            list: stepPanel.querySelector('#character-list'),
            pagination: stepPanel.querySelector('#character-pagination'),
        };
        const modalContent = elements.modal?.querySelector('.modal-content');
        if (modalContent) {
            modalContent.classList.add('wizard-character-picker-modal-content');
        }
        if (elements.list) {
            elements.list.classList.add('character-grid');
            elements.list.setAttribute('aria-live', 'polite');
        }
        if (elements.pagination) {
            elements.pagination.classList.add('pagination-controls');
        }
        return elements;
    }

    function debounce(fn, wait = 350) {
        let t;
        return (...args) => {
            clearTimeout(t);
            t = setTimeout(() => fn(...args), wait);
        };
    }

    function getSelectedCharacterIds() {
        return Array.from(
            new Set(
                Array.from(characterLibraryState.selectedByIndex.values())
                    .map((item) => item?.id)
                    .filter((id) => Number.isInteger(id)),
            ),
        );
    }

    function getCharacterSelectionLabel(selection, index) {
        const name = String(selection?.name || '').trim();
        if (name) {
            return `Character ${index}: ${name}`;
        }
        if (Number.isInteger(selection?.id)) {
            return `Character ${index}: #${selection.id}`;
        }
        return `Character ${index}`;
    }

    function renderCharacterSelectionChips() {
        const { chipBar } = getLibraryEls();
        if (!chipBar) {
            return;
        }

        const selections = Array.from(characterLibraryState.selectedByIndex.entries())
            .sort((left, right) => left[0] - right[0]);
        if (selections.length === 0) {
            chipBar.innerHTML = '<em>No existing characters selected.</em>';
            return;
        }

        chipBar.innerHTML = selections.map(([index, selection]) => `
            <span class="selected-character-chip" data-character-index="${index}">
                <span class="selected-character-chip-label">${escapeHTML(getCharacterSelectionLabel(selection, index))}</span>
                <button type="button" class="remove-chip" data-character-index="${index}" aria-label="Remove existing character from story row ${index}">×</button>
            </span>
        `).join('');

        chipBar.querySelectorAll('.remove-chip').forEach((button) => {
            button.addEventListener('click', (event) => {
                const index = Number.parseInt(
                    event.currentTarget.getAttribute('data-character-index'),
                    10,
                );
                if (Number.isNaN(index)) {
                    return;
                }
                characterLibraryState.selectedByIndex.delete(index);
                renderCharacterSelectionChips();
                renderCharacterList();
            });
        });
    }

    function closeCharacterPickerModal(options = {}) {
        const { restoreFocus = true } = options;
        const { modal, backdrop } = getLibraryEls();
        if (modal) {
            modal.classList.remove('open');
            modal.setAttribute('aria-hidden', 'true');
        }
        if (backdrop) {
            backdrop.classList.remove('open');
            backdrop.setAttribute('aria-hidden', 'true');
        }
        if (restoreFocus && characterLibraryState.restoreFocusEl instanceof HTMLElement) {
            characterLibraryState.restoreFocusEl.focus();
        }
        characterLibraryState.restoreFocusEl = null;
    }

    async function openCharacterPickerModal(index, triggerButton) {
        const { modal, backdrop, title, search } = getLibraryEls();
        if (!modal || !backdrop) {
            return;
        }

        characterLibraryState.activeIndex = index;
        characterLibraryState.restoreFocusEl = triggerButton instanceof HTMLElement
            ? triggerButton
            : null;

        if (title) {
            title.textContent = `Choose Existing Character for Character ${index}`;
        }

        backdrop.classList.add('open');
        backdrop.setAttribute('aria-hidden', 'false');
        modal.classList.add('open');
        modal.setAttribute('aria-hidden', 'false');

        if (!characterLibraryState.initialized || characterLibraryState.items.length === 0) {
            await loadCharacterLibrary();
        } else {
            renderCharacterList();
            renderPagination();
        }

        search?.focus();
    }

    function syncCharacterDetailsDisclosure(toggleButton, detailsDiv) {
        if (!(toggleButton instanceof HTMLElement) || !(detailsDiv instanceof HTMLElement)) {
            return;
        }

        toggleButton.setAttribute("aria-controls", detailsDiv.id);
        const isExpanded = window.getComputedStyle(detailsDiv).display !== "none";
        toggleButton.setAttribute("aria-expanded", isExpanded ? "true" : "false");
        toggleButton.textContent = isExpanded ? "Hide Details" : "Show Details";
    }

    // Simple HTML escape to prevent accidental HTML injection in names
    function escapeHTML(str) {
        if (str == null) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    // Spinner Elements
    const spinner = document.getElementById("spinner");

    // --- DYNAMIC DROPDOWN POPULATION ---
    const DROPDOWN_RECOVERY_CONFIG = {
        "story-genre": {
            listName: "genres",
            label: "genres",
            statusId: "story-genre-recovery",
            retryId: "story-genre-retry",
        },
        "story-image-style": {
            listName: "image_styles",
            label: "image styles",
            statusId: "story-image-style-recovery",
            retryId: "story-image-style-retry",
        },
    };

    function syncDropdownRecoveryDescribedBy(
        selectElement,
        statusElement,
        isVisible,
    ) {
        if (!selectElement || !statusElement || !statusElement.id) {
            return;
        }

        if (selectElement.dataset.baseDescribedby === undefined) {
            selectElement.dataset.baseDescribedby =
                selectElement.getAttribute("aria-describedby") || "";
        }

        const describedByIds = selectElement.dataset.baseDescribedby
            .split(/\s+/)
            .filter(Boolean)
            .filter((id) => id !== statusElement.id);

        if (isVisible) {
            describedByIds.push(statusElement.id);
        }

        if (describedByIds.length > 0) {
            selectElement.setAttribute(
                "aria-describedby",
                describedByIds.join(" "),
            );
            return;
        }

        selectElement.removeAttribute("aria-describedby");
    }

    function getDropdownRecoveryElements(selectElementId) {
        const selectElement = document.getElementById(selectElementId);
        const config = DROPDOWN_RECOVERY_CONFIG[selectElementId] || {};

        if (!selectElement) {
            return { config, selectElement: null, statusElement: null, retryButton: null };
        }

        let statusElement = config.statusId
            ? document.getElementById(config.statusId)
            : null;

        if (!statusElement) {
            const generatedStatusId = `${selectElementId}-load-status`;
            statusElement = document.getElementById(generatedStatusId);
            if (!statusElement) {
                statusElement = document.createElement("div");
                statusElement.id = generatedStatusId;
                statusElement.className =
                    "inline-status inline-status--error dropdown-recovery-status";
                statusElement.setAttribute("role", "status");
                statusElement.setAttribute("aria-live", "polite");
                statusElement.setAttribute("aria-atomic", "true");
                statusElement.style.display = "none";
                selectElement.insertAdjacentElement("afterend", statusElement);
            }
        }

        const retryButton = config.retryId
            ? document.getElementById(config.retryId)
            : null;

        return { config, selectElement, statusElement, retryButton };
    }

    function setDropdownRecoveryState(
        selectElementId,
        { message = "", showRetry = false, isLoading = false } = {},
    ) {
        const { selectElement, statusElement, retryButton } =
            getDropdownRecoveryElements(selectElementId);

        if (!selectElement) {
            return;
        }

        if (isLoading) {
            selectElement.setAttribute("aria-busy", "true");
        } else {
            selectElement.removeAttribute("aria-busy");
        }

        if (statusElement) {
            const hasMessage = Boolean(message);
            statusElement.textContent = message;
            statusElement.style.display = hasMessage ? "block" : "none";
            syncDropdownRecoveryDescribedBy(
                selectElement,
                statusElement,
                hasMessage,
            );
        }

        if (retryButton) {
            retryButton.style.display = showRetry ? "inline-flex" : "none";
            retryButton.disabled = isLoading;
        }
    }

    function buildDropdownRecoveryMessage(listName) {
        const config = Object.values(DROPDOWN_RECOVERY_CONFIG).find(
            (item) => item.listName === listName,
        );
        const label = config?.label || listName.replace(/_/g, " ");
        return `We couldn't load ${label} right now. Try again.`;
    }

    function initializeDropdownRetryButtons() {
        Object.entries(DROPDOWN_RECOVERY_CONFIG).forEach(
            ([selectElementId, config]) => {
                const retryButton = config.retryId
                    ? document.getElementById(config.retryId)
                    : null;
                if (!retryButton || retryButton.dataset.dropdownRetryBound === "true") {
                    return;
                }

                retryButton.addEventListener("click", async () => {
                    await populateDropdown(selectElementId, config.listName);
                });
                retryButton.dataset.dropdownRetryBound = "true";
            },
        );
    }

    async function populateDropdown(selectElementId, listName) {
        const { config, selectElement } = getDropdownRecoveryElements(
            selectElementId,
        );
        if (!selectElement) {
            console.error(`[populateDropdown] Select element with ID '${selectElementId}' not found.`);
            return;
        }

        selectElement.disabled = true;
        selectElement.innerHTML = '<option value="">Loading...</option>';
        setDropdownRecoveryState(selectElementId, { isLoading: true });

        try {
            // Use the public endpoint for fetching active items
            const items = await apiRequest(`/api/v1/dynamic-lists/${listName}/active-items`);

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
            if (items && items.length > 0) {
                items.forEach(item => {
                    const option = document.createElement("option");
                    option.value = item.item_value;
                    option.textContent = item.item_label;
                    selectElement.appendChild(option);
                });
                selectElement.disabled = false;
                setDropdownRecoveryState(selectElementId);
            } else {
                console.warn(`[populateDropdown] No active items found for list: ${listName}`);
                selectElement.innerHTML = '<option value="">No options available</option>';
                selectElement.disabled = true;
                setDropdownRecoveryState(selectElementId, {
                    message: buildDropdownRecoveryMessage(listName),
                    showRetry: Boolean(config.retryId),
                });
            }
        } catch (error) {
            console.error(`[populateDropdown] Error populating ${listName}:`, error);
            selectElement.innerHTML = '<option value="">Error loading options</option>';
            selectElement.disabled = true;
            setDropdownRecoveryState(selectElementId, {
                message: buildDropdownRecoveryMessage(listName),
                showRetry: Boolean(config.retryId),
            });
        }
    }

    function populateAllDropdowns() {
        console.log("[populateAllDropdowns] Starting to populate all dropdowns.");
        // Phase 2 rename alignment: list names are now 'genres' and 'image_styles'
        populateDropdown("story-genre", "genres");
        populateDropdown("story-writing-style", "writing_styles");
        populateDropdown("story-image-style", "image_styles");
        populateDropdown("story-word-to-picture-ratio", "word_to_picture_ratio");
        populateDropdown("story-text-density", "text_density");
        // Populate wizard text position selects from static constants (V + H)
        (function populateWizardTextPosition() {
            const vSelect = document.getElementById("story-default-text-position-v");
            const hSelect = document.getElementById("story-default-text-position-h");
            if (!vSelect || !hSelect) return;
            vSelect.innerHTML = "";
            hSelect.innerHTML = "";
            const { v: defaultV, h: defaultH } = parseTextPosition(STORY_EDITOR_DEFAULTS.text_position);
            STORY_EDITOR_TEXT_POSITIONS_V.forEach((val) => {
                const opt = document.createElement("option");
                opt.value = val;
                opt.textContent = STORY_EDITOR_POSITION_LABELS_V[val];
                if (val === defaultV) opt.selected = true;
                vSelect.appendChild(opt);
            });
            STORY_EDITOR_TEXT_POSITIONS_H.forEach((val) => {
                const opt = document.createElement("option");
                opt.value = val;
                opt.textContent = STORY_EDITOR_POSITION_LABELS_H[val];
                if (val === defaultH) opt.selected = true;
                hSelect.appendChild(opt);
            });
        })();
        populateDropdown("story-default-font-family", "font_families").then(() => {
            const select = document.getElementById("story-default-font-family");
            if (select && !select.value) {
                select.value = STORY_EDITOR_DEFAULTS.font_family;
            }
        });
        // Populate first character gender if present
        populateDropdown("char-gender-1", "genders");
    }

    // Phase 3 Wizard navigation
    let wizardStep = 0; // 0: basics, 1: characters, 2: options, 3: review
    const stepPanels = [
        document.getElementById('step-0-basics'),
        document.getElementById('step-1-characters'),
        document.getElementById('step-2-options'),
        document.getElementById('step-3-review'),
    ];
    const stepDots = Array.from(document.querySelectorAll('#wizard-steps .wizard-step'));
    const btnPrev = document.getElementById('wizard-prev');
    const btnNext = document.getElementById('wizard-next');
    const WIZARD_STEP_COUNT = 4;

    const WIZARD_FIELD_ERROR_CONFIG = {
        'story-genre': { errorId: 'story-genre-error' },
        'story-outline': { errorId: 'story-outline-error' },
        'char-name-1': { errorId: 'main-characters-error' },
        'story-num-pages': { errorId: 'story-num-pages-error' },
        'story-image-style': { errorId: 'story-image-style-error' },
        'story-word-to-picture-ratio': {
            errorId: 'story-word-to-picture-ratio-error',
        },
        'story-text-density': { errorId: 'story-text-density-error' },
    };

    function getWizardValidationControl(controlOrId) {
        if (!controlOrId) return null;
        if (typeof controlOrId === 'string') {
            return document.getElementById(controlOrId);
        }
        return controlOrId;
    }

    function getWizardValidationMeta(controlOrId) {
        const control = getWizardValidationControl(controlOrId);
        if (!control) return {};
        const config = WIZARD_FIELD_ERROR_CONFIG[control.id] || {};
        const errorId = config.errorId || control.getAttribute('aria-describedby');
        const errorEl = errorId ? document.getElementById(errorId) : null;
        return { control, errorId, errorEl };
    }

    function setWizardFieldError(controlOrId, message) {
        const { control, errorId, errorEl } = getWizardValidationMeta(controlOrId);
        if (!control) return;

        if (errorId) {
            control.setAttribute('aria-describedby', errorId);
        }

        if (message) {
            control.setAttribute('aria-invalid', 'true');
            if (errorEl) {
                errorEl.textContent = message;
            }
            return;
        }

        control.removeAttribute('aria-invalid');
        if (errorEl) {
            errorEl.textContent = '';
        }
    }

    function clearWizardStepErrors(stepIdx) {
        if (stepIdx === 0) {
            setWizardFieldError('story-genre', '');
            setWizardFieldError('story-outline', '');
        } else if (stepIdx === 1) {
            document
                .querySelectorAll('#main-characters-fieldset .char-name')
                .forEach((input) => setWizardFieldError(input, ''));
            const sharedError = document.getElementById('main-characters-error');
            if (sharedError) {
                sharedError.textContent = '';
            }
        } else if (stepIdx === 2) {
            setWizardFieldError('story-num-pages', '');
            setWizardFieldError('story-image-style', '');
            setWizardFieldError('story-word-to-picture-ratio', '');
            setWizardFieldError('story-text-density', '');
        }
    }

    function focusFirstInvalidWizardControl(invalidControls) {
        const firstInvalid = invalidControls.find(Boolean);
        if (firstInvalid && typeof firstInvalid.focus === 'function') {
            firstInvalid.focus();
        }
    }

    function attachWizardValidationClearHandler(controlOrId, eventNames = ['input', 'change']) {
        const control = getWizardValidationControl(controlOrId);
        if (!control || control.dataset.inlineValidationBound === 'true') {
            return;
        }

        eventNames.forEach((eventName) => {
            control.addEventListener(eventName, () => {
                if (control.id.startsWith('char-name-')) {
                    const names = Array.from(
                        document.querySelectorAll('#main-characters-fieldset .char-name'),
                    );
                    const hasCharacterName = names.some((input) => input.value.trim());
                    if (hasCharacterName) {
                        names.forEach((input) => setWizardFieldError(input, ''));
                        const sharedError = document.getElementById('main-characters-error');
                        if (sharedError) {
                            sharedError.textContent = '';
                        }
                    }
                    updateStepUI();
                    return;
                }

                const isEmptyNumber =
                    control.id === 'story-num-pages' &&
                    !parseInt(control.value || '0', 10);
                updateStepUI();
                if (!control.value || isEmptyNumber) {
                    return;
                }
                setWizardFieldError(control, '');
            });
        });

        control.dataset.inlineValidationBound = 'true';
    }

    function initializeWizardValidationA11y() {
        Object.keys(WIZARD_FIELD_ERROR_CONFIG).forEach((id) => {
            attachWizardValidationClearHandler(id);
        });
        document
            .querySelectorAll('#main-characters-fieldset .char-name')
            .forEach((input) => attachWizardValidationClearHandler(input));
    }

    function isWizardStepSatisfied(stepIdx) {
        if (stepIdx === 0) {
            const genre = document.getElementById('story-genre')?.value;
            const outline = document.getElementById('story-outline')?.value?.trim();
            return Boolean(genre && outline);
        }

        if (stepIdx === 1) {
            const names = Array.from(
                document.querySelectorAll('#main-characters-fieldset .char-name'),
            )
                .map((input) => input.value.trim())
                .filter(Boolean);
            return names.length > 0;
        }

        if (stepIdx === 2) {
            const numPages = parseInt(
                document.getElementById('story-num-pages')?.value || '0',
                10,
            );
            const imageStyle = document.getElementById('story-image-style')?.value;
            const ratio = document.getElementById('story-word-to-picture-ratio')?.value;
            const density = document.getElementById('story-text-density')?.value;
            return Boolean(numPages && imageStyle && ratio && density);
        }

        return true;
    }

    function getWizardMaxReachableStep() {
        let maxReachableStep = 0;
        for (let stepIdx = 0; stepIdx < WIZARD_STEP_COUNT - 1; stepIdx += 1) {
            if (!isWizardStepSatisfied(stepIdx)) {
                break;
            }
            maxReachableStep = stepIdx + 1;
        }
        return maxReachableStep;
    }

    function updateStepUI() {
        const maxReachableStep = getWizardMaxReachableStep();
        if (wizardStep > maxReachableStep) {
            wizardStep = maxReachableStep;
        }
        // Show only current panel
        stepPanels.forEach((el, i) => {
            if (el) el.style.display = i === wizardStep ? 'block' : 'none';
        });
        // Step indicators
        stepDots.forEach((dot, i) => {
            const isReachable = i <= maxReachableStep;
            dot.classList.toggle('active', i === wizardStep);
            if (i === wizardStep) {
                dot.setAttribute('aria-current', 'step');
            } else {
                dot.removeAttribute('aria-current');
            }

            dot.disabled = !isReachable;

            if (!isReachable) {
                dot.setAttribute('aria-disabled', 'true');
            } else {
                dot.removeAttribute('aria-disabled');
            }
        });
        // Nav buttons
        if (btnPrev) btnPrev.disabled = wizardStep === 0;
        if (btnNext) btnNext.style.display = wizardStep < 3 ? 'inline-block' : 'none';
        if (generateStoryButton) generateStoryButton.style.display = wizardStep === 3 ? 'inline-block' : 'none';
        // If on review, populate summary
        if (wizardStep === 3) populateReview();
        // Ensure the wizard character picker is wired when the Characters step is active.
        if (wizardStep === 1) {
            initCharacterLibraryUI();
        } else {
            closeCharacterPickerModal({ restoreFocus: false });
        }
    }

    function validateStep(stepIdx) {
        // Minimal validation per step
        if (stepIdx === 0) {
            const genreInput = document.getElementById('story-genre');
            const outlineInput = document.getElementById('story-outline');
            const genre = genreInput?.value;
            const outline = outlineInput?.value?.trim();
            const invalidControls = [];

            clearWizardStepErrors(stepIdx);

            if (!genre) {
                setWizardFieldError(genreInput, 'Select a genre to continue.');
                invalidControls.push(genreInput);
            }
            if (!outline) {
                setWizardFieldError(
                    outlineInput,
                    'Enter a story outline to continue.',
                );
                invalidControls.push(outlineInput);
            }
            if (invalidControls.length > 0) {
                displayMessage('Please select a Genre and provide a Story Outline to continue.', 'warning');
                focusFirstInvalidWizardControl(invalidControls);
                return false;
            }
        } else if (stepIdx === 1) {
            // Require at least one character name or at least one selected existing character (future)
            const nameInputs = Array.from(
                document.querySelectorAll('#main-characters-fieldset .char-name'),
            );
            const names = nameInputs.map(i => i.value.trim()).filter(Boolean);
            clearWizardStepErrors(stepIdx);
            if (names.length === 0) {
                nameInputs.forEach((input) => {
                    setWizardFieldError(
                        input,
                        'Add at least one character name to continue.',
                    );
                });
                displayMessage('Add at least one character name.', 'warning');
                focusFirstInvalidWizardControl(nameInputs);
                return false;
            }
        } else if (stepIdx === 2) {
            const numPagesInput = document.getElementById('story-num-pages');
            const imageStyleInput = document.getElementById('story-image-style');
            const ratioInput = document.getElementById('story-word-to-picture-ratio');
            const densityInput = document.getElementById('story-text-density');
            const numPages = parseInt(numPagesInput?.value || '0', 10);
            const imgStyle = imageStyleInput?.value;
            const ratio = ratioInput?.value;
            const density = densityInput?.value;
            const invalidControls = [];

            clearWizardStepErrors(stepIdx);

            if (!numPages) {
                setWizardFieldError(
                    numPagesInput,
                    'Enter the number of pages to continue.',
                );
                invalidControls.push(numPagesInput);
            }
            if (!imgStyle) {
                setWizardFieldError(
                    imageStyleInput,
                    'Select an image style to continue.',
                );
                invalidControls.push(imageStyleInput);
            }
            if (!ratio) {
                setWizardFieldError(
                    ratioInput,
                    'Select a word-to-picture ratio to continue.',
                );
                invalidControls.push(ratioInput);
            }
            if (!density) {
                setWizardFieldError(
                    densityInput,
                    'Select a text density to continue.',
                );
                invalidControls.push(densityInput);
            }
            if (invalidControls.length > 0) {
                displayMessage('Please complete options: pages, image style, ratio, and text density.', 'warning');
                focusFirstInvalidWizardControl(invalidControls);
                return false;
            }
        }
        return true;
    }

    function goToStep(step) {
        if (step < 0 || step > 3) return;
        const maxReachableStep = getWizardMaxReachableStep();
        if (step > maxReachableStep) {
            return;
        }
        wizardStep = step;
        updateStepUI();
    }

    // --- Characters Main Menu (stub) ---
    const charactersPageState = { page: 1, pageSize: 12, q: '', total: 0, items: [] };

    async function fetchCharactersPage() {
        const params = new URLSearchParams({ page: String(charactersPageState.page), page_size: String(charactersPageState.pageSize) });
        if (charactersPageState.q) params.set('q', charactersPageState.q);
        const data = await apiRequest(`/api/v1/characters?${params.toString()}`);
        charactersPageState.total = data.total;
        charactersPageState.items = data.items || [];
        renderCharactersPageList();
        renderCharactersPagePagination();
    }

    function renderCharactersPageList() {
        const listEl = document.getElementById('characters-page-list');
        if (!listEl) return;
        listEl.innerHTML = '';
        charactersPageState.items.forEach(item => {
            const card = document.createElement('div');
            card.className = 'character-card';
            card.innerHTML = `
                <div class="thumb">${item.thumbnail_path ? `<img src="${staticContentUrl(item.thumbnail_path)}" alt="${escapeHTML(item.name)} thumbnail">` : '<div class="no-thumb">No image</div>'}</div>
                <div class="meta">
                  <div class="name" style="display:flex;align-items:center;justify-content:space-between;gap:8px;">
                    <span>${escapeHTML(item.name)}</span>
                    <span style="opacity:.7;font-size:.8em;">#${item.id}</span>
                  </div>
                  <div class="actions">
                    <button type="button" class="action-button-info" data-action="regen" data-id="${item.id}">Regenerate</button>
                    <button type="button" class="action-button-danger" data-action="delete" data-id="${item.id}">Delete</button>
                  </div>
                </div>
            `;
            listEl.appendChild(card);

            // Clicking the card (but not action buttons) opens edit modal
            card.addEventListener('click', async (e) => {
                const target = e.target;
                if (target.closest('button[data-action]')) return; // ignore action buttons
                // If a modal is open (or closing), ignore card clicks to avoid click-through reopen
                const modalEl = document.getElementById('char-modal');
                if (modalEl && modalEl.classList.contains('open')) return;
                if (document.body.dataset.charModalState === 'closing') return;
                await openCharacterModal(item.id);
            });
        });

        // Wire per-card actions
        listEl.querySelectorAll('button[data-action="regen"]').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const id = Number(e.currentTarget.getAttribute('data-id'));
                // Open modal to edit/regenerate instead of using prompts
                await openCharacterModal(id);
            });
        });
        listEl.querySelectorAll('button[data-action="delete"]').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const id = Number(e.currentTarget.getAttribute('data-id'));
                if (!confirm('Delete this character? This action cannot be undone.')) return;
                try {
                    await apiRequest(`/api/v1/characters/${id}`, 'DELETE');
                    await fetchCharactersPage();
                    displayMessage('Character deleted.', 'success');
                } catch (err) {
                    // apiRequest shows errors
                }
            });
        });
    }

    function renderCharactersPagePagination() {
        const pagEl = document.getElementById('characters-page-pagination');
        if (!pagEl) return;
        const totalPages = Math.max(1, Math.ceil((charactersPageState.total || 0) / charactersPageState.pageSize));
        const cur = charactersPageState.page;
        pagEl.innerHTML = `
                <button id="characters-page-prev" class="action-button-secondary" ${cur <= 1 ? 'disabled' : ''}>Prev</button>
            <span style="margin:0 8px;">Page ${cur} of ${totalPages}</span>
                <button id="characters-page-next" class="action-button-secondary" ${cur >= totalPages ? 'disabled' : ''}>Next</button>
        `;
        const prev = document.getElementById('characters-page-prev');
        const next = document.getElementById('characters-page-next');
        if (prev) prev.addEventListener('click', async () => {
            if (charactersPageState.page > 1) {
                charactersPageState.page -= 1;
                await fetchCharactersPage();
            }
        });
        if (next) next.addEventListener('click', async () => {
            const totalPages = Math.max(1, Math.ceil((charactersPageState.total || 0) / charactersPageState.pageSize));
            if (charactersPageState.page < totalPages) {
                charactersPageState.page += 1;
                await fetchCharactersPage();
            }
        });
    }

    function showCharactersPage() {
        hideAllSections();
        if (charactersSection) {
            charactersSection.style.display = 'block';
            fetchCharactersPage();
        }
    }

    // --- Characters Page: Edit/Duplicate Modal ---
    // One-time wire of modal buttons to ensure they respond
    const charWizardState = {
        step: 0,
        characterId: null,
        photoFile: null,
        photoPreviewUrl: null,
        generatedImagePath: null,
    };

    function getCharWizardEls() {
        const modal = document.getElementById('char-modal');
        return {
            modal,
            backdrop: document.getElementById('char-modal-backdrop'),
            wizard: document.getElementById('char-modal-wizard'),
            editForm: document.getElementById('char-modal-edit-form'),
            modalActions: modal?.querySelector('.modal-actions'),
            steps: Array.from(document.querySelectorAll('#char-wizard-steps .wizard-step')),
            panels: [
                document.getElementById('char-wizard-panel-0'),
                document.getElementById('char-wizard-panel-1'),
                document.getElementById('char-wizard-panel-2'),
                document.getElementById('char-wizard-panel-3'),
            ],
            prev: document.getElementById('char-wizard-prev'),
            next: document.getElementById('char-wizard-next'),
            name: document.getElementById('char-wizard-name'),
            photo: document.getElementById('char-wizard-photo'),
            photoPreview: document.getElementById('char-wizard-photo-preview'),
            desc: document.getElementById('char-wizard-desc'),
            style: document.getElementById('char-wizard-style'),
            generatedImage: document.getElementById('char-wizard-generated-image'),
            status: document.getElementById('char-modal-status'),
        };
    }

    function setCharWizardMode(enabled) {
        const { modal, wizard, editForm, modalActions } = getCharWizardEls();
        if (!modal) return;
        modal.dataset.mode = enabled ? 'wizard' : 'edit';
        if (wizard) wizard.style.display = enabled ? '' : 'none';
        if (editForm) editForm.style.display = enabled ? 'none' : '';
        if (modalActions) modalActions.style.display = enabled ? 'none' : '';
    }

    function resetCharWizardState() {
        const { name, photo, photoPreview, desc, style, generatedImage, status } = getCharWizardEls();
        if (charWizardState.photoPreviewUrl && window.URL?.revokeObjectURL) {
            try { window.URL.revokeObjectURL(charWizardState.photoPreviewUrl); } catch { }
        }
        charWizardState.step = 0;
        charWizardState.characterId = null;
        charWizardState.photoFile = null;
        charWizardState.photoPreviewUrl = null;
        charWizardState.generatedImagePath = null;
        if (name) name.value = '';
        if (desc) desc.value = '';
        if (style) style.value = '';
        if (photo) photo.value = '';
        if (photoPreview) {
            photoPreview.src = '';
            photoPreview.style.display = 'none';
        }
        if (generatedImage) {
            generatedImage.src = '';
            generatedImage.style.display = 'none';
        }
        if (status) {
            status.textContent = '';
            status.className = 'inline-status';
            status.style.display = 'none';
        }
    }

    function setWizardStatus(msg, type = 'info') {
        const { status } = getCharWizardEls();
        if (!status) return;
        status.textContent = String(msg);
        status.className = `inline-status inline-status--${type}`;
        status.style.display = '';
    }

    function setWizardBusy(isBusy, msg = '') {
        const { next, prev, status } = getCharWizardEls();
        if (next) next.disabled = isBusy;
        if (prev) prev.disabled = isBusy;
        const region = status?.closest('[data-status-region]');
        if (region) region.setAttribute('aria-busy', isBusy ? 'true' : 'false');
        if (isBusy && msg) setWizardStatus(msg, 'info');
    }

    function updateCharWizardUI() {
        const { panels, steps, prev, next, modal } = getCharWizardEls();
        panels.forEach((el, i) => {
            if (el) el.style.display = i === charWizardState.step ? 'block' : 'none';
        });
        steps.forEach((dot, i) => {
            dot.classList.toggle('active', i === charWizardState.step);
            dot.setAttribute('aria-current', i === charWizardState.step ? 'step' : 'false');
        });
        if (prev) prev.disabled = charWizardState.step === 0;
        if (next) {
            if (charWizardState.step === 0) next.textContent = 'Create';
            else if (charWizardState.step === 1) next.textContent = 'Upload';
            else if (charWizardState.step === 2) next.textContent = 'Next';
            else next.textContent = 'Generate';
        }
        // Title
        const title = document.getElementById('char-modal-title');
        if (title) {
            const id = modal?.getAttribute('data-id');
            title.textContent = id ? `New Character #${id}` : 'New Character';
        }
    }

    async function charWizardNext() {
        const { modal, name, photo, desc, style, generatedImage } = getCharWizardEls();
        if (!modal) return;

        // Step 1: create character
        if (charWizardState.step === 0) {
            const n = (name?.value || '').trim();
            if (!n) {
                setWizardStatus('Please enter a character name.', 'warning');
                return;
            }
            setWizardBusy(true, 'Creating character…');
            try {
                const created = await apiRequest('/api/v1/characters/', 'POST', {
                    name: n,
                    generate_image: false,
                });
                const id = created?.id;
                if (!id) throw new Error('Missing character id');
                charWizardState.characterId = Number(id);
                modal.setAttribute('data-id', String(id));
                setWizardStatus('Character created. Upload a photo next.', 'success');
                charWizardState.step = 1;
                updateCharWizardUI();
            } catch (e) {
                setWizardStatus('Failed to create character.', 'error');
            } finally {
                setWizardBusy(false);
            }
            return;
        }

        const id = charWizardState.characterId || Number(modal.getAttribute('data-id'));
        if (!id) {
            setWizardStatus('Missing character id. Please start over.', 'error');
            return;
        }

        // Step 2: upload photo
        if (charWizardState.step === 1) {
            const file = photo?.files?.[0] || charWizardState.photoFile;
            if (!file) {
                setWizardStatus('Please choose a photo to upload.', 'warning');
                return;
            }
            setWizardBusy(true, 'Uploading photo…');
            try {
                const fd = new FormData();
                fd.append('photo', file);
                await apiRequest(`/api/v1/characters/${id}/photo`, 'POST', fd, true);
                setWizardStatus('Photo uploaded. Add a description next.', 'success');
                charWizardState.step = 2;
                updateCharWizardUI();
            } catch (e) {
                setWizardStatus('Failed to upload photo.', 'error');
            } finally {
                setWizardBusy(false);
            }
            return;
        }

        // Step 3: describe
        if (charWizardState.step === 2) {
            const d = (desc?.value || '').trim();
            const s = (style?.value || '').trim() || null;
            if (!d) {
                setWizardStatus('Please add a description.', 'warning');
                return;
            }
            setWizardBusy(true, 'Saving description…');
            try {
                await apiRequest(`/api/v1/characters/${id}`, 'PUT', {
                    description: d,
                    image_style: s,
                });
                setWizardStatus('Description saved. Generate the reference image.', 'success');
                charWizardState.step = 3;
                updateCharWizardUI();
            } catch (e) {
                setWizardStatus('Failed to save description.', 'error');
            } finally {
                setWizardBusy(false);
            }
            return;
        }

        // Step 4: generate
        if (charWizardState.step === 3) {
            const d = (desc?.value || '').trim();
            const s = (style?.value || '').trim() || null;
            if (!d) {
                setWizardStatus('Please add a description before generating.', 'warning');
                return;
            }
            setWizardBusy(true, 'Generating reference image…');
            try {
                const result = await apiRequest(`/api/v1/characters/${id}/generate-from-photo`, 'POST', {
                    description: d,
                    image_style: s,
                });
                const path = result?.current_image?.file_path;
                if (generatedImage && path) {
                    generatedImage.src = staticContentUrl(path);
                    generatedImage.style.display = '';
                }
                setWizardStatus('Reference image generated.', 'success');
            } catch (e) {
                setWizardStatus('Failed to generate reference image.', 'error');
            } finally {
                setWizardBusy(false);
            }
        }
    }

    function charWizardPrev() {
        if (charWizardState.step <= 0) return;
        charWizardState.step -= 1;
        updateCharWizardUI();
    }

    (function initCharactersModalWiring() {
        const backdrop = document.getElementById('char-modal-backdrop');
        const modal = document.getElementById('char-modal');
        const closeBtn = document.getElementById('char-modal-close');
        const saveBtn = document.getElementById('char-modal-save');
        const dupBtn = document.getElementById('char-modal-duplicate');
        const regenBtn = document.getElementById('char-modal-regenerate');
        if (!modal || !backdrop) return;

        function closeModal() {
            document.body.dataset.charModalState = 'closing';
            setTimeout(() => {
                backdrop.classList.remove('open');
                modal.classList.remove('open');
                // Clean up wizard state if it was active
                if (modal.dataset.mode === 'wizard') {
                    resetCharWizardState();
                    setCharWizardMode(false);
                }
                delete modal.dataset.mode;
                delete document.body.dataset.charModalState;
            }, 50);
        }

        if (closeBtn) closeBtn.addEventListener('click', (ev) => { ev.preventDefault(); ev.stopPropagation(); closeModal(); });
        backdrop?.addEventListener('click', (ev) => { ev.stopPropagation(); closeModal(); });
        modal?.addEventListener('click', (ev) => {
            // Clicks directly on modal empty area (if any) should close
            if (ev.target === modal) { ev.stopPropagation(); closeModal(); }
        });
        window.addEventListener('keydown', (ev) => { if (ev.key === 'Escape' && modal.classList.contains('open')) closeModal(); }, true);

        // Wizard navigation wiring (optional: tests may mount without these elements)
        const wizardPrev = document.getElementById('char-wizard-prev');
        const wizardNext = document.getElementById('char-wizard-next');
        const wizardPhoto = document.getElementById('char-wizard-photo');
        if (wizardPrev) wizardPrev.addEventListener('click', (ev) => { ev.preventDefault(); ev.stopPropagation(); charWizardPrev(); });
        if (wizardNext) wizardNext.addEventListener('click', async (ev) => { ev.preventDefault(); ev.stopPropagation(); await charWizardNext(); });
        if (wizardPhoto) {
            wizardPhoto.addEventListener('change', () => {
                const { photoPreview } = getCharWizardEls();
                const f = wizardPhoto.files?.[0] || null;
                charWizardState.photoFile = f;
                if (!photoPreview) return;
                if (charWizardState.photoPreviewUrl && window.URL?.revokeObjectURL) {
                    try { window.URL.revokeObjectURL(charWizardState.photoPreviewUrl); } catch { }
                }
                if (f && window.URL?.createObjectURL) {
                    charWizardState.photoPreviewUrl = window.URL.createObjectURL(f);
                    photoPreview.src = charWizardState.photoPreviewUrl;
                    photoPreview.style.display = '';
                } else {
                    photoPreview.src = '';
                    photoPreview.style.display = 'none';
                }
            });
        }

        async function collectModalPayload() {
            const nameEl = document.getElementById('modal-char-name');
            const ageEl = document.getElementById('modal-char-age');
            const genderEl = document.getElementById('modal-char-gender');
            const descEl = document.getElementById('modal-char-desc');
            const clothEl = document.getElementById('modal-char-clothing');
            const traitsEl = document.getElementById('modal-char-traits');
            const styleEl = document.getElementById('modal-char-style');
            return {
                name: nameEl?.value?.trim() || '',
                age: ageEl?.value ? Number(ageEl.value) : null,
                gender: genderEl?.value || null,
                description: descEl?.value?.trim() || null,
                clothing_style: clothEl?.value?.trim() || null,
                key_traits: traitsEl?.value?.trim() || null,
                image_style: styleEl?.value || null,
            };
        }

        // Save uses data-id on modal root to know which character to update
        if (saveBtn) saveBtn.addEventListener('click', async (ev) => {
            ev.preventDefault(); ev.stopPropagation();
            const modalEl = document.getElementById('char-modal');
            const regenBtnEl = document.getElementById('char-modal-regenerate');
            const statusEl = document.getElementById('char-modal-status');
            const actionsEl = modalEl?.querySelector('.modal-actions');
            const actionButtons = actionsEl ? Array.from(actionsEl.querySelectorAll('button')) : [];
            function setBusy(msg) {
                if (statusEl) {
                    statusEl.innerHTML = `<span class="spinner" aria-hidden="true"></span>${String(msg)}`;
                    statusEl.className = 'inline-status inline-status--info';
                    statusEl.style.display = '';
                    try { statusEl.scrollIntoView({ block: 'nearest', behavior: 'smooth' }); } catch { }
                }
                const region = statusEl?.closest('[data-status-region]');
                if (region) region.setAttribute('aria-busy', 'true');
                actionButtons.forEach(b => b.disabled = true);
            }
            function setDone(msg, type = 'success') {
                if (statusEl) {
                    statusEl.textContent = String(msg);
                    statusEl.className = `inline-status inline-status--${type}`;
                    statusEl.style.display = '';
                }
                const region = statusEl?.closest('[data-status-region]');
                if (region) region.setAttribute('aria-busy', 'false');
                actionButtons.forEach(b => b.disabled = false);
            }
            try {
                const id = document.getElementById('char-modal')?.getAttribute('data-id');
                const payload = await collectModalPayload();

                if (id) {
                    setBusy('Saving changes…');
                    await apiRequest(`/api/v1/characters/${id}`, 'PUT', payload);
                    await fetchCharactersPage();
                    setDone('Character updated.', 'success');
                    if (regenBtnEl) regenBtnEl.disabled = false;
                    // Keep modal open for further edits
                } else {
                    setBusy('Creating character…');
                    const created = await apiRequest('/api/v1/characters/', 'POST', {
                        ...payload,
                        generate_image: false,
                    });
                    await fetchCharactersPage();
                    setDone('Character created.', 'success');
                    if (created?.id) {
                        // Switch modal into edit mode for the newly created character
                        await openCharacterModal(created.id);
                    }
                }
            } catch (e) {
                setDone('Failed to save changes.', 'error');
            }
        });
        if (dupBtn) dupBtn.addEventListener('click', async (ev) => {
            ev.preventDefault(); ev.stopPropagation();
            const modalEl = document.getElementById('char-modal');
            const statusEl = document.getElementById('char-modal-status');
            const actionsEl = modalEl?.querySelector('.modal-actions');
            const actionButtons = actionsEl ? Array.from(actionsEl.querySelectorAll('button')) : [];
            function setBusy(msg) {
                if (statusEl) {
                    statusEl.innerHTML = `<span class=\"spinner\" aria-hidden=\"true\"></span>${String(msg)}`;
                    statusEl.className = 'inline-status inline-status--info';
                    statusEl.style.display = '';
                    try { statusEl.scrollIntoView({ block: 'nearest', behavior: 'smooth' }); } catch { }
                }
                const region = statusEl?.closest('[data-status-region]');
                if (region) region.setAttribute('aria-busy', 'true');
                actionButtons.forEach(b => b.disabled = true);
            }
            function setDone(msg, type = 'success') {
                if (statusEl) {
                    statusEl.textContent = String(msg);
                    statusEl.className = `inline-status inline-status--${type}`;
                    statusEl.style.display = '';
                }
                const region = statusEl?.closest('[data-status-region]');
                if (region) region.setAttribute('aria-busy', 'false');
                actionButtons.forEach(b => b.disabled = false);
            }
            try {
                setBusy('Creating a new character…');
                const payload = await collectModalPayload();
                await apiRequest('/api/v1/characters/', 'POST', { ...payload, generate_image: false });
                await fetchCharactersPage();
                setDone('Character created.', 'success');
            } catch (e) {
                setDone('Failed to create character.', 'error');
            }
        });

        if (regenBtn) regenBtn.addEventListener('click', async (ev) => {
            ev.preventDefault(); ev.stopPropagation();
            const id = document.getElementById('char-modal')?.getAttribute('data-id');
            if (!id) return;
            try {
                const payload = await collectModalPayload();
                // Inline modal status + disable controls during regeneration
                const modalEl = document.getElementById('char-modal');
                const statusEl = document.getElementById('char-modal-status');
                const imgEl = document.getElementById('char-modal-image');
                const actionsEl = modalEl?.querySelector('.modal-actions');
                const actionButtons = actionsEl ? Array.from(actionsEl.querySelectorAll('button')) : [];

                function setModalBusy(msg) {
                    if (statusEl) {
                        statusEl.innerHTML = `<span class="spinner" aria-hidden="true"></span>${String(msg)}`;
                        statusEl.className = 'inline-status inline-status--info';
                        statusEl.style.display = '';
                        // Ensure the status is visible near the buttons
                        try { statusEl.scrollIntoView({ block: 'nearest', behavior: 'smooth' }); } catch { }
                    }
                    const region = statusEl?.closest('[data-status-region]');
                    if (region) region.setAttribute('aria-busy', 'true');
                    actionButtons.forEach(b => b.disabled = true);
                }
                function setModalDone(msg, type = 'success') {
                    if (statusEl) {
                        statusEl.textContent = String(msg);
                        statusEl.className = `inline-status inline-status--${type}`;
                        statusEl.style.display = '';
                        try { statusEl.scrollIntoView({ block: 'nearest', behavior: 'smooth' }); } catch { }
                    }
                    const region = statusEl?.closest('[data-status-region]');
                    if (region) region.setAttribute('aria-busy', 'false');
                    actionButtons.forEach(b => b.disabled = false);
                }

                setModalBusy('Regenerating image… This may take a moment.');
                await apiRequest(`/api/v1/characters/${id}/regenerate-image`, 'POST', {
                    description: payload.description || undefined,
                    image_style: payload.image_style || undefined
                });
                // Refresh list/grid
                await fetchCharactersPage();
                // Update modal preview image
                try {
                    const detail = await apiRequest(`/api/v1/characters/${id}`);
                    if (imgEl) {
                        const path = detail?.current_image?.file_path || detail?.thumbnail_path || null;
                        if (path) {
                            imgEl.src = staticContentUrl(path);
                            imgEl.style.display = '';
                        }
                    }
                } catch { }
                setModalDone('Character image regenerated.', 'success');
            } catch (e) {
                // Inline error + re-enable buttons; avoid snackbar behind modal
                const modalEl = document.getElementById('char-modal');
                const statusEl = document.getElementById('char-modal-status');
                const actionsEl = modalEl?.querySelector('.modal-actions');
                const actionButtons = actionsEl ? Array.from(actionsEl.querySelectorAll('button')) : [];
                if (statusEl) {
                    statusEl.textContent = 'Failed to regenerate image.';
                    statusEl.className = 'inline-status inline-status--error';
                    statusEl.style.display = '';
                    const region = statusEl.closest('[data-status-region]');
                    if (region) region.setAttribute('aria-busy', 'false');
                }
                actionButtons.forEach(b => b.disabled = false);
            }
        });
    })();
    async function openCharacterModal(id) {
        setCharWizardMode(false);
        let detail;
        try {
            detail = await apiRequest(`/api/v1/characters/${id}`);
        } catch (e) {
            displayMessage('Failed to load character.', 'error');
            return;
        }
        const backdrop = document.getElementById('char-modal-backdrop');
        const modal = document.getElementById('char-modal');
        if (!modal || !backdrop) return;
        // Reset inline status on open
        const inlineStatus = document.getElementById('char-modal-status');
        if (inlineStatus) {
            inlineStatus.textContent = '';
            inlineStatus.style.display = 'none';
            inlineStatus.className = 'inline-status';
        }
        // Ensure wizard state is reset if previously used
        resetCharWizardState();
        modal.setAttribute('data-id', String(detail.id));
        const title = document.getElementById('char-modal-title');
        const nameEl = document.getElementById('modal-char-name');
        const ageEl = document.getElementById('modal-char-age');
        const genderEl = document.getElementById('modal-char-gender');
        const descEl = document.getElementById('modal-char-desc');
        const clothEl = document.getElementById('modal-char-clothing');
        const traitsEl = document.getElementById('modal-char-traits');
        const styleEl = document.getElementById('modal-char-style');
        const imgEl = document.getElementById('char-modal-image');

        if (title) title.textContent = `Edit Character #${detail.id}`;
        if (nameEl) nameEl.value = detail.name || '';
        if (ageEl) ageEl.value = detail.age != null ? detail.age : '';
        // Populate genders then preselect current value if present
        try {
            await populateDropdown('modal-char-gender', 'genders');
            if (genderEl && detail.gender) {
                const options = Array.from(genderEl.options).map(o => o.value.toLowerCase());
                const current = String(detail.gender).toLowerCase();
                if (options.includes(current)) {
                    genderEl.value = Array.from(genderEl.options).find(o => o.value.toLowerCase() === current).value;
                } else {
                    const opt = document.createElement('option');
                    opt.value = detail.gender;
                    opt.textContent = detail.gender;
                    genderEl.appendChild(opt);
                    genderEl.value = detail.gender;
                }
            }
        } catch (e) {
            if (genderEl) genderEl.value = detail.gender || '';
        }
        if (descEl) descEl.value = detail.description || detail.physical_appearance || '';
        if (clothEl) clothEl.value = detail.clothing_style || '';
        if (traitsEl) traitsEl.value = detail.key_traits || '';
        // Populate image styles from dynamic list, then select current value if present
        try {
            await populateDropdown('modal-char-style', 'image_styles');
            if (styleEl && detail.image_style) {
                const options = Array.from(styleEl.options).map(o => o.value.toLowerCase());
                const current = String(detail.image_style).toLowerCase();
                if (options.includes(current)) {
                    styleEl.value = Array.from(styleEl.options).find(o => o.value.toLowerCase() === current).value;
                } else {
                    // ensure the existing value is selectable if not in list
                    const opt = document.createElement('option');
                    opt.value = detail.image_style;
                    opt.textContent = detail.image_style;
                    styleEl.appendChild(opt);
                    styleEl.value = detail.image_style;
                }
            }
        } catch (e) {
            // If lists fail, keep whatever is there
        }

        // Show current image preview if available
        if (imgEl) {
            const path = detail?.current_image?.file_path || detail?.thumbnail_path || null;
            if (path) {
                imgEl.src = staticContentUrl(path);
                imgEl.style.display = '';
            } else {
                imgEl.style.display = 'none';
            }
        }

        function closeModal() {
            // Mark as closing to avoid click-through triggering card clicks beneath
            document.body.dataset.charModalState = 'closing';
            // Small timeout lets current click sequence finish before removing overlay
            setTimeout(() => {
                backdrop.classList.remove('open');
                modal.classList.remove('open');
                delete document.body.dataset.charModalState;
            }, 50);
        }

        // Opening the modal: add open classes
        backdrop.classList.add('open');
        modal.classList.add('open');
    }

    async function openNewCharacterModal() {
        const backdrop = document.getElementById('char-modal-backdrop');
        const modal = document.getElementById('char-modal');
        if (!modal || !backdrop) return;

        // Enter wizard mode
        resetCharWizardState();
        setCharWizardMode(true);

        // Reset inline status on open
        const inlineStatus = document.getElementById('char-modal-status');
        if (inlineStatus) {
            inlineStatus.textContent = '';
            inlineStatus.style.display = 'none';
            inlineStatus.className = 'inline-status';
        }

        modal.removeAttribute('data-id');
        // Populate image styles for wizard step 3 (best effort)
        try { await populateDropdown('char-wizard-style', 'image_styles'); } catch (e) { /* ignore */ }
        charWizardState.step = 0;
        updateCharWizardUI();

        backdrop.classList.add('open');
        modal.classList.add('open');
    }

    function hideAllSections() {
        [authSection, storyCreationSection, storyPreviewSection, browseStoriesSection, charactersSection].forEach(sec => {
            if (sec) sec.style.display = 'none';
        });
    }

    if (navCharacters) {
        navCharacters.addEventListener('click', () => {
            showCharactersPage();
        });
    }

    // Characters page: New Character
    const charactersPageNewBtn = document.getElementById('characters-page-new');
    if (charactersPageNewBtn) {
        charactersPageNewBtn.addEventListener('click', async () => {
            await openNewCharacterModal();
        });
    }

    const charactersPageSearch = document.getElementById('characters-page-search');
    if (charactersPageSearch) {
        charactersPageSearch.addEventListener('input', debounce(() => {
            charactersPageState.q = charactersPageSearch.value.trim();
            charactersPageState.page = 1;
            fetchCharactersPage();
        }, 300));
    }

    // Characters page: Sync from stories
    const charactersPageSyncBtn = document.getElementById('characters-page-sync');
    if (charactersPageSyncBtn) {
        charactersPageSyncBtn.addEventListener('click', async () => {
            try {
                displayMessage('Syncing characters from your stories...', 'info');
                await apiRequest('/stories/backfill-characters', 'POST', { include_drafts: true });
                await fetchCharactersPage();
                displayMessage('Characters synced from stories.', 'success');
            } catch (e) {
                // apiRequest shows error
            }
        });
    }

    // Characters page: Import from JSON
    const charactersPageImportBtn = document.getElementById('characters-page-import');
    if (charactersPageImportBtn) {
        charactersPageImportBtn.addEventListener('click', async () => {
            const input = document.createElement('input');
            input.type = 'file';
            input.accept = 'application/json';
            input.onchange = async () => {
                const file = input.files && input.files[0];
                if (!file) return;
                try {
                    const text = await file.text();
                    let data;
                    try { data = JSON.parse(text); } catch (e) { throw new Error('Invalid JSON file.'); }
                    const items = Array.isArray(data) ? data : [data];
                    if (!items.length) throw new Error('No characters found in JSON.');
                    let ok = 0, fail = 0;
                    displayMessage('Importing characters...', 'info');
                    for (const raw of items) {
                        try {
                            const payload = {
                                name: raw.name || '',
                                description: raw.description || raw.physical_appearance || '',
                                age: typeof raw.age === 'number' ? raw.age : (raw.age ? parseInt(raw.age, 10) : undefined),
                                gender: raw.gender || '',
                                clothing_style: raw.clothing_style || '',
                                key_traits: raw.key_traits || raw.traits || '',
                                image_style: raw.image_style || undefined,
                                generate_image: !!raw.generate_image,
                            };
                            if (!payload.name) { fail++; continue; }
                            await apiRequest('/api/v1/characters/', 'POST', payload);
                            ok++;
                        } catch (e) {
                            fail++;
                        }
                    }
                    await fetchCharactersPage();
                    displayMessage(`Import complete. ${ok} saved, ${fail} failed.`, ok > 0 && fail === 0 ? 'success' : (ok > 0 ? 'warning' : 'error'));
                } catch (err) {
                    displayMessage(err.message || 'Import failed.', 'error');
                }
            };
            input.click();
        });
    }

    function populateReview() {
        const review = document.getElementById('review-container');
        if (!review) return;
        const data = getStoryDataFromForm();
        const editorSettings = data.editor_settings || STORY_EDITOR_DEFAULTS;
        // Simple summary
        review.innerHTML = '';
        const s = document.createElement('div');
        s.className = 'review-summary';
        const characters = data.main_characters?.map(c => c.name).filter(Boolean) || [];
        const reusedCount = Array.isArray(data.character_ids) ? data.character_ids.length : 0;
        const pageFormatLabels = {
            letter: 'US Letter',
            a4: 'A4',
            portrait: 'Portrait',
            landscape: 'Landscape',
            'square-storybook': 'Square Storybook',
        };
        const pageFormat = String(
            editorSettings.page_format || STORY_EDITOR_DEFAULTS.page_format,
        ).toLowerCase();
        const layoutMode = normalizeLayoutMode(editorSettings.layout_mode);
        s.innerHTML = `
            <p><strong>Title:</strong> ${escapeHTML(data.title || '(AI will generate)')}</p>
            <p><strong>Genre:</strong> ${escapeHTML(data.genre || '(not set)')}</p>
            <p><strong>Outline:</strong> ${escapeHTML(data.story_outline || '(empty)')}</p>
            <p><strong>Characters:</strong> ${escapeHTML(characters.length ? characters.join(', ') : '(none)')}</p>
            <p><strong>Reused characters:</strong> ${reusedCount}</p>
            <p><strong>Writing style:</strong> ${escapeHTML(data.writing_style || '(not set)')}</p>
            <p><strong>Pages:</strong> ${escapeHTML(data.num_pages || '(not set)')} | <strong>Style:</strong> ${escapeHTML(data.image_style || '(not set)')}</p>
            <p><strong>Ratio:</strong> ${escapeHTML(data.word_to_picture_ratio || '(not set)')} | <strong>Density:</strong> ${escapeHTML(data.text_density || '(not set)')}</p>
            <p><strong>Page format:</strong> ${escapeHTML(pageFormatLabels[pageFormat] || pageFormat)}</p>
            <p><strong>Layout mode:</strong> ${escapeHTML(getLayoutModeLabel(layoutMode))} | <strong>Text position:</strong> ${escapeHTML(editorSettings.text_position || 'bottom')}</p>
            <p><strong>Image framing:</strong> ${escapeHTML(editorSettings.image_fit || '(default)')} | <strong>Cover title placement:</strong> ${escapeHTML(editorSettings.cover_title_placement || '(default)')}</p>
            <p><strong>Readability treatment:</strong> ${escapeHTML(editorSettings.readability_treatment || '(default)')}</p>
            <p><strong>Font:</strong> ${escapeHTML(editorSettings.font_family || 'storybook')} ${escapeHTML(editorSettings.font_size || 28)}px | <strong>Colour:</strong> ${escapeHTML(editorSettings.font_color || '#ffffff')} | <strong>Text box opacity:</strong> ${escapeHTML(editorSettings.text_box_opacity ?? 0.6)}</p>
        `;
        review.appendChild(s);
    }

    // Wire next/back
    if (btnNext) {
        btnNext.addEventListener('click', () => {
            if (!validateStep(wizardStep)) return;
            goToStep(Math.min(3, wizardStep + 1));
        });
    }
    if (btnPrev) {
        btnPrev.addEventListener('click', () => {
            goToStep(Math.max(0, wizardStep - 1));
        });
    }
    // Click on step indicators
    stepDots.forEach((dot) => {
        dot.addEventListener('click', () => {
            if (dot.disabled || dot.getAttribute('aria-disabled') === 'true') {
                return;
            }
            // Close Characters modal if open and reset modal state
            try {
                const modal = document.getElementById('char-modal');
                const backdrop = document.getElementById('char-modal-backdrop');
                if (modal) modal.classList.remove('open');
                if (backdrop) backdrop.classList.remove('open');
                if (document && document.body && document.body.dataset) {
                    delete document.body.dataset.charModalState;
                }
            } catch (error) {
                console.error("Error closing modal:", error);
            }
            const s = parseInt(dot.getAttribute('data-step'), 10);
            // Navigate to requested step
            if (!Number.isNaN(s)) {
                goToStep(Math.max(0, Math.min(3, s)));
            }
            // End step indicator click handler and forEach
        });
    });

    // --- INITIALIZATION ---
    // initializeCharacterDetailsToggle(document.querySelector('.character-details-toggle')); // Moved to after first entry ensure
    initializeDropdownRetryButtons();
    updateNav(!!authToken);
    if (!!authToken) {
        if (window.location.hash === "#browse") {
            showSection(browseStoriesSection);
            loadAndDisplayUserStories();
        } else {
            showSection(storyCreationSection);
            populateAllDropdowns(); // Populate all dropdowns on load if logged in
        }
        initializeWizardValidationA11y();
        // Initialize wizard UI state on load
        goToStep(0);
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

    // Reset the wizard form and related state so a fresh story can be created.
    // Exposed at module scope for reuse (e.g., nav actions, "Use as Template").
    function resetFormAndState() {
        console.log("[resetFormAndState] Attempting to reset form and state.");
        wizardStep = 0;
        if (storyCreationForm) {
            storyCreationForm.reset();
            console.log("[resetFormAndState] storyCreationForm reset called.");
        } else {
            console.error("[resetFormAndState] storyCreationForm is null!");
        }

        // Manually reset dropdowns to their placeholder state as a safeguard
        const dropdownIds = [
            "story-genre",
            "story-image-style",
            "story-word-to-picture-ratio",
            "story-text-density",
        ];
        dropdownIds.forEach(id => {
            const select = document.getElementById(id);
            if (select) {
                select.selectedIndex = 0; // The placeholder is the first option
            }
        });

        clearWizardStepErrors(0);
        clearWizardStepErrors(1);
        clearWizardStepErrors(2);

        // Clear existing dynamic characters (beyond the first one)
        const characterEntries = document.querySelectorAll(
            "#main-characters-fieldset .character-entry",
        );
        console.log(
            `[resetFormAndState] Found ${characterEntries.length} character entries.`,
        );
        characterEntries.forEach((entry, index) => {
            if (index > 0) {
                entry.remove();
                console.log(
                    `[resetFormAndState] Removed character entry ${index + 1}.`,
                );
            } else {
                const firstCharacterEntry = characterEntries[0];
                const nameInput = firstCharacterEntry?.querySelector("#char-name-1");
                if (nameInput) nameInput.value = "";
                const ageInput = firstCharacterEntry?.querySelector("#char-age-1");
                if (ageInput) ageInput.value = "";
                const genderSelect = firstCharacterEntry?.querySelector("#char-gender-1");
                if (genderSelect) genderSelect.selectedIndex = 0;
                const physicalTextarea = firstCharacterEntry?.querySelector(
                    "#char-physical-appearance-1",
                );
                if (physicalTextarea) physicalTextarea.value = "";
                const clothingInput = firstCharacterEntry?.querySelector(
                    "#char-clothing-style-1",
                );
                if (clothingInput) clothingInput.value = "";
                const traitsTextarea =
                    firstCharacterEntry?.querySelector("#char-key-traits-1");
                if (traitsTextarea) traitsTextarea.value = "";

                // Hide details and reset toggle text for first character row
                const detailsDiv = document.getElementById("char-details-1");
                const toggleButton = document.getElementById("char-details-toggle-1");
                if (detailsDiv) detailsDiv.style.display = "none";
                if (toggleButton && detailsDiv) {
                    syncCharacterDetailsDisclosure(toggleButton, detailsDiv);
                }
                console.log(
                    "[resetFormAndState] Reset fields and state for first character entry.",
                );
            }
        });

        characterCount = 1; // Reset character count
        console.log("[resetFormAndState] characterCount reset to 1.");

        characterLibraryState.page = 1;
        characterLibraryState.q = '';
        characterLibraryState.items = [];
        characterLibraryState.total = 0;
        characterLibraryState.selectedByIndex.clear();
        characterLibraryState.activeIndex = 1;
        const { search } = getLibraryEls();
        if (search) {
            search.value = '';
        }
        renderCharacterSelectionChips();
        closeCharacterPickerModal({ restoreFocus: false });

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

        // Hide PDF actions as no story is actively being previewed after a reset.
        setPdfActionButtonsVisibility(false);
        closePdfPreviewModal();
        console.log("[resetFormAndState] PDF action buttons hidden.");

        showSection(storyCreationSection); // Ensure the creation form is visible
        updateStepUI();
        displayMessage("Form cleared. Ready for a new story.", "info");
        console.log(
            "[resetFormAndState] Form fields and draft state reset. Navigated to story creation section.",
        );
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
            <div class="character-entry-header">
                <h4 class="character-entry-title">Character ${characterCount}</h4>
                <div class="character-entry-actions wizard-character-row-actions">
                    <button type="button" class="character-details-toggle action-button-info" id="char-details-toggle-${characterCount}" data-target="char-details-${characterCount}" aria-controls="char-details-${characterCount}" aria-expanded="false">Show Details</button>
                    <button type="button" class="wizard-character-picker-trigger action-button-secondary" data-character-index="${characterCount}" aria-haspopup="dialog" aria-controls="character-picker-modal">Add existing character</button>
                    <button type="button" class="remove-character-button action-button-danger" aria-label="Delete character ${characterCount} from this story">Delete from Story</button>
                </div>
            </div>
            <div class="form-group">
                <label for="char-name-${characterCount}">Name <span class="required-badge">Required</span></label>
                <input type="text" id="char-name-${characterCount}" name="char-name-${characterCount}" class="char-name" required aria-describedby="main-characters-error">
            </div>
            <div id="char-details-${characterCount}" class="character-details-fields" style="display: none;">
                <div class="form-group">
                    <label for="char-age-${characterCount}">Age</label>
                    <input type="number" id="char-age-${characterCount}" name="char-age-${characterCount}" class="char-age">
                </div>
                <div class="form-group">
                    <label for="char-gender-${characterCount}">Gender</label>
                    <select id="char-gender-${characterCount}" name="char-gender-${characterCount}" class="char-gender"></select>
                </div>
                <div class="form-group">
                    <label for="char-physical-appearance-${characterCount}">Physical Appearance</label>
                    <textarea id="char-physical-appearance-${characterCount}" name="char-physical-appearance-${characterCount}" class="char-physical-appearance" rows="2"></textarea>
                </div>
                <div class="form-group">
                    <label for="char-clothing-style-${characterCount}">Clothing Style</label>
                    <textarea id="char-clothing-style-${characterCount}" name="char-clothing-style-${characterCount}" class="char-clothing-style" rows="2"></textarea>
                </div>
                <div class="form-group">
                    <label for="char-key-traits-${characterCount}">Key Traits/Habits</label>
                    <textarea id="char-key-traits-${characterCount}" name="char-key-traits-${characterCount}" class="char-key-traits" rows="2"></textarea>
                </div>
            </div>
        `;
        fieldset.appendChild(newCharacterEntry);
        const detailsToggle = newCharacterEntry.querySelector('.character-details-toggle');
        const detailsPanel = newCharacterEntry.querySelector('.character-details-fields');
        if (detailsToggle && detailsPanel) {
            syncCharacterDetailsDisclosure(detailsToggle, detailsPanel);
        }
        attachWizardValidationClearHandler(newCharacterEntry.querySelector('.char-name'));
        updateStepUI();
        // Populate gender dropdown for the newly added character entry
        try { populateDropdown(`char-gender-${characterCount}`, 'genders'); } catch (e) { /* ignore */ }
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

    function normalizeStoryEditorSettings(settings) {
        const normalized = {
            ...STORY_EDITOR_DEFAULTS,
            ...(settings || {}),
        };
        normalized.layout_mode = normalizeLayoutMode(normalized.layout_mode);
        normalized.text_alignment = normalizeTextAlignment(
            normalized.text_alignment,
            normalized.text_position,
        );
        normalized.readability_treatment = normalizeReadabilityTreatment(
            normalized.readability_treatment,
        );
        return normalized;
    }

    function normalizePageEditorState(page) {
        const state = { ...(page?.editor_state || {}) };
        if (state.original_text == null) state.original_text = page?.text || "";
        if (state.original_image_path == null) {
            state.original_image_path = page?.image_path || null;
        }
        return state;
    }

    function findStoryEditorPageIndex(story, pageId) {
        return Array.isArray(story?.pages)
            ? story.pages.findIndex((page) => page.id === pageId)
            : -1;
    }

    function renumberStoryEditorPages(story) {
        if (!story || !Array.isArray(story.pages)) return;
        story.pages.forEach((page, index) => {
            page.page_number = index === 0 ? 0 : index;
        });
        story.num_pages = Math.max(story.pages.length - 1, 0);
        const coverPage = story.pages[0];
        if (coverPage) {
            story.title = coverPage.text || story.title || "Untitled Story";
        }
    }

    function createStoryEditorDraftPage(story, page = {}) {
        const now = new Date().toISOString();
        const draftPage = {
            id: page.id ?? nextStoryEditorTempPageId--,
            story_id: page.story_id ?? story?.id ?? null,
            page_number: page.page_number ?? 1,
            text: page.text || "",
            image_description: page.image_description ?? null,
            image_path: page.image_path ?? null,
            editor_state: normalizePageEditorState({
                text: page.text || "",
                image_path: page.image_path ?? null,
                editor_state: page.editor_state || {},
            }),
            created_at: page.created_at || now,
            updated_at: page.updated_at || now,
        };
        draftPage.__original = JSON.parse(JSON.stringify(draftPage));
        return draftPage;
    }

    function resolveStoryEditorSplitIndex(text, preferredIndex) {
        const normalizedText = String(text || "");
        if (normalizedText.length <= 1) return 0;

        let splitIndex = Number.isInteger(preferredIndex)
            ? preferredIndex
            : Math.floor(normalizedText.length / 2);
        splitIndex = Math.max(1, Math.min(normalizedText.length - 1, splitIndex));

        for (let offset = 0; offset < normalizedText.length; offset += 1) {
            const rightIndex = splitIndex + offset;
            if (/\s/.test(normalizedText[rightIndex] || "")) {
                return Math.min(normalizedText.length - 1, rightIndex + 1);
            }
            const leftIndex = splitIndex - offset;
            if (/\s/.test(normalizedText[leftIndex] || "")) {
                return Math.max(1, leftIndex + 1);
            }
        }

        return splitIndex;
    }

    function cloneStoryForEditor(story) {
        const cloned = JSON.parse(JSON.stringify(story));
        if (cloned.cover_subtitle == null) cloned.cover_subtitle = "";
        if (cloned.cover_author == null) cloned.cover_author = "";
        cloned.editor_settings = normalizeStoryEditorSettings(cloned.editor_settings);
        cloned.pages = Array.isArray(cloned.pages)
            ? cloned.pages
                .slice()
                .sort((a, b) => parseInt(a.page_number, 10) - parseInt(b.page_number, 10))
                .map((page) => ({
                    ...page,
                    editor_state: normalizePageEditorState(page),
                }))
            : [];
        return cloned;
    }

    function createStoryEditorHistorySnapshot(story) {
        if (!story) return null;
        return {
            title: story.title || "",
            cover_subtitle: story.cover_subtitle || "",
            cover_author: story.cover_author || "",
            editor_settings: normalizeStoryEditorSettings(story.editor_settings),
            pages: Array.isArray(story.pages)
                ? story.pages.map((page) => ({
                    id: page.id,
                    story_id: page.story_id,
                    page_number: page.page_number,
                    text: page.text || "",
                    image_description: page.image_description || null,
                    image_path: page.image_path || null,
                    editor_state: normalizePageEditorState(page),
                    created_at: page.created_at || null,
                    updated_at: page.updated_at || null,
                }))
                : [],
        };
    }

    function serializeStoryEditorHistorySnapshot(snapshot) {
        return JSON.stringify(snapshot || null);
    }

    function canUndoStoryEditorChange() {
        return storyEditorState.historyPast.length > 0;
    }

    function canRedoStoryEditorChange() {
        return storyEditorState.historyFuture.length > 0;
    }

    function updateStoryEditorHistoryControls() {
        const undoButton = document.getElementById("story-editor-undo-button");
        const redoButton = document.getElementById("story-editor-redo-button");
        if (undoButton) undoButton.disabled = !canUndoStoryEditorChange();
        if (redoButton) redoButton.disabled = !canRedoStoryEditorChange();
    }

    function resetStoryEditorHistory() {
        storyEditorState.historyPast = [];
        storyEditorState.historyFuture = [];
        updateStoryEditorHistoryControls();
    }

    function mergeStoryEditorHistorySnapshot(currentStory, snapshot) {
        const nextStory = cloneStoryForEditor(currentStory);
        if (!snapshot) return nextStory;

        nextStory.title = snapshot.title || "";
        nextStory.cover_subtitle = snapshot.cover_subtitle || "";
        nextStory.cover_author = snapshot.cover_author || "";
        nextStory.editor_settings = normalizeStoryEditorSettings(
            snapshot.editor_settings,
        );

        nextStory.pages = Array.isArray(snapshot.pages)
            ? snapshot.pages.map((page) => ({
                ...page,
                editor_state: normalizePageEditorState(page),
            }))
            : [];
        renumberStoryEditorPages(nextStory);

        return nextStory;
    }

    function recordStoryEditorHistoryChange(beforeSnapshot, afterSnapshot) {
        if (!beforeSnapshot || !afterSnapshot) return false;

        if (
            serializeStoryEditorHistorySnapshot(beforeSnapshot)
            === serializeStoryEditorHistorySnapshot(afterSnapshot)
        ) {
            return false;
        }

        storyEditorState.historyPast.push(beforeSnapshot);
        if (storyEditorState.historyPast.length > STORY_EDITOR_HISTORY_LIMIT) {
            storyEditorState.historyPast.shift();
        }
        storyEditorState.historyFuture = [];
        updateStoryEditorHistoryControls();
        return true;
    }

    function applyStoryEditorMutation(
        mutator,
        { refresh = "live", autosave = true } = {},
    ) {
        const story = storyEditorState.story;
        if (!story) return false;

        const beforeSnapshot = createStoryEditorHistorySnapshot(story);
        mutator(story);
        const afterSnapshot = createStoryEditorHistorySnapshot(story);
        const changed = recordStoryEditorHistoryChange(
            beforeSnapshot,
            afterSnapshot,
        );

        if (!changed) return false;

        if (refresh === "render") {
            renderStoryEditor();
        } else if (refresh === "live") {
            applyLivePreviewUpdate();
        }

        if (autosave) {
            scheduleStoryEditorAutosave();
        }

        return true;
    }

    function applyStoryEditorHistoryDirection(direction) {
        const sourceStack =
            direction === "undo"
                ? storyEditorState.historyPast
                : storyEditorState.historyFuture;
        const destinationStack =
            direction === "undo"
                ? storyEditorState.historyFuture
                : storyEditorState.historyPast;

        if (!storyEditorState.story || sourceStack.length === 0) return;

        destinationStack.push(
            createStoryEditorHistorySnapshot(storyEditorState.story),
        );
        const snapshot = sourceStack.pop();
        storyEditorState.story = mergeStoryEditorHistorySnapshot(
            storyEditorState.story,
            snapshot,
        );
        renderStoryEditor();
        scheduleStoryEditorAutosave();
        updateStoryEditorHistoryControls();
    }

    function handleStoryEditorHistoryKeydown(event) {
        if (!event || event.defaultPrevented || event.altKey) return;
        if (!event.ctrlKey && !event.metaKey) return;

        const key = String(event.key || "").toLowerCase();
        const isUndo = key === "z" && !event.shiftKey;
        const isRedo = key === "y" || (key === "z" && event.shiftKey);

        if (!isUndo && !isRedo) return;

        event.preventDefault();
        if (isUndo) {
            applyStoryEditorHistoryDirection("undo");
            return;
        }
        applyStoryEditorHistoryDirection("redo");
    }

    function getPageEffectiveSettings(story, page) {
        const settings = normalizeStoryEditorSettings(story?.editor_settings);
        const editorState = normalizePageEditorState(page);
        [
            "text_position",
            "text_alignment",
            "font_size",
            "font_color",
            "text_box_opacity",
        ].forEach((key) => {
            if (editorState[key] !== undefined && editorState[key] !== null && editorState[key] !== "") {
                settings[key] = editorState[key];
            }
        });
        settings.text_alignment = normalizeTextAlignment(
            settings.text_alignment,
            settings.text_position,
        );
        settings.readability_treatment = normalizeReadabilityTreatment(
            settings.readability_treatment,
        );
        return settings;
    }

    function normalizeTextAlignment(alignment, textPosition) {
        const normalized = String(alignment || "").trim().toLowerCase();
        if (["left", "center", "right"].includes(normalized)) {
            return normalized;
        }
        return parseTextPosition(textPosition).h;
    }

    function normalizeReadabilityTreatment(value) {
        const normalized = String(value || "").trim().toLowerCase();
        return STORY_EDITOR_READABILITY_OPTIONS.find(
            (option) => String(option.value).trim().toLowerCase() === normalized,
        )?.value || "";
    }

    function getReadabilityOpacity(settings) {
        const baseOpacity = Math.max(
            0,
            Math.min(1, Number(settings.text_box_opacity ?? 0.6)),
        );
        const treatment = normalizeReadabilityTreatment(
            settings.readability_treatment,
        );
        if (treatment === "High-contrast box") {
            return Math.max(baseOpacity, 0.82);
        }
        if (treatment === "Subtle gradient band") {
            return Math.max(baseOpacity, 0.52);
        }
        if (treatment === "Soft shadow") {
            return Math.max(baseOpacity * 0.35, 0.14);
        }
        return baseOpacity;
    }

    function hexToRgb(value) {
        const normalized = String(value || "").trim();
        const match = normalized.match(/^#?([0-9a-f]{6})$/i);
        if (!match) return { r: 255, g: 255, b: 255 };
        const hex = match[1];
        return {
            r: parseInt(hex.slice(0, 2), 16),
            g: parseInt(hex.slice(2, 4), 16),
            b: parseInt(hex.slice(4, 6), 16),
        };
    }

    function relativeLuminance({ r, g, b }) {
        const channels = [r, g, b].map((channel) => {
            const normalized = channel / 255;
            return normalized <= 0.03928
                ? normalized / 12.92
                : ((normalized + 0.055) / 1.055) ** 2.4;
        });
        return (0.2126 * channels[0]) + (0.7152 * channels[1]) + (0.0722 * channels[2]);
    }

    function contrastRatio(a, b) {
        const lighter = Math.max(a, b);
        const darker = Math.min(a, b);
        return (lighter + 0.05) / (darker + 0.05);
    }

    function getPreviewTextBoxMetrics(settings) {
        const stageWidth = 612;
        const stageHeight = 792;
        const layoutMode = normalizeLayoutMode(settings.layout_mode);
        if (layoutMode === "horizontal-split") {
            return { width: stageWidth, height: stageHeight * 0.38 };
        }
        if (layoutMode === "vertical-split") {
            return { width: stageWidth * 0.44, height: stageHeight };
        }

        const positionStyle = getTextPositionStyle(settings.text_position);
        return {
            width: (parseFloat(positionStyle.width) / 100) * stageWidth,
            height: (parseFloat(positionStyle.height) / 100) * stageHeight,
        };
    }

    function estimateWrappedLineCount(text, boxWidth, fontSize) {
        const safeWidth = Math.max(80, boxWidth - 32);
        const charsPerLine = Math.max(8, Math.floor(safeWidth / (fontSize * 0.56)));
        return String(text || "")
            .split(/\n+/)
            .reduce((count, line) => count + Math.max(1, Math.ceil(Math.max(line.length, 1) / charsPerLine)), 0);
    }

    function getPreviewTextValue(story, page) {
        if (parseInt(page?.page_number, 10) === 0) {
            return [
                story?.title || "Untitled Story",
                story?.cover_subtitle || "",
                story?.cover_author ? `By ${story.cover_author}` : "",
            ].filter(Boolean).join("\n");
        }
        return page?.text || "";
    }

    function getStoryEditorWarnings(story, page) {
        const settings = getPageEffectiveSettings(story, page);
        const warnings = [];
        const contrast = contrastRatio(
            relativeLuminance(hexToRgb(settings.font_color || "#ffffff")),
            0.58 * (1 - getReadabilityOpacity(settings)),
        );

        if (contrast < 4.5) {
            warnings.push({
                type: "contrast",
                message: "Low contrast warning: text may be hard to read against the artwork.",
            });
        }

        const { width, height } = getPreviewTextBoxMetrics(settings);
        const fontSize = Math.max(12, parseInt(settings.font_size, 10) || 28);
        const lineHeight = fontSize * 1.28;
        const estimatedLines = estimateWrappedLineCount(
            getPreviewTextValue(story, page),
            width,
            fontSize,
        );
        const maxLines = Math.max(1, Math.floor((height - 32) / lineHeight));
        if (estimatedLines > maxLines) {
            warnings.push({
                type: "overflow",
                message: "Text overflow warning: this copy is likely too long for the current text box.",
            });
        }

        return warnings;
    }

    function renderPageWarnings(story, page, preview) {
        const warningContainer = preview
            ?.querySelector(`.story-editor-page-warnings[data-page-id="${page.id}"]`);
        const warnings = getStoryEditorWarnings(story, page);
        if (preview) {
            preview.classList.toggle("story-editor-page-preview--warning", warnings.length > 0);
            preview.classList.toggle(
                "story-editor-page-preview--contrast-warning",
                warnings.some((warning) => warning.type === "contrast"),
            );
        }
        if (!warningContainer) return;
        warningContainer.innerHTML = warnings.map((warning) => (
            `<p class="story-editor-page-warning story-editor-page-warning--${warning.type}">${escapeHTML(warning.message)}</p>`
        )).join("");
    }

    function getTextPositionStyle(position) {
        const oldMap = {
            top: "top-center",
            bottom: "bottom-center",
            left: "middle-left",
            right: "middle-right",
            center: "middle-center",
        };
        const normalized = oldMap[String(position || "").toLowerCase()]
            || String(position || "bottom-center").toLowerCase();
        const parts = normalized.split("-");
        const vertical = ["top", "middle", "bottom"].includes(parts[0]) ? parts[0] : "bottom";
        const horizontal = ["left", "center", "right"].includes(parts[1]) ? parts[1] : "center";
        const percent = (value, total) => `${((value / total) * 100).toFixed(3)}%`;
        const stageWidth = 612;
        const stageHeight = 792;
        const margin = 36;
        const top = vertical === "top"
            ? percent(margin, stageHeight)
            : vertical === "middle"
                ? percent((stageHeight - (stageHeight * 0.34)) / 2, stageHeight)
                : "";
        const bottom = vertical === "bottom" ? percent(margin, stageHeight) : "";
        const height = vertical === "middle"
            ? percent(stageHeight * 0.34, stageHeight)
            : percent(stageHeight * 0.22, stageHeight);

        let width;
        let left;
        let right;
        if (horizontal === "left") {
            width = percent(stageWidth * 0.48, stageWidth);
            left = percent(margin, stageWidth);
            right = "";
        } else if (horizontal === "right") {
            width = percent(stageWidth * 0.48, stageWidth);
            left = "";
            right = percent(margin, stageWidth);
        } else {
            width = vertical === "middle"
                ? percent(stageWidth * 0.65, stageWidth)
                : percent(stageWidth - (2 * margin), stageWidth);
            left = vertical === "middle"
                ? percent((stageWidth - (stageWidth * 0.65)) / 2, stageWidth)
                : percent(margin, stageWidth);
            right = "";
        }

        return {
            position: "absolute",
            top,
            right,
            bottom,
            left,
            width,
            height,
        };
    }

    function applyEditorPreviewStyles(pageStage, imageSlot, textCard, settings) {
        const layoutMode = normalizeLayoutMode(settings.layout_mode);
        const positionStyle = getTextPositionStyle(settings.text_position);
        const { v, h } = parseTextPosition(settings.text_position);
        const textAlignment = normalizeTextAlignment(
            settings.text_alignment,
            settings.text_position,
        );
        const readabilityTreatment = normalizeReadabilityTreatment(
            settings.readability_treatment,
        );
        const justifyContent = v === "top"
            ? "flex-start"
            : v === "middle"
                ? "center"
                : "flex-end";
        const alignItems = h === "left"
            ? "flex-start"
            : h === "center"
                ? "center"
                : "flex-end";
        const textAlign = textAlignment;

        pageStage.dataset.layoutMode = layoutMode;
        if (imageSlot) {
            imageSlot.dataset.layoutMode = layoutMode;
            imageSlot.style.position = "";
            imageSlot.style.inset = "";
            imageSlot.style.width = "";
            imageSlot.style.height = "";
            imageSlot.style.minHeight = "0";
            imageSlot.style.overflow = "hidden";
        }

        pageStage.style.display = "block";
        pageStage.style.gridTemplateColumns = "";
        pageStage.style.gridTemplateRows = "";
        pageStage.style.justifyContent = "";
        pageStage.style.alignItems = "";

        textCard.style.display = "block";
        textCard.style.alignItems = "";
        textCard.style.justifyContent = "";
        textCard.style.textAlign = "left";
        textCard.style.position = positionStyle.position;
        textCard.style.top = positionStyle.top;
        textCard.style.right = positionStyle.right;
        textCard.style.bottom = positionStyle.bottom;
        textCard.style.left = positionStyle.left;
        textCard.style.width = positionStyle.width;
        textCard.style.height = positionStyle.height;
        textCard.style.marginLeft = "0";
        textCard.style.marginRight = "0";
        textCard.style.boxSizing = "border-box";
        textCard.style.padding = "1rem";
        textCard.style.fontSize = `${Math.max(12, parseInt(settings.font_size, 10) || 28)}px`;
        textCard.style.color = settings.font_color || "#ffffff";
        textCard.style.textAlign = textAlign;
        textCard.style.fontFamily = "inherit";
        textCard.dataset.readabilityTreatment = readabilityTreatment || "default";
        textCard.style.backgroundColor = `rgba(0, 0, 0, ${getReadabilityOpacity(settings)})`;
        textCard.style.backgroundImage = "";
        textCard.style.textShadow = "none";
        textCard.style.outline = "none";
        textCard.style.backdropFilter = "none";
        textCard.style.webkitBackdropFilter = "none";

        if (readabilityTreatment === "Soft shadow") {
            textCard.style.textShadow = "0 2px 12px rgba(0, 0, 0, 0.85), 0 1px 2px rgba(0, 0, 0, 0.65)";
        } else if (readabilityTreatment === "Subtle gradient band") {
            const baseOpacity = Math.max(0, Math.min(1, Number(settings.text_box_opacity ?? 0.6)));
            const peakOpacity = Math.max(baseOpacity + 0.2, 0.52);
            textCard.style.backgroundColor = "transparent";
            textCard.style.backgroundImage = `linear-gradient(180deg, rgba(0, 0, 0, ${Math.max(baseOpacity, 0.18)}) 0%, rgba(0, 0, 0, ${peakOpacity}) 50%, rgba(0, 0, 0, ${Math.max(baseOpacity, 0.18)}) 100%)`;
            textCard.style.backdropFilter = "blur(1px)";
            textCard.style.webkitBackdropFilter = "blur(1px)";
        } else if (readabilityTreatment === "High-contrast box") {
            textCard.style.outline = "1px solid rgba(255, 255, 255, 0.1)";
        }

        if (layoutMode === "horizontal-split" || layoutMode === "vertical-split") {
            pageStage.style.display = "grid";
            pageStage.style.gridTemplateRows = layoutMode === "horizontal-split" ? "1.05fr 0.7fr" : "1fr";
            pageStage.style.gridTemplateColumns = layoutMode === "vertical-split" ? "1.12fr 0.88fr" : "1fr";
            if (imageSlot) {
                imageSlot.style.position = "relative";
                imageSlot.style.width = "100%";
                imageSlot.style.height = "100%";
            }
            textCard.style.display = "flex";
            textCard.style.position = "relative";
            textCard.style.top = "";
            textCard.style.right = "";
            textCard.style.bottom = "";
            textCard.style.left = "";
            textCard.style.width = "100%";
            textCard.style.height = "100%";
            textCard.style.padding = "1.25rem";
            textCard.style.alignItems = alignItems;
            textCard.style.justifyContent = justifyContent;
            textCard.style.textAlign = textAlign;
            textCard.style.borderRadius = "0";
        }
    }

    /**
     * Re-applies preview styles to all visible page stages without destroying
     * the DOM. Used by control input handlers so native UI elements (colour
     * pickers, selects) are not detached mid-interaction.
     */
    function applyLivePreviewUpdate() {
        const story = storyEditorState.story;
        if (!story || !story.pages) return;
        story.pages.forEach((page) => {
            const pageSettings = getPageEffectiveSettings(story, page);
            const preview = document.querySelector(
                `.story-editor-page-preview[data-page-id="${page.id}"]`
            );
            if (!preview) return;
            const pageStage = preview.querySelector(".story-editor-page-stage");
            const imageSlot = preview.querySelector(".story-editor-page-image-slot");
            const textCard = preview.querySelector(".story-editor-text-card");
            if (pageStage && textCard) {
                applyEditorPreviewStyles(pageStage, imageSlot, textCard, pageSettings);
            }
            const textContent = preview.querySelector(
                ".story-editor-text-card-content"
            );
            if (textContent) {
                if (parseInt(page.page_number, 10) === 0) {
                    textContent.innerHTML = createCoverPreviewMarkup(story);
                } else {
                    textContent.textContent = page.text || "";
                }
            }
            renderPageWarnings(story, page, preview);
        });
    }

    function createCoverPreviewMarkup(story) {
        const title = escapeHTML(story?.title || "Untitled Story");
        const subtitle = escapeHTML(story?.cover_subtitle || "");
        const author = escapeHTML(story?.cover_author || "");
        return `
            <div class="story-editor-cover-preview">
                <div class="story-editor-cover-title">${title}</div>
                ${subtitle ? `<div class="story-editor-cover-subtitle">${subtitle}</div>` : ""}
                ${author ? `<div class="story-editor-cover-author">By ${author}</div>` : ""}
            </div>
        `;
    }

    function buildStoryEditorPayload({ includeAllPages = false } = {}) {
        const story = storyEditorState.story;
        if (!story) return null;
        const changedPages = (story.pages || []).map((page, index) => {
            const state = normalizePageEditorState(page);
            const payloadState = {
                original_text: state.original_text,
                original_image_path: state.original_image_path,
            };

            STORY_EDITOR_PAGE_OVERRIDE_FIELDS.forEach((key) => {
                if (state[key] !== undefined && state[key] !== null && state[key] !== "") {
                    payloadState[key] = state[key];
                }
            });

            return {
                id: page.id > 0 ? page.id : null,
                page_number: index === 0 ? 0 : index,
                text: page.text || "",
                image_description: page.image_description || null,
                image_path: page.image_path || null,
                editor_state: payloadState,
            };
        });

        return {
            title: story.title,
            cover_subtitle: story.cover_subtitle,
            cover_author: story.cover_author,
            editor_settings: story.editor_settings,
            replace_pages: true,
            pages: changedPages,
        };
    }

    function setStoryEditorSaveStatus(state, message, { showRetry = false } = {}) {
        storyEditorState.saveStatus = {
            state,
            message,
            showRetry,
        };

        const statusEl = document.getElementById("story-editor-save-status");
        if (statusEl) {
            statusEl.dataset.state = state;
            statusEl.textContent = message;
        }

        const retryButton = document.getElementById("story-editor-retry-save-button");
        if (retryButton) {
            retryButton.style.display = showRetry ? "inline-flex" : "none";
            retryButton.disabled = storyEditorState.isSaving;
        }
    }

    async function persistStoryEditor({ immediate = false, toast = false } = {}) {
        const story = storyEditorState.story;
        if (!story || !story.id || storyEditorState.isSaving) {
            storyEditorState.saveRequested = storyEditorState.isSaving;
            return;
        }
        const payload = buildStoryEditorPayload({ includeAllPages: immediate });
        if (!payload) return;

        storyEditorState.isSaving = true;
        setStoryEditorSaveStatus(
            "saving",
            immediate ? "Saving..." : "Auto-saving...",
        );
        try {
            const updatedStory = await apiRequest(
                `/api/v1/stories/${story.id}/editor`,
                "PUT",
                payload,
            );
            currentStoryId = updatedStory.id;
            if (!storyEditorState.saveRequested) {
                storyEditorState.story = cloneStoryForEditor(updatedStory);
                storyEditorState.story.pages.forEach((page) => {
                    page.__original = JSON.parse(JSON.stringify(page));
                });
                renderStoryEditor();
                setStoryEditorSaveStatus(
                    "saved",
                    `Saved ${new Date().toLocaleTimeString()}`,
                );
            }
            if (toast) displayMessage("Story changes saved.", "success");
        } catch (error) {
            console.error("[persistStoryEditor] Error saving editor state:", error);
            setStoryEditorSaveStatus(
                "failed",
                "Save failed. Retry to keep editing.",
                { showRetry: true },
            );
        } finally {
            storyEditorState.isSaving = false;
            if (storyEditorState.saveStatus.showRetry) {
                setStoryEditorSaveStatus(
                    storyEditorState.saveStatus.state,
                    storyEditorState.saveStatus.message,
                    { showRetry: true },
                );
            }
            if (storyEditorState.saveRequested) {
                storyEditorState.saveRequested = false;
                persistStoryEditor({ immediate: true });
            }
        }
    }

    function scheduleStoryEditorAutosave() {
        clearTimeout(storyEditorState.autosaveTimer);
        storyEditorState.autosaveTimer = setTimeout(() => {
            persistStoryEditor();
        }, 800);
        setStoryEditorSaveStatus("unsaved", "Unsaved changes");
    }

    async function restoreStoryPageText(pageId) {
        const story = storyEditorState.story;
        if (!story) return;
        const updatedPage = await apiRequest(
            `/api/v1/stories/${story.id}/pages/${pageId}/restore-text`,
            "POST",
        );
        if (!updatedPage) return;
        applyStoryEditorMutation((editorStory) => {
            const page = editorStory.pages.find((item) => item.id === pageId);
            if (!page) return;
            page.text = updatedPage.text;
            page.editor_state = normalizePageEditorState(updatedPage);
            if (parseInt(page.page_number, 10) === 0) {
                editorStory.title = updatedPage.text;
            }
        }, { refresh: "render", autosave: false });
        displayMessage("Original page text restored.", "success");
    }

    async function restoreStoryPageImage(pageId) {
        const story = storyEditorState.story;
        if (!story) return;
        const updatedPage = await apiRequest(
            `/api/v1/stories/${story.id}/pages/${pageId}/restore-image`,
            "POST",
        );
        if (!updatedPage) return;
        applyStoryEditorMutation((editorStory) => {
            const page = editorStory.pages.find((item) => item.id === pageId);
            if (!page) return;
            page.image_path = updatedPage.image_path;
            page.editor_state = normalizePageEditorState(updatedPage);
        }, { refresh: "render", autosave: false });
        displayMessage("Original page image restored.", "success");
    }

    async function regenerateStoryPageText(pageId) {
        const story = storyEditorState.story;
        if (!story) return;
        const updatedPage = await apiRequest(
            `/api/v1/stories/${story.id}/pages/${pageId}/regenerate-text`,
            "POST",
        );
        if (!updatedPage) return;
        applyStoryEditorMutation((editorStory) => {
            const page = editorStory.pages.find((item) => item.id === pageId);
            if (!page) return;
            page.text = updatedPage.text;
            page.image_description = updatedPage.image_description || page.image_description;
            page.editor_state = normalizePageEditorState(updatedPage);
        }, { refresh: "render", autosave: false });
        displayMessage("Page text regenerated.", "success");
    }

    async function regenerateStoryPageImage(pageId) {
        const story = storyEditorState.story;
        if (!story) return;
        const updatedPage = await apiRequest(
            `/api/v1/stories/${story.id}/pages/${pageId}/regenerate-image`,
            "POST",
        );
        if (!updatedPage) return;
        applyStoryEditorMutation((editorStory) => {
            const page = editorStory.pages.find((item) => item.id === pageId);
            if (!page) return;
            page.image_path = updatedPage.image_path;
            page.editor_state = normalizePageEditorState(updatedPage);
        }, { refresh: "render", autosave: false });
        displayMessage("Page image regenerated.", "success");
    }

    function createFontOptions(selectedValue) {
        return STORY_EDITOR_FONT_OPTIONS.map((option) => {
            const selected = option.value === selectedValue ? "selected" : "";
            return `<option value="${option.value}" ${selected}>${option.label}</option>`;
        }).join("");
    }

    function createLayoutModeOptions(selectedValue) {
        const normalized = normalizeLayoutMode(selectedValue);
        return STORY_EDITOR_LAYOUT_OPTIONS.map((option) => {
            const selected = option.value === normalized ? "selected" : "";
            return `<option value="${option.value}" ${selected}>${option.label}</option>`;
        }).join("");
    }

    function createTextAlignmentOptions(selectedValue) {
        const normalized = normalizeTextAlignment(selectedValue);
        return STORY_EDITOR_TEXT_ALIGNMENT_OPTIONS.map((option) => {
            const selected = option.value === normalized ? "selected" : "";
            return `<option value="${option.value}" ${selected}>${option.label}</option>`;
        }).join("");
    }

    function createReadabilityTreatmentOptions(selectedValue) {
        const normalized = normalizeReadabilityTreatment(selectedValue);
        return STORY_EDITOR_READABILITY_OPTIONS.map((option) => {
            const selected = option.value === normalized ? "selected" : "";
            return `<option value="${option.value}" ${selected}>${option.label}</option>`;
        }).join("");
    }

    function createColorSwatches(targetId, selectedValue) {
        const normalized = String(selectedValue || "").trim().toLowerCase();
        return `
            <div class="story-editor-color-swatches" role="group" aria-label="Curated text colour swatches">
                ${STORY_EDITOR_COLOR_SWATCHES.map((color) => {
                    const isSelected = color.toLowerCase() === normalized;
                    const swatchClass = relativeLuminance(hexToRgb(color)) > 0.8
                        ? " story-editor-color-swatch--light"
                        : "";
                    return `<button type="button" class="story-editor-color-swatch${swatchClass}" data-color-swatch-target="${targetId}" data-color-value="${color}" aria-label="Use ${color} text" aria-pressed="${isSelected ? "true" : "false"}" style="background:${color};"></button>`;
                }).join("")}
            </div>
        `;
    }

    function createTextPositionOptions(selectedValue) {
        return ["top", "bottom", "left", "right", "center"].map((value) => {
            const selected = value === selectedValue ? "selected" : "";
            const label = value.charAt(0).toUpperCase() + value.slice(1);
            return `<option value="${value}" ${selected}>${label}</option>`;
        }).join("");
    }

    function parseTextPosition(position) {
        const oldMap = {
            top: "top-center",
            bottom: "bottom-center",
            left: "middle-left",
            right: "middle-right",
            center: "middle-center",
        };
        const normalized = oldMap[String(position || "").toLowerCase()]
            || String(position || "bottom-center").toLowerCase();
        const parts = normalized.split("-");
        return {
            v: ["top", "middle", "bottom"].includes(parts[0]) ? parts[0] : "bottom",
            h: ["left", "center", "right"].includes(parts[1]) ? parts[1] : "center",
        };
    }

    function combineTextPosition(vertical, horizontal) {
        return `${vertical || "bottom"}-${horizontal || "center"}`;
    }

    function isPrivateStoryAssetPath(path) {
        const normalized = String(path || "")
            .trim()
            .replace(/^\/+/, "")
            .replace(/\\/g, "/");
        return /^images\/user_\d+\/story_\d+(?:\/|$)/.test(normalized);
    }

    function revokeStoryEditorImageUrl(entry) {
        if (!entry?.objectUrl || !window.URL?.revokeObjectURL) return;
        window.URL.revokeObjectURL(entry.objectUrl);
    }

    function syncStoryEditorImageCache(story) {
        const pages = Array.isArray(story?.pages) ? story.pages : [];
        const validImagePaths = new Map(
            pages
                .filter((page) => page?.image_path && isPrivateStoryAssetPath(page.image_path))
                .map((page) => [page.id, page.image_path]),
        );

        for (const [pageId, entry] of storyEditorState.pageImageObjectUrls.entries()) {
            if (entry.storyId !== story?.id || validImagePaths.get(pageId) !== entry.imagePath) {
                revokeStoryEditorImageUrl(entry);
                storyEditorState.pageImageObjectUrls.delete(pageId);
            }
        }

        for (const [pageId, entry] of storyEditorState.pageImageFetches.entries()) {
            if (entry.storyId !== story?.id || validImagePaths.get(pageId) !== entry.imagePath) {
                storyEditorState.pageImageFetches.delete(pageId);
            }
        }
    }

    function createStoryPageImageElement(src) {
        const imageEl = document.createElement("img");
        imageEl.className = "story-editor-page-image";
        imageEl.src = src;
        imageEl.alt = "Story page image";
        return imageEl;
    }

    function setStoryPageImageSlotContent(slot, content) {
        if (!slot) return;
        slot.innerHTML = "";
        if (typeof content === "string") {
            slot.innerHTML = content;
            return;
        }
        slot.appendChild(content);
    }

    async function fetchPrivateStoryPageImageObjectUrl(storyId, pageId) {
        const token = localStorage.getItem("authToken");
        const response = await fetch(
            `${API_BASE_URL}/api/v1/stories/${storyId}/pages/${pageId}/image`,
            {
                method: "GET",
                headers: {
                    Authorization: `Bearer ${token}`,
                },
            },
        );

        if (!response.ok) {
            throw new Error(`Could not load story image (${response.status}).`);
        }

        const blob = await response.blob();
        return window.URL.createObjectURL(blob);
    }

    async function hydrateStoryPageImage(story, page) {
        const slot = document.querySelector(
            `.story-editor-page-image-slot[data-page-id="${page.id}"]`,
        );
        if (!slot) return;

        if (!page.image_path) {
            setStoryPageImageSlotContent(
                slot,
                '<div class="story-editor-page-image story-editor-page-image--placeholder">Image unavailable</div>',
            );
            return;
        }

        if (!isPrivateStoryAssetPath(page.image_path)) {
            setStoryPageImageSlotContent(
                slot,
                createStoryPageImageElement(staticContentUrl(page.image_path)),
            );
            return;
        }

        if (Number(page.id) <= 0) {
            setStoryPageImageSlotContent(
                slot,
                '<div class="story-editor-page-image story-editor-page-image--placeholder">Save to load image</div>',
            );
            return;
        }

        const cachedImage = storyEditorState.pageImageObjectUrls.get(page.id);
        if (
            cachedImage
            && cachedImage.storyId === story.id
            && cachedImage.imagePath === page.image_path
        ) {
            setStoryPageImageSlotContent(
                slot,
                createStoryPageImageElement(cachedImage.objectUrl),
            );
            return;
        }

        setStoryPageImageSlotContent(
            slot,
            '<div class="story-editor-page-image story-editor-page-image--placeholder">Loading image...</div>',
        );

        let pendingImage = storyEditorState.pageImageFetches.get(page.id);
        if (
            !pendingImage
            || pendingImage.storyId !== story.id
            || pendingImage.imagePath !== page.image_path
        ) {
            pendingImage = {
                storyId: story.id,
                imagePath: page.image_path,
                promise: fetchPrivateStoryPageImageObjectUrl(story.id, page.id),
            };
            storyEditorState.pageImageFetches.set(page.id, pendingImage);
        }

        try {
            const objectUrl = await pendingImage.promise;
            const latestStory = storyEditorState.story;
            const latestPage = latestStory?.pages?.find((item) => item.id === page.id);

            if (!latestStory || latestStory.id !== story.id || latestPage?.image_path !== page.image_path) {
                revokeStoryEditorImageUrl({ objectUrl });
                return;
            }

            const previousImage = storyEditorState.pageImageObjectUrls.get(page.id);
            if (previousImage && previousImage.objectUrl !== objectUrl) {
                revokeStoryEditorImageUrl(previousImage);
            }

            storyEditorState.pageImageObjectUrls.set(page.id, {
                storyId: story.id,
                imagePath: page.image_path,
                objectUrl,
            });

            const latestSlot = document.querySelector(
                `.story-editor-page-image-slot[data-page-id="${page.id}"]`,
            );
            setStoryPageImageSlotContent(
                latestSlot,
                createStoryPageImageElement(objectUrl),
            );
        } catch (error) {
            console.error("[story editor image] Error loading image:", error);
            setStoryPageImageSlotContent(
                slot,
                '<div class="story-editor-page-image story-editor-page-image--placeholder">Image unavailable</div>',
            );
        } finally {
            const activeFetch = storyEditorState.pageImageFetches.get(page.id);
            if (
                activeFetch
                && activeFetch.storyId === pendingImage.storyId
                && activeFetch.imagePath === pendingImage.imagePath
            ) {
                storyEditorState.pageImageFetches.delete(page.id);
            }
        }
    }

    function createTextPositionSelects(currentPosition, idPrefix, pageId) {
        const { v, h } = parseTextPosition(currentPosition);
        const pageAttr = pageId != null ? ` data-page-id="${pageId}"` : "";
        const verticalOptions = STORY_EDITOR_TEXT_POSITIONS_V.map((value) =>
            `<option value="${value}" ${value === v ? "selected" : ""}>${STORY_EDITOR_POSITION_LABELS_V[value]}</option>`
        ).join("");
        const horizontalOptions = STORY_EDITOR_TEXT_POSITIONS_H.map((value) =>
            `<option value="${value}" ${value === h ? "selected" : ""}>${STORY_EDITOR_POSITION_LABELS_H[value]}</option>`
        ).join("");
        return `
            <div style="display:flex;gap:0.5rem;align-items:center;">
                <select id="${idPrefix}-v" class="story-editor-select" style="flex:1;min-width:0" ${pageAttr ? `data-page-field="text_position_v"${pageAttr}` : ""}>${verticalOptions}</select>
                <select id="${idPrefix}-h" class="story-editor-select" style="flex:1;min-width:0" ${pageAttr ? `data-page-field="text_position_h"${pageAttr}` : ""}>${horizontalOptions}</select>
            </div>
        `;
    }

    function renderStoryEditor() {
        const story = storyEditorState.story;
        if (!storyPreviewContent || !story) {
            console.error("[displayStory] Story preview content area or story data is missing.");
            displayMessage("Could not display story preview.", "error");
            setPdfActionButtonsVisibility(false);
            return;
        }

        syncStoryEditorImageCache(story);

        currentStoryId = story.id;
        storyPreviewContent.innerHTML = "";

        const shell = document.createElement("div");
        shell.className = "story-editor-shell";
        shell.tabIndex = -1;
        const saveStatus = storyEditorState.saveStatus || {
            state: "saved",
            message: "Saved",
            showRetry: false,
        };
        const previewAvailable = storyEditorState.previewAvailable !== false;
        shell.innerHTML = `
            <div class="story-editor-toolbar">
                <div class="story-editor-title-group">
                    <label class="story-editor-field-label" for="story-editor-title">Story Title</label>
                    <input id="story-editor-title" class="story-editor-title-input" type="text" value="${escapeHTML(story.title || "Untitled Story")}">
                    <div class="story-editor-cover-fields">
                        <div>
                            <label class="story-editor-field-label" for="story-editor-cover-subtitle">Cover Subtitle</label>
                            <input id="story-editor-cover-subtitle" class="story-editor-title-input" type="text" value="${escapeHTML(story.cover_subtitle || "")}" placeholder="Optional subtitle">
                        </div>
                        <div>
                            <label class="story-editor-field-label" for="story-editor-cover-author">Cover Author</label>
                            <input id="story-editor-cover-author" class="story-editor-title-input" type="text" value="${escapeHTML(story.cover_author || "")}" placeholder="Optional author name">
                        </div>
                    </div>
                </div>
                <div class="story-editor-toolbar-actions">
                    ${previewAvailable ? '<button type="button" id="story-editor-preview-button" class="action-button-secondary">Back to Preview</button>' : ''}
                    <div class="story-editor-history-actions" aria-label="Editor history controls">
                        <button type="button" id="story-editor-undo-button" class="action-button-secondary" ${canUndoStoryEditorChange() ? "" : "disabled"} aria-label="Undo recent change">Undo</button>
                        <button type="button" id="story-editor-redo-button" class="action-button-secondary" ${canRedoStoryEditorChange() ? "" : "disabled"} aria-label="Redo recent change">Redo</button>
                    </div>
                    <span id="story-editor-save-status" class="story-editor-save-status" role="status" aria-live="polite" aria-atomic="true" data-state="${saveStatus.state}">${escapeHTML(saveStatus.message)}</span>
                    <button type="button" id="story-editor-retry-save-button" class="action-button-secondary" style="display:${saveStatus.showRetry ? "inline-flex" : "none"};">Retry save</button>
                    <button type="button" id="story-editor-save-button" class="action-button-primary">Save</button>
                </div>
            </div>
            <div class="story-editor-layout">
                <aside class="story-editor-sidebar">
                    <h3>Document Defaults</h3>
                    <label class="story-editor-field-label" for="story-editor-layout-mode">Layout Mode</label>
                    <select id="story-editor-layout-mode" class="story-editor-select">${createLayoutModeOptions(story.editor_settings.layout_mode)}</select>
                    <label class="story-editor-field-label" for="story-editor-font-family">Font</label>
                    <select id="story-editor-font-family" class="story-editor-select">${createFontOptions(story.editor_settings.font_family)}</select>
                    <label class="story-editor-field-label" for="story-editor-font-size">Font Size</label>
                        <input id="story-editor-font-size" class="story-editor-number" type="number" min="16" max="56" step="1" value="${Number(story.editor_settings.font_size || 28)}">
                    <label class="story-editor-field-label" for="story-editor-font-color">Font Colour</label>
                    <div class="story-editor-color-row">
                        <input id="story-editor-font-color" class="story-editor-color" type="color" value="${story.editor_settings.font_color || "#ffffff"}">
                    </div>
                    ${createColorSwatches("story-editor-font-color", story.editor_settings.font_color || "#ffffff")}
                    <label class="story-editor-field-label">Text Position</label>
                    ${createTextPositionSelects(story.editor_settings.text_position, "story-editor-text-position", null)}
                    <label class="story-editor-field-label" for="story-editor-text-alignment">Text Alignment</label>
                    <select id="story-editor-text-alignment" class="story-editor-select">${createTextAlignmentOptions(story.editor_settings.text_alignment)}</select>
                    <label class="story-editor-field-label" for="story-editor-readability-treatment">Readability Treatment</label>
                    <select id="story-editor-readability-treatment" class="story-editor-select">${createReadabilityTreatmentOptions(story.editor_settings.readability_treatment)}</select>
                        <div style="display:flex;align-items:center;gap:0.5rem;">
                            <label class="story-editor-field-label" for="story-editor-text-opacity" style="margin:0;">Text Box Opacity</label>
                            <span id="story-editor-text-opacity-value" style="font-size:0.85rem;color:#a8b3c7;min-width:2.5rem;text-align:right;">${Math.round((story.editor_settings.text_box_opacity ?? 0.6) * 100)}%</span>
                        </div>
                    <input id="story-editor-text-opacity" class="story-editor-range" type="range" min="0" max="1" step="0.05" value="${Number(story.editor_settings.text_box_opacity ?? 0.6)}">
                    <p class="story-editor-help">Defaults apply to all pages unless a page override is set.</p>
                </aside>
                <div class="story-editor-pages" id="story-editor-pages"></div>
            </div>
        `;

        storyPreviewContent.appendChild(shell);
        shell.addEventListener("keydown", handleStoryEditorHistoryKeydown);
        shell.querySelector("#story-editor-preview-button")?.addEventListener("click", () => {
            renderStoryReadOnlyPreview();
        });
        shell.querySelector("#story-editor-undo-button")?.addEventListener("click", () => {
            applyStoryEditorHistoryDirection("undo");
        });
        shell.querySelector("#story-editor-redo-button")?.addEventListener("click", () => {
            applyStoryEditorHistoryDirection("redo");
        });
        const titleInput = shell.querySelector("#story-editor-title");
        titleInput.addEventListener("input", (event) => {
            applyStoryEditorMutation((editorStory) => {
                editorStory.title = event.target.value;
                const coverPage = editorStory.pages.find(
                    (page) => parseInt(page.page_number, 10) === 0,
                );
                if (coverPage) coverPage.text = editorStory.title;
            });
        });

        shell.querySelector("#story-editor-cover-subtitle")?.addEventListener("input", (event) => {
            applyStoryEditorMutation((editorStory) => {
                editorStory.cover_subtitle = event.target.value;
            });
        });

        shell.querySelector("#story-editor-cover-author")?.addEventListener("input", (event) => {
            applyStoryEditorMutation((editorStory) => {
                editorStory.cover_author = event.target.value;
            });
        });

        [
            ["#story-editor-layout-mode", "layout_mode", (value) => normalizeLayoutMode(value)],
            ["#story-editor-font-family", "font_family", (value) => value],
            ["#story-editor-font-size", "font_size", (value) => parseInt(value, 10)],
            ["#story-editor-font-color", "font_color", (value) => value],
            ["#story-editor-text-alignment", "text_alignment", (value) => normalizeTextAlignment(value, story.editor_settings.text_position)],
            ["#story-editor-readability-treatment", "readability_treatment", (value) => normalizeReadabilityTreatment(value)],
            ["#story-editor-text-opacity", "text_box_opacity", (value) => Number(value)],
        ].forEach(([selector, key, parser]) => {
            const input = shell.querySelector(selector);
            input.addEventListener("input", (event) => {
                applyStoryEditorMutation((editorStory) => {
                    editorStory.editor_settings[key] = parser(event.target.value);
                });
            });
        });

        const opacityInput = shell.querySelector("#story-editor-text-opacity");
        const opacityValueEl = shell.querySelector("#story-editor-text-opacity-value");
        if (opacityInput && opacityValueEl) {
            opacityInput.addEventListener("input", (event) => {
                opacityValueEl.textContent = `${Math.round(Number(event.target.value) * 100)}%`;
            });
        }

        ["story-editor-text-position-v", "story-editor-text-position-h"].forEach((id) => {
            const element = shell.querySelector(`#${id}`);
            if (!element) return;
            element.addEventListener("input", () => {
                const vertical = shell.querySelector("#story-editor-text-position-v")?.value || "bottom";
                const horizontal = shell.querySelector("#story-editor-text-position-h")?.value || "center";
                applyStoryEditorMutation((editorStory) => {
                    editorStory.editor_settings.text_position = combineTextPosition(
                        vertical,
                        horizontal,
                    );
                });
            });
        });

        shell.querySelectorAll("[data-color-swatch-target]").forEach((button) => {
            button.addEventListener("click", () => {
                const targetId = button.dataset.colorSwatchTarget;
                const value = button.dataset.colorValue;
                const targetInput = document.getElementById(targetId);
                if (!targetInput) return;
                targetInput.value = value;
                targetInput.dispatchEvent(new Event("input", { bubbles: true }));
            });
        });

        shell.querySelector("#story-editor-save-button").addEventListener("click", async () => {
            await persistStoryEditor({ immediate: true, toast: true });
            renderStoryEditor();
        });

        shell.querySelector("#story-editor-retry-save-button").addEventListener("click", async () => {
            await persistStoryEditor({ immediate: true, toast: true });
            renderStoryEditor();
        });

        const pagesContainer = shell.querySelector("#story-editor-pages");
        if (!story.pages || story.pages.length === 0) {
            pagesContainer.innerHTML = "<p>This story has no pages.</p>";
        } else {
            story.pages.forEach((page) => {
                const pageSettings = getPageEffectiveSettings(story, page);
                const isCoverPage = parseInt(page.page_number, 10) === 0;
                const canMoveUp = !isCoverPage && parseInt(page.page_number, 10) > 1;
                const canMoveDown = !isCoverPage && parseInt(page.page_number, 10) < story.pages.length - 1;
                const canMerge = !isCoverPage && parseInt(page.page_number, 10) < story.pages.length - 1;
                const pageCard = document.createElement("article");
                pageCard.className = "story-editor-page-card";
                pageCard.innerHTML = `
                    <div class="story-editor-page-header">
                        <div>
                            <h3>${parseInt(page.page_number, 10) === 0 ? "Cover Page" : `Page ${page.page_number}`}</h3>
                            <p class="story-editor-page-subtitle">${escapeHTML(getLayoutModeDescription(pageSettings.layout_mode))}</p>
                        </div>
                        <div class="story-editor-page-actions">
                            <button type="button" class="action-button-secondary" data-action="restore-text" data-page-id="${page.id}">Restore Text</button>
                            <button type="button" class="action-button-secondary" data-action="restore-image" data-page-id="${page.id}">Restore Image</button>
                            ${isCoverPage ? "" : `<button type="button" class="action-button-info" data-action="regen-text" data-page-id="${page.id}">Regenerate Text</button>`}
                            <button type="button" class="action-button-info" data-action="regen-image" data-page-id="${page.id}">Regenerate Image</button>
                            <button type="button" class="action-button-secondary" data-action="add-page" data-page-id="${page.id}">Add Page After</button>
                            ${isCoverPage ? "" : `<button type="button" class="action-button-secondary" data-action="duplicate-page" data-page-id="${page.id}">Duplicate</button>`}
                            ${isCoverPage ? "" : `<button type="button" class="action-button-secondary" data-action="move-up" data-page-id="${page.id}" ${canMoveUp ? "" : "disabled"}>Move Up</button>`}
                            ${isCoverPage ? "" : `<button type="button" class="action-button-secondary" data-action="move-down" data-page-id="${page.id}" ${canMoveDown ? "" : "disabled"}>Move Down</button>`}
                            ${isCoverPage ? "" : `<button type="button" class="action-button-secondary" data-action="split-page" data-page-id="${page.id}">Split</button>`}
                            ${isCoverPage ? "" : `<button type="button" class="action-button-secondary" data-action="merge-page" data-page-id="${page.id}" ${canMerge ? "" : "disabled"}>Merge Next</button>`}
                            ${isCoverPage ? "" : `<button type="button" class="action-button-secondary" data-action="delete-page" data-page-id="${page.id}">Delete</button>`}
                        </div>
                    </div>
                    <div class="story-editor-page-layout">
                        <div class="story-editor-page-preview" data-page-id="${page.id}">
                            <div class="story-editor-page-stage">
                                <div class="story-editor-page-image-slot" data-page-id="${page.id}">${page.image_path ? `<div class="story-editor-page-image story-editor-page-image--placeholder">Loading image...</div>` : `<div class="story-editor-page-image story-editor-page-image--placeholder">Image unavailable</div>`}</div>
                                <div class="story-editor-text-card">
                                    <div class="story-editor-text-card-content">${parseInt(page.page_number, 10) === 0 ? createCoverPreviewMarkup(story) : escapeHTML(page.text || "")}</div>
                                </div>
                            </div>
                            <div class="story-editor-page-warnings" data-page-id="${page.id}"></div>
                        </div>
                        <div class="story-editor-page-controls">
                            <label class="story-editor-field-label">Page Text</label>
                            <textarea class="story-editor-textarea" data-page-field="text" data-page-id="${page.id}" rows="5">${escapeHTML(page.text || "")}</textarea>
                            <div>
                                <label class="story-editor-field-label">Text Position Override</label>
                                ${createTextPositionSelects(page.editor_state.text_position || pageSettings.text_position, "page-text-pos-" + page.id, page.id)}
                            </div>
                            <div>
                                <label class="story-editor-field-label">Text Alignment Override</label>
                                <select class="story-editor-select" data-page-field="text_alignment" data-page-id="${page.id}">${createTextAlignmentOptions(page.editor_state.text_alignment || pageSettings.text_alignment)}</select>
                            </div>
                            <div class="story-editor-inline-grid">
                                <div>
                                    <label class="story-editor-field-label">Font Size Override</label>
                                    <input class="story-editor-number" data-page-field="font_size" data-page-id="${page.id}" type="number" min="16" max="56" value="${page.editor_state.font_size ?? ""}" placeholder="Default ${pageSettings.font_size}">
                                </div>
                                <div>
                                    <label class="story-editor-field-label">Font Colour Override</label>
                                    <div class="story-editor-color-row">
                                        <input id="story-editor-page-font-color-${page.id}" class="story-editor-color" data-page-field="font_color" data-page-id="${page.id}" type="color" value="${page.editor_state.font_color || pageSettings.font_color || "#ffffff"}">
                                    </div>
                                    ${createColorSwatches(`story-editor-page-font-color-${page.id}`, page.editor_state.font_color || pageSettings.font_color || "#ffffff")}
                                </div>
                            </div>
                            <div>
                                <div style="display:flex;align-items:center;gap:0.5rem;">
                                    <label class="story-editor-field-label" for="story-editor-page-opacity-${page.id}" style="margin:0;">Text Box Opacity Override</label>
                                    <span data-page-opacity-value="${page.id}" style="font-size:0.85rem;color:#a8b3c7;min-width:2.5rem;text-align:right;">${Math.round(Number(page.editor_state.text_box_opacity ?? pageSettings.text_box_opacity ?? 0.6) * 100)}%</span>
                                </div>
                                <input
                                    id="story-editor-page-opacity-${page.id}"
                                    class="story-editor-range"
                                    data-page-field="text_box_opacity"
                                    data-page-id="${page.id}"
                                    type="range"
                                    min="0"
                                    max="1"
                                    step="0.05"
                                    value="${Number(page.editor_state.text_box_opacity ?? pageSettings.text_box_opacity ?? 0.6)}"
                                >
                            </div>
                            <button type="button" class="action-button-secondary story-editor-clear-override" data-action="clear-overrides" data-page-id="${page.id}">Use Document Defaults</button>
                        </div>
                    </div>
                `;
                const pageStage = pageCard.querySelector(".story-editor-page-stage");
                const imageSlot = pageCard.querySelector(".story-editor-page-image-slot");
                const textCard = pageCard.querySelector(".story-editor-text-card");
                applyEditorPreviewStyles(pageStage, imageSlot, textCard, pageSettings);
                renderPageWarnings(story, page, pageCard.querySelector(".story-editor-page-preview"));
                pagesContainer.appendChild(pageCard);
                void hydrateStoryPageImage(story, page);
            });
        }

        pagesContainer.querySelectorAll("[data-color-swatch-target]").forEach((button) => {
            button.addEventListener("click", () => {
                const targetId = button.dataset.colorSwatchTarget;
                const value = button.dataset.colorValue;
                const targetInput = document.getElementById(targetId);
                if (!targetInput) return;
                targetInput.value = value;
                targetInput.dispatchEvent(new Event("input", { bubbles: true }));
            });
        });

        pagesContainer.querySelectorAll("[data-page-field]").forEach((input) => {
            input.addEventListener("input", (event) => {
                const pageId = parseInt(event.target.dataset.pageId, 10);
                const field = event.target.dataset.pageField;
                applyStoryEditorMutation((editorStory) => {
                    const page = editorStory.pages.find((item) => item.id === pageId);
                    if (!page) return;
                    if (field === "text") {
                        page.text = event.target.value;
                        if (parseInt(page.page_number, 10) === 0) {
                            editorStory.title = event.target.value;
                        }
                    } else if (field === "text_position_v" || field === "text_position_h") {
                        const pageCard = event.target.closest(".story-editor-page-card");
                        const verticalInput = pageCard?.querySelector(`[data-page-field="text_position_v"][data-page-id="${pageId}"]`);
                        const horizontalInput = pageCard?.querySelector(`[data-page-field="text_position_h"][data-page-id="${pageId}"]`);
                        const vertical = verticalInput?.value || "bottom";
                        const horizontal = horizontalInput?.value || "center";
                        page.editor_state.text_position = combineTextPosition(
                            vertical,
                            horizontal,
                        );
                    } else if (field === "text_box_opacity") {
                        page.editor_state[field] = event.target.value === ""
                            ? null
                            : Number(event.target.value);
                        const valueEl = event.target
                            .closest(".story-editor-page-controls")
                            ?.querySelector(`[data-page-opacity-value="${pageId}"]`);
                        if (valueEl) {
                            valueEl.textContent = `${Math.round(Number(event.target.value) * 100)}%`;
                        }
                    } else if (field === "font_size") {
                        page.editor_state[field] = event.target.value
                            ? parseInt(event.target.value, 10)
                            : null;
                    } else if (field === "text_alignment") {
                        page.editor_state[field] = event.target.value || null;
                    } else {
                        page.editor_state[field] = event.target.value || null;
                    }
                });
            });
        });

        pagesContainer.querySelectorAll("[data-action]").forEach((button) => {
            button.addEventListener("click", async (event) => {
                const pageId = parseInt(event.currentTarget.dataset.pageId, 10);
                const action = event.currentTarget.dataset.action;
                const page = story.pages.find((item) => item.id === pageId);
                if (!page) return;
                if (action === "clear-overrides") {
                    applyStoryEditorMutation((editorStory) => {
                        const targetPage = editorStory.pages.find(
                            (item) => item.id === pageId,
                        );
                        if (!targetPage) return;
                        targetPage.editor_state.text_position = null;
                        targetPage.editor_state.text_alignment = null;
                        targetPage.editor_state.font_size = null;
                        targetPage.editor_state.font_color = null;
                        targetPage.editor_state.text_box_opacity = null;
                    }, { refresh: "render" });
                    return;
                }
                if (action === "add-page") {
                    applyStoryEditorMutation((editorStory) => {
                        const pageIndex = findStoryEditorPageIndex(editorStory, pageId);
                        if (pageIndex < 0) return;
                        editorStory.pages.splice(
                            pageIndex + 1,
                            0,
                            createStoryEditorDraftPage(editorStory),
                        );
                        renumberStoryEditorPages(editorStory);
                    }, { refresh: "render" });
                    return;
                }
                if (action === "duplicate-page") {
                    applyStoryEditorMutation((editorStory) => {
                        const pageIndex = findStoryEditorPageIndex(editorStory, pageId);
                        if (pageIndex < 0) return;
                        const sourcePage = editorStory.pages[pageIndex];
                        const duplicatePage = createStoryEditorDraftPage(editorStory, {
                            text: sourcePage.text,
                            image_description: sourcePage.image_description,
                            image_path: sourcePage.image_path,
                            editor_state: {
                                ...normalizePageEditorState(sourcePage),
                                original_text: sourcePage.text || "",
                                original_image_path: sourcePage.image_path || null,
                            },
                        });
                        editorStory.pages.splice(pageIndex + 1, 0, duplicatePage);
                        renumberStoryEditorPages(editorStory);
                    }, { refresh: "render" });
                    return;
                }
                if (action === "move-up" || action === "move-down") {
                    applyStoryEditorMutation((editorStory) => {
                        const pageIndex = findStoryEditorPageIndex(editorStory, pageId);
                        if (pageIndex <= 0) return;
                        const swapIndex = action === "move-up"
                            ? pageIndex - 1
                            : pageIndex + 1;
                        if (swapIndex <= 0 || swapIndex >= editorStory.pages.length) return;
                        const [movingPage] = editorStory.pages.splice(pageIndex, 1);
                        editorStory.pages.splice(swapIndex, 0, movingPage);
                        renumberStoryEditorPages(editorStory);
                    }, { refresh: "render" });
                    return;
                }
                if (action === "delete-page") {
                    applyStoryEditorMutation((editorStory) => {
                        const pageIndex = findStoryEditorPageIndex(editorStory, pageId);
                        if (pageIndex <= 0) return;
                        editorStory.pages.splice(pageIndex, 1);
                        renumberStoryEditorPages(editorStory);
                    }, { refresh: "render" });
                    return;
                }
                if (action === "split-page") {
                    applyStoryEditorMutation((editorStory) => {
                        const pageIndex = findStoryEditorPageIndex(editorStory, pageId);
                        if (pageIndex <= 0) return;
                        const targetPage = editorStory.pages[pageIndex];
                        const textarea = document.querySelector(
                            `[data-page-field="text"][data-page-id="${pageId}"]`,
                        );
                        const splitIndex = resolveStoryEditorSplitIndex(
                            targetPage.text,
                            textarea?.selectionStart,
                        );
                        if (splitIndex <= 0 || splitIndex >= String(targetPage.text || "").length) return;
                        const firstText = String(targetPage.text || "").slice(0, splitIndex).trim();
                        const secondText = String(targetPage.text || "").slice(splitIndex).trim();
                        if (!firstText || !secondText) return;
                        targetPage.text = firstText;
                        targetPage.editor_state.original_text = firstText;
                        const splitPage = createStoryEditorDraftPage(editorStory, {
                            text: secondText,
                            image_description: null,
                            image_path: null,
                            editor_state: {
                                original_text: secondText,
                                original_image_path: null,
                            },
                        });
                        editorStory.pages.splice(pageIndex + 1, 0, splitPage);
                        renumberStoryEditorPages(editorStory);
                    }, { refresh: "render" });
                    return;
                }
                if (action === "merge-page") {
                    applyStoryEditorMutation((editorStory) => {
                        const pageIndex = findStoryEditorPageIndex(editorStory, pageId);
                        if (pageIndex <= 0 || pageIndex >= editorStory.pages.length - 1) return;
                        const targetPage = editorStory.pages[pageIndex];
                        const nextPage = editorStory.pages[pageIndex + 1];
                        targetPage.text = [targetPage.text, nextPage.text]
                            .filter(Boolean)
                            .join("\n\n")
                            .trim();
                        targetPage.editor_state.original_text = targetPage.text;
                        editorStory.pages.splice(pageIndex + 1, 1);
                        renumberStoryEditorPages(editorStory);
                    }, { refresh: "render" });
                    return;
                }
                if (action === "restore-text" && page.id <= 0) {
                    applyStoryEditorMutation((editorStory) => {
                        const targetPage = editorStory.pages.find((item) => item.id === pageId);
                        if (!targetPage) return;
                        targetPage.text = normalizePageEditorState(targetPage).original_text || "";
                    }, { refresh: "render" });
                    return;
                }
                if (action === "restore-image" && page.id <= 0) {
                    applyStoryEditorMutation((editorStory) => {
                        const targetPage = editorStory.pages.find((item) => item.id === pageId);
                        if (!targetPage) return;
                        targetPage.image_path = normalizePageEditorState(targetPage).original_image_path || null;
                    }, { refresh: "render" });
                    return;
                }
                if ((action === "regen-image" || action === "regen-text") && page.id <= 0) {
                    displayMessage("Save the story once before regenerating this page.", "error");
                    return;
                }
                showSpinner();
                try {
                    if (action === "restore-text") {
                        await restoreStoryPageText(pageId);
                    } else if (action === "restore-image") {
                        await restoreStoryPageImage(pageId);
                    } else if (action === "regen-text") {
                        await regenerateStoryPageText(pageId);
                    } else if (action === "regen-image") {
                        await regenerateStoryPageImage(pageId);
                    }
                } catch (error) {
                    console.error("[story editor action] Error:", error);
                } finally {
                    hideSpinner();
                }
            });
        });

        setPdfActionButtonsVisibility(Boolean(story.pages && story.pages.length > 0));

        updateStoryEditorHistoryControls();
    }

    function renderStoryReadOnlyPreview() {
        const story = storyEditorState.story;
        if (!storyPreviewContent || !story) {
            console.error("[renderStoryReadOnlyPreview] Story preview content area or story data is missing.");
            displayMessage("Could not display story preview.", "error");
            setPdfActionButtonsVisibility(false);
            return;
        }

        syncStoryEditorImageCache(story);

        currentStoryId = story.id;
        storyPreviewContent.innerHTML = "";

        const shell = document.createElement("div");
        shell.className = "story-editor-shell story-editor-shell--preview";
        shell.innerHTML = `
            <div class="story-editor-toolbar">
                <div class="story-editor-title-group">
                    <span class="story-editor-field-label">Story Title</span>
                    <h2 class="story-editor-preview-title">${escapeHTML(story.title || "Untitled Story")}</h2>
                </div>
                <div class="story-editor-toolbar-actions">
                    <button type="button" id="story-preview-edit-button" class="action-button-primary">Edit Story</button>
                </div>
            </div>
            <div class="story-editor-layout">
                <aside class="story-editor-sidebar">
                    <h3>Story Settings</h3>
                    <dl class="story-editor-preview-meta">
                        <div><dt>Layout</dt><dd>${escapeHTML(getLayoutModeLabel(story.editor_settings.layout_mode || STORY_EDITOR_DEFAULTS.layout_mode))}</dd></div>
                        <div><dt>Font</dt><dd>${escapeHTML(story.editor_settings.font_family || STORY_EDITOR_DEFAULTS.font_family)}</dd></div>
                        <div><dt>Font Size</dt><dd>${Number(story.editor_settings.font_size || STORY_EDITOR_DEFAULTS.font_size)}px</dd></div>
                        <div><dt>Font Colour</dt><dd>${escapeHTML(story.editor_settings.font_color || STORY_EDITOR_DEFAULTS.font_color)}</dd></div>
                        <div><dt>Text Position</dt><dd>${escapeHTML(story.editor_settings.text_position || STORY_EDITOR_DEFAULTS.text_position)}</dd></div>
                        <div><dt>Text Alignment</dt><dd>${escapeHTML(normalizeTextAlignment(story.editor_settings.text_alignment, story.editor_settings.text_position))}</dd></div>
                        <div><dt>Readability</dt><dd>${escapeHTML(story.editor_settings.readability_treatment || "Default")}</dd></div>
                        <div><dt>Text Box Opacity</dt><dd>${Math.round(Number(story.editor_settings.text_box_opacity ?? STORY_EDITOR_DEFAULTS.text_box_opacity) * 100)}%</dd></div>
                    </dl>
                </aside>
                <div class="story-editor-pages" id="story-preview-pages"></div>
            </div>
        `;

        storyPreviewContent.appendChild(shell);
        shell.querySelector("#story-preview-edit-button")?.addEventListener("click", () => {
            renderStoryEditor();
        });

        const pagesContainer = shell.querySelector("#story-preview-pages");
        if (!story.pages || story.pages.length === 0) {
            pagesContainer.innerHTML = "<p>This story has no pages.</p>";
        } else {
            story.pages.forEach((page) => {
                const pageSettings = getPageEffectiveSettings(story, page);
                const pageCard = document.createElement("article");
                pageCard.className = "story-editor-page-card story-editor-page-card--preview";
                pageCard.innerHTML = `
                    <div class="story-editor-page-header">
                        <div>
                            <h3>${parseInt(page.page_number, 10) === 0 ? "Cover Page" : `Page ${page.page_number}`}</h3>
                            <p class="story-editor-page-subtitle">${escapeHTML(`${getLayoutModeLabel(pageSettings.layout_mode)} preset preview`)}</p>
                        </div>
                    </div>
                    <div class="story-editor-page-layout">
                        <div class="story-editor-page-preview" data-page-id="${page.id}">
                            <div class="story-editor-page-stage">
                                <div class="story-editor-page-image-slot" data-page-id="${page.id}">${page.image_path ? '<div class="story-editor-page-image story-editor-page-image--placeholder">Loading image...</div>' : '<div class="story-editor-page-image story-editor-page-image--placeholder">Image unavailable</div>'}</div>
                                <div class="story-editor-text-card">
                                    <div class="story-editor-text-card-content">${parseInt(page.page_number, 10) === 0 ? createCoverPreviewMarkup(story) : escapeHTML(page.text || "")}</div>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
                const pageStage = pageCard.querySelector(".story-editor-page-stage");
                const imageSlot = pageCard.querySelector(".story-editor-page-image-slot");
                const textCard = pageCard.querySelector(".story-editor-text-card");
                applyEditorPreviewStyles(pageStage, imageSlot, textCard, pageSettings);
                pagesContainer.appendChild(pageCard);
                void hydrateStoryPageImage(story, page);
            });
        }

        setPdfActionButtonsVisibility(Boolean(story.pages && story.pages.length > 0));
    }

    // Function to render the story preview/editor
    function displayStory(story, options = {}) {
        if (!story) {
            console.error("[displayStory] Story data is missing.");
            displayMessage("Could not display story preview.", "error");
            setPdfActionButtonsVisibility(false);
            return;
        }
        console.log("[displayStory] Story object received:", JSON.parse(JSON.stringify(story)));
        storyEditorState.story = cloneStoryForEditor(story);
        nextStoryEditorTempPageId = -1;
        storyEditorState.previewAvailable = options.previewAvailable !== false;
        clearTimeout(storyEditorState.autosaveTimer);
        storyEditorState.saveStatus = {
            state: "saved",
            message: "Saved",
            showRetry: false,
        };
        storyEditorState.story.pages.forEach((page) => {
            page.__original = JSON.parse(JSON.stringify(page));
        });
        resetStoryEditorHistory();
        if (options.mode === "preview") {
            renderStoryReadOnlyPreview();
        } else {
            renderStoryEditor();
        }
        storyPreviewContent?.scrollIntoView?.({ behavior: "instant", block: "start" });
    }

    function showSection(sectionToShow) {
        // No inline message area to clear; hide snackbar on major view change
        if (snackbarEl) snackbarEl.style.display = 'none';
        // Ensure adminPanelContainer is part of this array
        [
            authSection,
            storyCreationSection,
            storyPreviewSection,
            browseStoriesSection,
            charactersSection,
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
                setPdfActionButtonsVisibility(false);
            }
        }
    }

    function displayMessage(message, type = "info", { toast = false, persistMs = 5000 } = {}) {
        if (snackbarEl) {
            snackbarEl.textContent = String(message);
            snackbarEl.className = `snackbar snackbar--${type}`;
            snackbarEl.style.display = 'block';
            clearTimeout(displayMessage._snackbarTimer);
            displayMessage._snackbarTimer = setTimeout(() => {
                snackbarEl.style.display = 'none';
            }, persistMs);
        }
        if (toast && typeof showToast === 'function') showToast(message, type);

        // Update persistent message box content and style
        const msgBox = document.getElementById('api-message');
        if (msgBox) {
            msgBox.textContent = String(message);
            // Lightweight color cue
            let color;
            switch (type) {
                case 'success': color = '#6BFF6B'; break;
                case 'warning': color = '#FFA500'; break;
                case 'error': color = '#FF6B6B'; break;
                default: color = '#ADD8E6';
            }
            msgBox.style.color = color;
        }
    }

    function setAuthMode(mode) {
        const authSectionHeading = authSection?.querySelector("h2");
        const formsByMode = {
            login: loginForm,
            signup: signupForm,
            forgot: forgotPasswordForm,
            reset: resetPasswordForm,
        };
        const headingByMode = {
            login: "Login",
            signup: "Sign Up",
            forgot: "Forgot Password",
            reset: "Reset Password",
        };

        Object.entries(formsByMode).forEach(([key, formEl]) => {
            if (formEl) {
                formEl.style.display = key === mode ? "block" : "none";
            }
        });

        if (authSectionHeading && headingByMode[mode]) {
            authSectionHeading.textContent = headingByMode[mode];
        }
    }

    function showLoginForm() {
        setAuthMode("login");
    }

    function updateNav(isLoggedIn) {
        if (isLoggedIn) {
            navLoginSignup.style.display = "none";
            navCreateStory.style.display = "inline-block";
            navBrowseStories.style.display = "inline-block";
            if (navCharacters) navCharacters.style.display = "inline-block";
            navLogout.style.display = "inline-block";
            // Show admin link only if user is admin
            fetchAndSetUserRole(); // Call this to determine if admin link should be shown
        } else {
            navLoginSignup.style.display = "inline-block";
            navCreateStory.style.display = "none";
            navBrowseStories.style.display = "none";
            if (navCharacters) navCharacters.style.display = "none";
            navLogout.style.display = "none";
            if (navAdminPanel) navAdminPanel.style.display = "none"; // Hide admin panel link on logout
            // Explicitly hide app sections and close any character modal
            try {
                if (charactersSection) charactersSection.style.display = 'none';
                if (storyCreationSection) storyCreationSection.style.display = 'none';
                const modal = document.getElementById('char-modal');
                const backdrop = document.getElementById('char-modal-backdrop');
                if (modal) modal.classList.remove('open');
                if (backdrop) backdrop.classList.remove('open');
                if (document && document.body && document.body.dataset) {
                    delete document.body.dataset.charModalState;
                }
            } catch (e) {
                console.warn('Cleanup on logout encountered a minor issue:', e);
            }
            showSection(authSection);
        }
    }

    async function fetchAndSetUserRole() {
        if (!localStorage.getItem("authToken")) {
            if (navAdminPanel) navAdminPanel.style.display = "none";
            return;
        }
        try {
            const user = await apiRequest("/api/v1/users/me");
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

    // Toast helper
    function showToast(message, type = 'info', timeoutMs = 3200) {
        const tc = document.getElementById('toast-container');
        if (!tc) return;
        const toast = document.createElement('div');
        toast.className = `toast toast--${type}`;
        toast.textContent = String(message);
        tc.appendChild(toast);
        const t = setTimeout(() => {
            if (toast.parentNode) toast.parentNode.removeChild(toast);
        }, timeoutMs);
        toast.addEventListener('click', () => {
            clearTimeout(t);
            if (toast.parentNode) toast.parentNode.removeChild(toast);
        });
    }

    // Password toggles and strength meter
    const toggleLoginPw = document.getElementById('toggle-login-password');
    const toggleSignupPw = document.getElementById('toggle-signup-password');
    const toggleSignupPwConfirm = document.getElementById('toggle-signup-password-confirm');
    if (toggleLoginPw) toggleLoginPw.addEventListener('click', () => togglePasswordVisibility('login-password', toggleLoginPw));
    if (toggleSignupPw) toggleSignupPw.addEventListener('click', () => togglePasswordVisibility('signup-password', toggleSignupPw));
    if (toggleSignupPwConfirm) toggleSignupPwConfirm.addEventListener('click', () => togglePasswordVisibility('signup-password-confirm', toggleSignupPwConfirm));
    function togglePasswordVisibility(inputId, buttonEl) {
        const input = document.getElementById(inputId);
        if (!input) return;
        const isText = input.type === 'text';
        input.type = isText ? 'password' : 'text';
        if (buttonEl) buttonEl.textContent = isText ? 'Show' : 'Hide';
    }
    const signupPw = document.getElementById('signup-password');
    const pwStrength = document.getElementById('password-strength');
    if (signupPw && pwStrength) {
        signupPw.addEventListener('input', () => {
            const v = signupPw.value || '';
            pwStrength.textContent = `Strength: ${estimateStrength(v)}`;
        });
    }
    function estimateStrength(v) {
        let score = 0;
        if (v.length >= 8) score++;
        if (/[A-Z]/.test(v)) score++;
        if (/[0-9]/.test(v)) score++;
        if (/[^A-Za-z0-9]/.test(v)) score++;
        return ['Weak', 'Fair', 'Good', 'Strong', 'Excellent'][score] || '—';
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
                let errorDetailRaw = responseData && responseData.detail ? responseData.detail : `Unknown error. Status: ${response.status}`;
                // If FastAPI returns a list of validation errors, format them nicely
                let errorDetail;
                if (Array.isArray(errorDetailRaw)) {
                    errorDetail = errorDetailRaw.map(e => {
                        const loc = Array.isArray(e.loc) ? e.loc.join('.') : e.loc;
                        return `${loc}: ${e.msg}`;
                    }).join('\n');
                } else if (typeof errorDetailRaw === 'object') {
                    errorDetail = JSON.stringify(errorDetailRaw);
                } else {
                    errorDetail = String(errorDetailRaw);
                }
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
                } else {
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
            displayMessage(
                error.message ||
                "An unexpected error occurred. Please check the console.",
                "error",
            );
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
                `/api/v1/stories/${storyId}/title`,
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

    // (Removed duplicate POPULATE DYNAMIC FORM ELEMENTS block to avoid overriding the ID-based implementation above)
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
                storyData = await apiRequest(`/api/v1/stories/${storyId}`);
                if (storyData) {
                    showSection(storyPreviewSection);
                    displayStory(storyData, { mode: "preview", previewAvailable: true });
                } else {
                    displayMessage("Could not load story details.", "error");
                }
            }
        } catch (error) {
            console.error("[viewOrEditStory] Error:", error);
            // displayMessage is usually handled by apiRequest
            displayMessage(`Error loading story: ${error.message}`, "error");
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
            const storyData = await apiRequest(`/api/v1/stories/${storyId}`);
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
            displayMessage(
                `Error using story as template: ${error.message}`,
                "error",
            );
        } finally {
            hideSpinner();
        }
    }

    async function deleteStory(storyId) {
        if (!confirm("Are you sure you want to delete this story?")) return;
        try {
            const token = localStorage.getItem("authToken");
            const response = await fetch(`${API_BASE_URL}/api/v1/stories/${storyId}`, {
                method: "DELETE",
                headers: {
                    Authorization: `Bearer ${token}`,
                },
            });
            if (!response.ok) {
                let errorDetail = "Unknown error";
                try {
                    const errorData = await response.json();
                    errorDetail = errorData.detail || JSON.stringify(errorData);
                } catch (e) {
                    errorDetail = await response.text();
                }
                throw new Error(
                    `Delete story failed: ${response.status} ${response.statusText}. Detail: ${errorDetail}`,
                );
            }
            displayMessage("Story deleted successfully.", "success");
            // Optionally, refresh the list or navigate away
            // await loadAndDisplayUserStories();
            // showSection(browseStoriesSection);
        } catch (error) {
            console.error("[deleteStory] Error:", error);
            displayMessage(`Error deleting story: ${error.message}`, "error");
        } finally {
            hideSpinner();
        }
    }

    // Event listeners for switching between login and signup views
    if (showSignupLink) {
        showSignupLink.addEventListener("click", (e) => {
            e.preventDefault();
            setAuthMode("signup");
        });
    }

    if (showLoginLink) {
        showLoginLink.addEventListener("click", (e) => {
            e.preventDefault();
            showLoginForm();
        });
    }

    if (showForgotPasswordLink) {
        showForgotPasswordLink.addEventListener("click", (e) => {
            e.preventDefault();
            setAuthMode("forgot");
        });
    }

    if (showResetPasswordLink) {
        showResetPasswordLink.addEventListener("click", (e) => {
            e.preventDefault();
            setAuthMode("reset");
        });
    }

    if (forgotPasswordBackToLoginLink) {
        forgotPasswordBackToLoginLink.addEventListener("click", (e) => {
            e.preventDefault();
            showLoginForm();
        });
    }

    if (resetPasswordBackToLoginLink) {
        resetPasswordBackToLoginLink.addEventListener("click", (e) => {
            e.preventDefault();
            showLoginForm();
        });
    }

    if (resetPasswordRequestLink) {
        resetPasswordRequestLink.addEventListener("click", (e) => {
            e.preventDefault();
            setAuthMode("forgot");
        });
    }

    // Event listeners for navigation
    if (navCreateStory) {
        navCreateStory.addEventListener("click", () => {
            showSection(storyCreationSection);
            resetFormAndState();
            populateAllDropdowns(); // Populate dropdowns when navigating to the create form
            showSection(storyCreationSection);
            goToStep(0); // ensure wizard starts at Basics
        });
    }

    if (navBrowseStories) {
        navBrowseStories.addEventListener("click", async () => {
            showSection(browseStoriesSection);
            await loadAndDisplayUserStories();
        });
    }

    // --- AUTHENTICATION ---
    const forgotPasswordFlowPresent = Boolean(
        showForgotPasswordLink
        || forgotPasswordBackToLoginLink
        || resetPasswordRequestLink,
    );
    const resetPasswordFlowPresent = Boolean(
        showResetPasswordLink
        || resetPasswordBackToLoginLink
        || resetPasswordRequestLink
        || forgotPasswordForm,
    );

    if (!signupForm) {
        console.error("[auth] signupForm not found; signup will not work.");
    }
    if (!loginForm) {
        console.error("[auth] loginForm not found; login will not work.");
    }
    if (!forgotPasswordForm && forgotPasswordFlowPresent) {
        console.error("[auth] forgotPasswordForm not found; reset request will not work.");
    }
    if (!resetPasswordForm && resetPasswordFlowPresent) {
        console.error("[auth] resetPasswordForm not found; password reset will not work.");
    }
    if (signupForm) console.log("[auth] Signup form listener attaching...");
    signupForm && signupForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const username = signupForm.username?.value || document.getElementById('signup-username')?.value;
        const email = signupForm.email?.value || document.getElementById('signup-email')?.value;
        const password = signupForm.password?.value || document.getElementById('signup-password')?.value;
        const confirm = signupForm.password_confirm ? signupForm.password_confirm.value : document.getElementById('signup-password-confirm')?.value;
        console.log('[auth] Signup submit captured:', { username, emailMasked: !!email, hasPassword: !!password });
        if (confirm !== undefined && password !== confirm) {
            displayMessage("Passwords do not match. Please re-enter.", "error");
            return;
        }
        try {
            await apiRequest("/api/v1/users/", "POST", { username, email, password }); // Add email to payload
            displayMessage("Signup successful! Please login.", "success");
            signupForm.reset();
            showLoginForm();
        } catch (error) { }
    });

    if (loginForm) console.log("[auth] Login form listener attaching...");
    loginForm && loginForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const username = loginForm.username?.value || document.getElementById('login-username')?.value;
        const password = loginForm.password?.value || document.getElementById('login-password')?.value;

        const formData = new URLSearchParams();
        formData.append("username", username);
        formData.append("password", password);

        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/token`, {
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

    forgotPasswordForm && forgotPasswordForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const identifier =
            forgotPasswordForm.identifier?.value
            || document.getElementById("forgot-password-identifier")?.value;

        try {
            const response = await apiRequest(
                "/api/v1/password-reset/request",
                "POST",
                { identifier },
            );
            const resetTokenInput = document.getElementById("reset-password-token");
            if (response?.reset_token_preview && resetTokenInput) {
                resetTokenInput.value = response.reset_token_preview;
            }
            displayMessage(
                response?.reset_token_preview
                    ? "Reset token issued. The reset form has been prefilled for this local environment."
                    : (response?.detail || "If the account exists, a reset token has been issued."),
                "success",
                { persistMs: 5000 },
            );
            setAuthMode("reset");
        } catch (error) {
            displayMessage(
                error.message || "Could not request a password reset.",
                "error",
            );
        }
    });

    resetPasswordForm && resetPasswordForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const token =
            resetPasswordForm.token?.value
            || document.getElementById("reset-password-token")?.value;
        const newPassword =
            resetPasswordForm.new_password?.value
            || document.getElementById("reset-password-new-password")?.value;
        const confirmPassword =
            resetPasswordForm.confirm_password?.value
            || document.getElementById("reset-password-confirm-password")?.value;

        if (newPassword !== confirmPassword) {
            displayMessage("Passwords do not match. Please re-enter.", "error");
            return;
        }

        try {
            const response = await apiRequest(
                "/api/v1/password-reset/confirm",
                "POST",
                {
                    token,
                    new_password: newPassword,
                    confirm_password: confirmPassword,
                },
            );
            displayMessage(
                response?.detail || "Password reset successful.",
                "success",
            );
            resetPasswordForm.reset();
            forgotPasswordForm?.reset();
            showLoginForm();
        } catch (error) {
            displayMessage(
                error.message || "Could not reset the password.",
                "error",
            );
        }
    });

    navLogout.addEventListener("click", () => {
        authToken = null;
        localStorage.removeItem("authToken");
        updateNav(false);
        displayMessage("Logged out.", "info");
        currentStoryId = null;
        setPdfActionButtonsVisibility(false);
        closePdfPreviewModal();
    });

    // --- STORY CREATION / DRAFT HANDLING ---

    // Function to gather form data
    function getStoryDataFromForm() {
        const mainCharacters = Array.from(
            document.querySelectorAll("#main-characters-fieldset .character-entry"),
        ).map((entry) => {
            const nameInput = entry.querySelector('input[id^="char-name-"]');
            const ageInput = entry.querySelector('input[id^="char-age-"]');
            const genderInput = entry.querySelector('select[id^="char-gender-"]') || entry.querySelector('input[id^="char-gender-"]');
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
                gender: genderInput ? (genderInput.value || '').trim() : "",
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

        // Read optional enum fields; if not selected (empty string), omit them to let backend defaults apply.
        const ratioVal = document.getElementById("story-word-to-picture-ratio").value;
        const densityVal = document.getElementById("story-text-density").value;
        const imageStyleVal = document.getElementById("story-image-style").value;
        const writingStyleVal = document.getElementById("story-writing-style")?.value;
        const imageFitVal = document.getElementById("story-image-fit")?.value;
        const coverTitlePlacementVal = document.getElementById("story-cover-title-placement")?.value;
        const readabilityTreatmentVal = document.getElementById("story-readability-treatment")?.value;
        const pageFormatVal =
            document.getElementById("story-page-format")?.value
            || STORY_EDITOR_DEFAULTS.page_format;
        const layoutModeVal = normalizeLayoutMode(
            document.getElementById("story-layout-mode")?.value,
        );
        const tpV = document.getElementById("story-default-text-position-v")?.value || "bottom";
        const tpH = document.getElementById("story-default-text-position-h")?.value || "center";
        const textPositionVal = combineTextPosition(tpV, tpH);
        const fontFamilyVal = document.getElementById("story-default-font-family")?.value || STORY_EDITOR_DEFAULTS.font_family;
        const fontSizeRaw = document.getElementById("story-default-font-size")?.value;
        const fontColorVal = document.getElementById("story-default-font-color")?.value || STORY_EDITOR_DEFAULTS.font_color;
        const textBoxOpacityRaw = document.getElementById("story-default-text-box-opacity")?.value;
        const fontSizeVal = Number.parseInt(fontSizeRaw, 10);
        const textBoxOpacityVal = Number.parseFloat(textBoxOpacityRaw);

        const payload = {
            title: document.getElementById("story-title").value,
            genre: document.getElementById("story-genre").value,
            story_outline: document.getElementById("story-outline").value,
            main_characters: mainCharacters,
            num_pages: numPagesAsInt,
            tone: document.getElementById("story-tone").value,
            setting: document.getElementById("story-setting").value,
            // Phase 3: add selected existing characters by id
            character_ids: getSelectedCharacterIds(),
            editor_settings: {
                page_format: pageFormatVal,
                layout_mode: layoutModeVal,
                text_position: textPositionVal,
                font_family: fontFamilyVal,
                font_size: Number.isFinite(fontSizeVal)
                    ? fontSizeVal
                    : STORY_EDITOR_DEFAULTS.font_size,
                font_color: fontColorVal,
                text_box_opacity: Number.isFinite(textBoxOpacityVal)
                    ? textBoxOpacityVal
                    : STORY_EDITOR_DEFAULTS.text_box_opacity,
            },
        };

        if (writingStyleVal) payload.writing_style = writingStyleVal;
        if (ratioVal) payload.word_to_picture_ratio = ratioVal;
        if (densityVal) payload.text_density = densityVal;
        if (imageStyleVal) payload.image_style = imageStyleVal;
        if (imageFitVal) payload.editor_settings.image_fit = imageFitVal;
        if (coverTitlePlacementVal) {
            payload.editor_settings.cover_title_placement = coverTitlePlacementVal;
        }
        if (readabilityTreatmentVal) {
            payload.editor_settings.readability_treatment = readabilityTreatmentVal;
        }

        return payload;
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
                displayMessage(
                    `Draft saving failed: ${error.message || "Unknown error"}`,
                    "error",
                );
            } finally {
                hideSpinner();
            }
        });
    }

    // Modified Event listener for the main story creation/finalization form submission
    if (generateStoryButton) {
        generateStoryButton.addEventListener("click", async function (event) {
            event.preventDefault();
            displayMessage("Initiating story generation...", "info");

            const storyData = getStoryDataFromForm();

            // If we are editing a draft, add its ID to the payload.
            if (currentStoryId && currentStoryIsDraft) {
                storyData.draft_id = parseInt(currentStoryId);
                console.log("[FormSubmit] Finalizing draft. Payload includes draft_id:", storyData.draft_id);
            } else {
                console.log("[FormSubmit] Creating a new story from scratch.");
            }

            try {
                // Always use the public endpoint that starts a background task.
                const endpoint = "/api/v1/stories/";
                const method = "POST";

                // The endpoint returns a task object.
                const task = await apiRequest(endpoint, method, storyData);

                if (task && task.id) {
                    console.log("[FormSubmit] Story generation task started successfully. Task ID:", task.id);
                    showSection(storyCreationSection); // Stay on this section to show progress
                    pollForStoryStatus(task.id); // Start polling for status updates.
                } else {
                    console.error("[FormSubmit] Failed to start story generation task. Invalid response:", task);
                    displayMessage("Could not start story generation. The server response was not as expected.", "error");
                }
            } catch (error) {
                console.error("[FormSubmit] Error during story generation initiation:", error);
                // The apiRequest function should have already displayed an error message.
            }
        });
    }

    // --- STORY GENERATION PROGRESS POLLING ---
    // Internal configuration for polling, overridable in tests via __TEST_API__
    const __pollingConfig = {
        baseIntervalMs: 3000,
        maxIntervalMs: 15000,
        slowNoticeMs: 5 * 60 * 1000,
        maxDurationMs: 30 * 60 * 1000,
    };

    function __setPollingConfig(cfg) {
        if (!cfg || typeof cfg !== 'object') return;
        if (typeof cfg.baseIntervalMs === 'number') __pollingConfig.baseIntervalMs = cfg.baseIntervalMs;
        if (typeof cfg.maxIntervalMs === 'number') __pollingConfig.maxIntervalMs = cfg.maxIntervalMs;
        if (typeof cfg.slowNoticeMs === 'number') __pollingConfig.slowNoticeMs = cfg.slowNoticeMs;
        if (typeof cfg.maxDurationMs === 'number') __pollingConfig.maxDurationMs = cfg.maxDurationMs;
    }

    async function pollForStoryStatus(taskId) {
        const progressArea = document.getElementById("generation-progress-area");
        const statusMessage = document.getElementById("generation-status-message");
        const progressBar = document.getElementById("generation-progress-bar");

        if (!progressArea || !statusMessage || !progressBar) {
            console.error("Polling UI elements not found!");
            displayMessage("Could not show generation progress.", "warning");
            return;
        }

        progressArea.style.display = "block";
        // a11y: announce progress changes and mark busy
        progressArea.setAttribute('aria-busy', 'true');
        statusMessage.setAttribute('aria-live', 'polite');
        // Backoff and timeout settings
        const baseIntervalMs = __pollingConfig.baseIntervalMs;
        let currentIntervalMs = baseIntervalMs;
        const maxIntervalMs = __pollingConfig.maxIntervalMs;
        const startedAt = Date.now();
        const slowNoticeMs = __pollingConfig.slowNoticeMs;
        const maxDurationMs = __pollingConfig.maxDurationMs; // overridable

        let stopped = false;
        let slowNoticeShown = false;

        const poll = async () => {
            try {
                const task = await apiRequest(`/api/v1/stories/generation-status/${taskId}`);
                if (task) {
                    const status = String(task.status || '').toLowerCase();
                    // Show progress if provided
                    if (typeof task.progress === 'number') {
                        progressBar.style.width = `${task.progress}%`;
                        progressBar.textContent = `${task.progress}%`;
                    }
                    // Map status message or derive from current_step
                    const step = String(task.current_step || '').toLowerCase();
                    const stepMap = {
                        initializing: 'Initializing...',
                        generating_text: 'Generating story content...',
                        generating_character_images: 'Generating character reference images...',
                        generating_page_images: 'Generating page images...',
                        finalizing: 'Finalizing...'
                    };
                    // Backend does not return status_message; expose a helpful default
                    statusMessage.textContent = stepMap[step] || 'Processing...';

                    if (status === 'completed' || status === 'success') {
                        stopped = true;
                        statusMessage.textContent = 'Story generation complete! Loading...';
                        progressArea.style.display = 'none';
                        progressArea.setAttribute('aria-busy', 'false');
                        if (task.story_id) {
                            const storyData = await apiRequest(`/api/v1/stories/${task.story_id}`);
                            showSection(storyPreviewSection);
                            displayStory(storyData);
                        } else {
                            throw new Error("Polling complete, but no story_id was returned.");
                        }
                    } else if (status === 'failed') {
                        stopped = true;
                        progressArea.style.display = 'none';
                        progressArea.setAttribute('aria-busy', 'false');
                        // Backend surfaces failure details as last_error in the API schema
                        displayMessage(`Story generation failed: ${task.last_error || 'Unknown error'}`, 'error');
                    }
                }
            } catch (error) {
                stopped = true;
                progressArea.style.display = 'none';
                progressArea.setAttribute('aria-busy', 'false');
                console.error("Error during status polling:", error);
                displayMessage(`An error occurred while checking story progress: ${error.message}`, 'error');
            }
        };

        // Kick off immediately then schedule subsequent ticks via setTimeout (simpler & test-friendly)
        await poll();
        async function tick() {
            if (stopped) return;
            // Timeout guard
            if (Date.now() - startedAt > maxDurationMs) {
                stopped = true;
                progressArea.style.display = 'none';
                progressArea.setAttribute('aria-busy', 'false');
                displayMessage('Story generation timed out. Please try again later.', 'error');
                return;
            }
            if (!slowNoticeShown && Date.now() - startedAt > slowNoticeMs) {
                slowNoticeShown = true;
                displayMessage(
                    'Story generation is still running. This can take several minutes.',
                    'warning',
                    { persistMs: 10000 }
                );
            }
            try {
                await poll();
            } catch (e) {
                stopped = true; // poll will have reported error
                return;
            }
            // If still not stopped (status not terminal), backoff & schedule next tick
            if (!stopped) {
                if (currentIntervalMs < maxIntervalMs) {
                    currentIntervalMs = Math.min(maxIntervalMs, Math.floor(currentIntervalMs * 1.25));
                }
                setTimeout(tick, currentIntervalMs);
            }
        }
        setTimeout(tick, currentIntervalMs);
    }

    // Expose minimal test hook without polluting production behavior
    if (typeof window !== 'undefined') {
        window.__TEST_API__ = window.__TEST_API__ || {};
        window.__TEST_API__.pollForStatus = pollForStoryStatus;
        window.__TEST_API__.setPollingConfig = __setPollingConfig;
        window.__TEST_API__.displayStory = displayStory;
        window.__TEST_API__.populateCreateFormWithStoryData =
            populateCreateFormWithStoryData;
        window.__TEST_API__.viewOrEditStory = viewOrEditStory;
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
        // Show skeletons while loading
        for (let i = 0; i < 3; i++) {
            const skel = document.createElement('div');
            skel.className = 'story-item skeleton';
            skel.style.height = '84px';
            skel.style.marginBottom = '12px';
            userStoriesList.appendChild(skel);
        }

        try {
            const stories = await apiRequest(
                `/api/v1/stories/?include_drafts=${includeDrafts}&skip=0&limit=100`,
            );
            if (stories && stories.length > 0) {
                userStoriesList.innerHTML = "";
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
                    viewButton.classList.add("action-button-info");
                    viewButton.addEventListener("click", (e) => {
                        e.stopPropagation(); // Prevent triggering click on listItem
                        viewOrEditStory(story.id, story.is_draft);
                    });
                    actionsContainer.appendChild(viewButton);

                    // Use as Template Button
                    const useAsTemplateButton = document.createElement("button");
                    useAsTemplateButton.textContent = "Use as Template";
                    useAsTemplateButton.classList.add("action-button-info");
                    useAsTemplateButton.addEventListener("click", (e) => {
                        e.stopPropagation();
                        useStoryAsTemplate(story.id);
                    });
                    actionsContainer.appendChild(useAsTemplateButton);

                    // Delete Story Button
                    const deleteButton = document.createElement("button");
                    deleteButton.textContent = "Delete";
                    deleteButton.classList.add("action-button-danger");
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
            displayMessage(`Failed to load stories: ${error.message}`, "error");
            userStoriesList.innerHTML =
                "<p>Could not load stories. Please try again later.</p>";
        } finally {
            hideSpinner();
        }
    }

    if (pdfPreviewCloseButton) {
        pdfPreviewCloseButton.addEventListener("click", () => {
            closePdfPreviewModal();
        });
    }

    if (pdfPreviewBackdrop) {
        pdfPreviewBackdrop.addEventListener("click", () => {
            closePdfPreviewModal();
        });
    }

    if (pdfPreviewModal) {
        pdfPreviewModal.addEventListener("click", (event) => {
            if (event.target === pdfPreviewModal) {
                closePdfPreviewModal();
            }
        });
    }

    window.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && pdfPreviewModal?.classList.contains("open")) {
            closePdfPreviewModal();
        }
    });

    if (pdfPreviewDownloadButton) {
        pdfPreviewDownloadButton.addEventListener("click", () => {
            if (!pdfPreviewObjectUrl) {
                displayMessage("Open a PDF preview before downloading.", "error");
                return;
            }
            triggerPdfDownload(pdfPreviewObjectUrl, pdfPreviewFilename);
            displayMessage("PDF downloaded from preview.", "success");
        });
    }

    if (previewPdfButton) {
        previewPdfButton.addEventListener("click", async () => {
            if (!currentStoryId) {
                displayMessage(
                    "No story selected or story ID is missing. Cannot preview PDF.",
                    "error",
                );
                return;
            }

            openPdfPreviewModal();
            revokePdfPreviewUrl();
            setPdfPreviewLoadingState("Preparing PDF preview... Please wait.");

            try {
                const { blob, filename } = await fetchStoryPdfBlob("inline");
                pdfPreviewFilename = filename;
                pdfPreviewObjectUrl = window.URL.createObjectURL(blob);
                setPdfPreviewReadyState(pdfPreviewObjectUrl);
                displayMessage("PDF preview ready.", "success");
            } catch (error) {
                console.error("[PDFPreview] Error preparing PDF preview:", error);
                setPdfPreviewErrorState(`Error previewing PDF: ${error.message}`);
                displayMessage(`Error previewing PDF: ${error.message}`, "error");
            }
        });
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
                const { blob, filename } = await fetchStoryPdfBlob("attachment");
                const url = window.URL.createObjectURL(blob);
                triggerPdfDownload(url, filename);
                window.URL.revokeObjectURL(url);

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

        // ===== Phase 3 Additions: Wizard & Character Reuse bootstrap marker (core logic appended earlier if any) =====
        // (If needed for future progressive enhancement hooks)
        // window.__PHASE3_WIZARD__ flag prevents duplicate initialization.
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
        document.getElementById("story-writing-style").value =
            storyData.writing_style || "";
        document.getElementById("story-word-to-picture-ratio").value =
            storyData.word_to_picture_ratio || "One image per page";
        document.getElementById("story-text-density").value =
            storyData.text_density || "Concise (~30-50 words)";
        document.getElementById("story-image-style").value =
            storyData.image_style || "Default";
        const editorSettings = storyData.editor_settings || STORY_EDITOR_DEFAULTS;
        const pageFormatEl = document.getElementById("story-page-format");
        if (pageFormatEl) {
            pageFormatEl.value =
                editorSettings.page_format || STORY_EDITOR_DEFAULTS.page_format;
        }
        const layoutModeEl = document.getElementById("story-layout-mode");
        if (layoutModeEl) {
            layoutModeEl.value = normalizeLayoutMode(
                editorSettings.layout_mode || STORY_EDITOR_DEFAULTS.layout_mode,
            );
        }
        const imageFitEl = document.getElementById("story-image-fit");
        if (imageFitEl) {
            imageFitEl.value = editorSettings.image_fit || "";
        }
        const coverTitlePlacementEl = document.getElementById(
            "story-cover-title-placement",
        );
        if (coverTitlePlacementEl) {
            coverTitlePlacementEl.value =
                editorSettings.cover_title_placement || "";
        }
        const readabilityTreatmentEl = document.getElementById(
            "story-readability-treatment",
        );
        if (readabilityTreatmentEl) {
            readabilityTreatmentEl.value =
                editorSettings.readability_treatment || "";
        }
        const prefillPos = parseTextPosition(
            editorSettings.text_position || STORY_EDITOR_DEFAULTS.text_position,
        );
        const prefillVEl = document.getElementById("story-default-text-position-v");
        const prefillHEl = document.getElementById("story-default-text-position-h");
        if (prefillVEl) prefillVEl.value = prefillPos.v;
        if (prefillHEl) prefillHEl.value = prefillPos.h;
        document.getElementById("story-default-font-family").value =
            editorSettings.font_family || STORY_EDITOR_DEFAULTS.font_family;
        document.getElementById("story-default-font-size").value =
            editorSettings.font_size || STORY_EDITOR_DEFAULTS.font_size;
        document.getElementById("story-default-font-color").value =
            editorSettings.font_color || STORY_EDITOR_DEFAULTS.font_color;
        document.getElementById("story-default-text-box-opacity").value =
            editorSettings.text_box_opacity ?? STORY_EDITOR_DEFAULTS.text_box_opacity;

        const fieldset = document.getElementById("main-characters-fieldset");
        const existingEntries = fieldset.querySelectorAll(".character-entry");
        existingEntries.forEach((entry, index) => {
            if (index > 0) entry.remove();
        });
        characterCount = 0;
        characterLibraryState.selectedByIndex.clear();

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
                if (toggleButton && detailsDiv) {
                    syncCharacterDetailsDisclosure(toggleButton, detailsDiv);
                }
            });
        } else {
            characterCount = 1;
            const firstCharToggle = document.getElementById("char-details-toggle-1"); // Changed from querySelector to getElementById
            const firstCharDetails = document.getElementById("char-details-1");
            if (firstCharDetails) firstCharDetails.style.display = "none";
            if (firstCharToggle && firstCharDetails) {
                syncCharacterDetailsDisclosure(firstCharToggle, firstCharDetails);
            }
        }

        if (Array.isArray(storyData.character_ids)) {
            storyData.character_ids.forEach((id, index) => {
                if (Number.isInteger(id)) {
                    characterLibraryState.selectedByIndex.set(index + 1, {
                        id,
                        name: `#${id}`,
                    });
                }
            });
        }
        renderCharacterSelectionChips();

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
        updateStepUI();
        console.log(
            "[populateCreateFormWithStoryData] Form population complete. currentStoryId:",
            currentStoryId,
            "currentStoryIsDraft:",
            currentStoryIsDraft,
        );
    }

    function fillCharacterFormFromItem(item, index) {
        while (characterCount < index) addCharacterEntry();
        const nameEl = document.getElementById(`char-name-${index}`);
        const ageEl = document.getElementById(`char-age-${index}`);
        const genderEl = document.getElementById(`char-gender-${index}`);
        const physEl = document.getElementById(`char-physical-appearance-${index}`);
        const clothEl = document.getElementById(`char-clothing-style-${index}`);
        const traitsEl = document.getElementById(`char-key-traits-${index}`);

        if (nameEl) nameEl.value = item?.name || '';
        if (ageEl) ageEl.value = (item && item.age != null) ? item.age : '';
        if (genderEl) {
            if (genderEl.tagName === 'SELECT' && (!genderEl.options || genderEl.options.length <= 1)) {
                try { populateDropdown(`char-gender-${index}`, 'genders'); } catch (e) { }
            }
            const val = item?.gender || '';
            if (val) {
                const options = Array.from(genderEl.options || []);
                const match = options.find((option) => option.value.toLowerCase() === val.toLowerCase());
                if (match) {
                    genderEl.value = match.value;
                } else {
                    const opt = document.createElement('option');
                    opt.value = val;
                    opt.textContent = val;
                    genderEl.appendChild(opt);
                    genderEl.value = val;
                }
            } else {
                genderEl.value = '';
            }
        }
        if (physEl) physEl.value = item?.description || item?.physical_appearance || '';
        if (clothEl) clothEl.value = item?.clothing_style || '';
        if (traitsEl) traitsEl.value = item?.key_traits || '';

        const detailsDiv = document.getElementById(`char-details-${index}`);
        const toggleBtn = document.getElementById(`char-details-toggle-${index}`);
        if (detailsDiv && toggleBtn) {
            detailsDiv.style.display = 'none';
            syncCharacterDetailsDisclosure(toggleBtn, detailsDiv);
        }
    }

    async function loadCharacterLibrary() {
        const { list } = getLibraryEls();
        if (!list) {
            return;
        }

        try {
            const params = new URLSearchParams();
            if (characterLibraryState.q) params.set('q', characterLibraryState.q);
            params.set('page', String(characterLibraryState.page));
            params.set('page_size', String(characterLibraryState.pageSize));
            const res = await apiRequest(`/api/v1/characters/?${params.toString()}`);
            characterLibraryState.items = res?.items || [];
            characterLibraryState.total = res?.total || 0;
            characterLibraryState.initialized = true;
            renderCharacterList();
            renderPagination();
        } catch (err) {
            const msg = (err && err.message)
                ? `Failed to load characters: ${escapeHTML(err.message)}`
                : 'Failed to load characters.';
            list.innerHTML = `<p class="error-message">${msg}</p>`;
            console.error('[Character Library] Load failed:', err);
        }
    }

    function renderCharacterList() {
        const { list } = getLibraryEls();
        if (!list) {
            return;
        }
        if (!characterLibraryState.items.length) {
            list.innerHTML = '<p>No characters found.</p>';
            return;
        }

        const activeSelection = characterLibraryState.selectedByIndex.get(
            characterLibraryState.activeIndex,
        );
        list.innerHTML = characterLibraryState.items.map((item) => {
            const selected = activeSelection?.id === item.id;
            const imgSrc = item.thumbnail_path ? staticContentUrl(item.thumbnail_path) : '';
            return `
                <button type="button" class="character-card${selected ? ' selected' : ''}" data-id="${item.id}" aria-pressed="${selected ? 'true' : 'false'}">
                    <div class="thumb">
                        ${imgSrc ? `<img src="${imgSrc}" alt="${escapeHTML(item.name)} thumbnail">` : '<div class="no-thumb">No image</div>'}
                    </div>
                    <div class="meta">
                        <div class="name">
                            <span>${escapeHTML(item.name)}</span>
                            <span>#${item.id}</span>
                        </div>
                    </div>
                </button>`;
        }).join('');

        list.querySelectorAll('.character-card').forEach((card) => {
            card.addEventListener('click', async () => {
                const id = parseInt(card.getAttribute('data-id'), 10);
                const item = characterLibraryState.items.find((candidate) => candidate.id === id);
                if (!item) {
                    return;
                }

                let detail = item;
                try {
                    detail = await apiRequest(`/api/v1/characters/${id}`);
                } catch (err) {
                    console.warn('[Character Library] Failed to fetch detail for character', id, err);
                }

                const targetIdx = characterLibraryState.activeIndex || 1;
                fillCharacterFormFromItem(detail || item, targetIdx);
                characterLibraryState.selectedByIndex.set(targetIdx, {
                    id,
                    name: detail?.name || item.name || `#${id}`,
                });
                renderCharacterSelectionChips();
                closeCharacterPickerModal();
                displayMessage(`Loaded "${item?.name || 'Character'}" into Character ${targetIdx}.`, 'success', { persistMs: 2500 });
            });
        });
    }

    function renderPagination() {
        const { pagination } = getLibraryEls();
        if (!pagination) {
            return;
        }
        const totalPages = Math.max(1, Math.ceil(characterLibraryState.total / characterLibraryState.pageSize));
        const cur = characterLibraryState.page;
        pagination.innerHTML = `
            <button id="lib-prev" ${cur <= 1 ? 'disabled' : ''} class="action-button-secondary">Prev</button>
            <span style="margin:0 8px;">Page ${cur} of ${totalPages}</span>
            <button id="lib-next" ${cur >= totalPages ? 'disabled' : ''} class="action-button-secondary">Next</button>
        `;
        const prev = pagination.querySelector('#lib-prev');
        const next = pagination.querySelector('#lib-next');
        if (prev) prev.addEventListener('click', async () => {
            if (characterLibraryState.page > 1) {
                characterLibraryState.page -= 1;
                await loadCharacterLibrary();
            }
        });
        if (next) next.addEventListener('click', async () => {
            if (characterLibraryState.page < totalPages) {
                characterLibraryState.page += 1;
                await loadCharacterLibrary();
            }
        });
    }

    // ---- Character Library: modal picker wiring ----
    async function initCharacterLibraryUI() {
        const {
            createFromCurrentBtn,
            close,
            backdrop,
            modal,
            search,
            syncBtn,
            list,
            pagination,
        } = getLibraryEls();
        if (!list || !pagination) return;

        renderCharacterSelectionChips();

        if (syncBtn && !syncBtn._wired) {
            syncBtn.addEventListener('click', async () => {
                try {
                    displayMessage('Syncing characters from your stories...', 'info');
                    await apiRequest('/stories/backfill-characters', 'POST', { include_drafts: true });
                    await loadCharacterLibrary();
                    displayMessage('Characters synced from stories.', 'success');
                } catch (e) {
                    displayMessage('Sync failed. See console for details.', 'error');
                    console.error('[Character Sync] Error:', e);
                }
            });
            syncBtn._wired = true;
        }

        if (createFromCurrentBtn && !createFromCurrentBtn._wired) {
            createFromCurrentBtn.addEventListener('click', async () => {
                try {
                    const entries = Array.from(document.querySelectorAll('#main-characters-fieldset .character-entry'));
                    const payloads = entries.map((entry) => {
                        const name = entry.querySelector('input[id^="char-name-"]')?.value?.trim();
                        const ageVal = entry.querySelector('input[id^="char-age-"]')?.value?.trim();
                        return {
                            name: name || '',
                            description: entry.querySelector('textarea[id^="char-physical-appearance-"]')?.value?.trim() || '',
                            age: ageVal ? parseInt(ageVal, 10) : null,
                            gender: (entry.querySelector('select[id^="char-gender-"]')?.value || entry.querySelector('input[id^="char-gender-"]')?.value || '').trim(),
                            clothing_style: entry.querySelector('textarea[id^="char-clothing-style-"]')?.value?.trim() || '',
                            key_traits: entry.querySelector('textarea[id^="char-key-traits-"]')?.value?.trim() || '',
                            image_style: document.getElementById('story-image-style')?.value || undefined,
                        };
                    }).filter((character) => character.name);
                    if (payloads.length === 0) {
                        displayMessage('Add at least one character name first.', 'warning');
                        return;
                    }
                    displayMessage('Saving characters to your library...', 'info');
                    for (const payload of payloads) {
                        try {
                            await apiRequest('/api/v1/characters/', 'POST', { ...payload, generate_image: false });
                        } catch (e) {
                            console.error('[Create From Current] Failed to save character', payload.name, e);
                        }
                    }
                    await loadCharacterLibrary();
                    displayMessage('Characters saved to your library.', 'success');
                } catch (e) {
                    displayMessage('Save failed. See console for details.', 'error');
                    console.error('[Create From Current] Error:', e);
                }
            });
            createFromCurrentBtn._wired = true;
        }

        const onSearch = debounce(async () => {
            characterLibraryState.q = (search?.value || '').trim();
            characterLibraryState.page = 1;
            await loadCharacterLibrary();
        }, 300);
        if (search && !search._wired) {
            search.addEventListener('input', onSearch);
            search._wired = true;
        }
        if (close && !close._wired) {
            close.addEventListener('click', () => closeCharacterPickerModal());
            close._wired = true;
        }
        if (backdrop && !backdrop._wired) {
            backdrop.addEventListener('click', () => closeCharacterPickerModal());
            backdrop._wired = true;
        }
        if (modal && !modal._wired) {
            modal.addEventListener('click', (event) => {
                if (event.target === modal) {
                    closeCharacterPickerModal();
                }
            });
            modal._wired = true;
        }
        if (!window.__wizardCharacterPickerEscapeBound) {
            window.addEventListener('keydown', (event) => {
                if (event.key === 'Escape') {
                    const { modal: pickerModal } = getLibraryEls();
                    if (pickerModal?.classList.contains('open')) {
                        closeCharacterPickerModal();
                    }
                }
            });
            window.__wizardCharacterPickerEscapeBound = true;
        }
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
        // Track which character slot (1..N) the user last interacted with
        mainCharactersFieldset.addEventListener('focusin', function (event) {
            const el = event.target;
            if (!el || !el.id) return;
            const m = el.id.match(/-(\d+)$/);
            if (m) {
                const idx = parseInt(m[1], 10);
                if (!Number.isNaN(idx)) characterLibraryState.activeIndex = idx;
            }
        });
        mainCharactersFieldset.addEventListener("click", function (event) {
            const target = event.target;
            if (!(target instanceof HTMLElement)) return;

            if (target.classList.contains("remove-character-button")) {
                const characterEntry = target.closest(".character-entry");
                if (characterEntry) {
                    const nameInput = characterEntry.querySelector('input[id^="char-name-"]');
                    const match = nameInput?.id?.match(/-(\d+)$/);
                    const index = match ? Number.parseInt(match[1], 10) : Number.NaN;
                    if (!Number.isNaN(index)) {
                        characterLibraryState.selectedByIndex.delete(index);
                        renderCharacterSelectionChips();
                        renderCharacterList();
                    }
                    characterEntry.remove();
                    updateStepUI();
                }
                return;
            }

            if (target.classList.contains('wizard-character-picker-trigger')) {
                const idx = Number.parseInt(target.getAttribute('data-character-index'), 10);
                if (!Number.isNaN(idx)) {
                    openCharacterPickerModal(idx, target);
                }
                return;
            }

            if (target.classList.contains("character-details-toggle")) {
                console.log(
                    "[Toggle Click] Button clicked:",
                    target,
                    "ID:",
                    target.id,
                );
                const targetId = target.dataset.target;
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
                    syncCharacterDetailsDisclosure(target, detailsDiv);
                    console.log(
                        `[Toggle Click] Set detailsDiv.style.display to '${detailsDiv.style.display}', button text to '${target.textContent}'`,
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
                        const me = await apiRequest('/api/v1/users/me');
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
                actionsCell.innerHTML = `<button class="admin-save-user-changes action-button-primary">Save</button> <button class="admin-cancel-user-edit action-button-secondary">Cancel</button>`;
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
                        const me = await apiRequest('/api/v1/users/me');
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
                            await apiRequest(`/api/v1/admin/users/${id}/role`, "PUT", { role });
                            updateSuccess++;
                        } catch (err) {
                            updateErrors.push("role");
                        }
                    }
                    // Status update
                    if (active !== prevActive) {
                        updateCount++;
                        try {
                            await apiRequest(`/api/v1/admin/users/${id}/status`, "PUT", {
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
                            await apiRequest(`/api/v1/admin/users/${id}`, "PATCH", { email });
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
            const users = await apiRequest("/api/v1/admin/users");
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
            const lists = await apiRequest("/api/v1/admin/dynamic-lists/");
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
            const items = await apiRequest(`/api/v1/admin/dynamic-lists/${listName}/items`);
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
                    <button class="admin-action-button action-button-info" data-id="${item.id}" data-list="${listName}" onclick="showEditItemInput('${listName}', ${item.id})">Edit</button>
                    <button class="admin-action-button action-button-danger" data-id="${item.id}" data-list="${listName}" onclick="deleteDynamicListItem('${listName}', ${item.id})">Delete</button>
                    <button class="admin-action-button action-button-info" data-id="${item.id}" data-list="${listName}" onclick="toggleDynamicListItemActive('${listName}', ${item.id}, ${item.is_active})">${item.is_active ? 'Deactivate' : 'Activate'}</button>
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
                await apiRequest(`/api/v1/admin/dynamic-lists/${listName}/items`, 'POST', { item_value: value, item_label: label, list_name: listName });
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
                await apiRequest(`/api/v1/admin/dynamic-lists/items/${itemId}`, 'PUT', { item_value: value, item_label: label });
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
            await apiRequest(`/api/v1/admin/dynamic-lists/items/${itemId}`, 'DELETE');
            displayMessage('Item deleted!', 'success');
            loadDynamicListItems(listName);
        } catch (err) {
            displayMessage('Failed to delete item.', 'error');
        }
    };

    // --- ADMIN: TOGGLE ACTIVE/INACTIVE ---
    window.toggleDynamicListItemActive = async function (listName, itemId, isActive) {
        try {
            await apiRequest(`/api/v1/admin/dynamic-lists/items/${itemId}`, 'PUT', { is_active: !isActive });
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
    .admin-action-button, .action-button-primary, .action-button-secondary, .action-button-danger, .action-button-info {
            border: none;
            border-radius: 4px;
            padding: 6px 16px;
            font-size: 1em;
            margin: 0 2px;
            cursor: pointer;
            transition: background 0.2s, color 0.2s;
        }
    /* Button colors: primary=green (Save), secondary=grey (Cancel/Prev/Next), danger=red (Delete) */
    .action-button-primary { background: #16a34a; color: #fff; }
    .action-button-primary:hover { background: #15803d; }
    .action-button-secondary { background: #e5e7eb; color: #111827; }
    .action-button-secondary:hover { background: #d1d5db; }
    .action-button-danger { background: #ef4444; color: #fff; }
    .action-button-danger:hover { background: #dc2626; }
    .action-button-info { background: #3b82f6; color: #fff; }
    .action-button-info:hover { background: #2563eb; }
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
