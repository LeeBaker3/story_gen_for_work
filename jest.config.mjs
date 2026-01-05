/** @type {import('jest').Config} */
export default {
    testEnvironment: "jsdom",
    roots: ["<rootDir>/frontend/tests"],
    setupFilesAfterEnv: ["<rootDir>/frontend/tests/setup-tests.mjs"],
    moduleFileExtensions: ["js", "mjs", "json"],
    transform: {},
    reporters: [
        "default",
        ["jest-junit", { outputDirectory: "frontend/test-results", outputName: "junit.xml" }]
    ],
    coverageDirectory: "frontend/coverage",
    collectCoverageFrom: ["frontend/**/*.js", "!frontend/tests/**"]
};
