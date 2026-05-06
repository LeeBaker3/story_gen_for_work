window.STORY_GENERATOR_CONFIG = Object.assign(
    {
        // Leave empty to use localhost during local development and same-origin
        // requests elsewhere. Set this to an absolute URL to target another API.
        apiBaseUrl: "",
    },
    window.STORY_GENERATOR_CONFIG || {},
);

window.resolveStoryGeneratorApiBaseUrl = function resolveStoryGeneratorApiBaseUrl(
    locationOverride,
) {
    const configuredBaseUrl =
        typeof window.STORY_GENERATOR_CONFIG?.apiBaseUrl === "string"
            ? window.STORY_GENERATOR_CONFIG.apiBaseUrl.trim().replace(/\/$/, "")
            : "";
    const activeLocation = locationOverride || window.location;

    if (configuredBaseUrl) {
        return configuredBaseUrl;
    }

    if (
        activeLocation.hostname === "localhost" ||
        activeLocation.hostname === "127.0.0.1"
    ) {
        return "http://127.0.0.1:8000";
    }

    return String(activeLocation.origin || "").replace(/\/$/, "");
};