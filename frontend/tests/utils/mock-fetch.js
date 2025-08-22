// Lightweight fetch mock with reset helpers. Tests can override window.fetch.
import { jest } from '@jest/globals';

const defaultResponse = (data = {}, init = {}) => ({
    ok: true,
    status: 200,
    json: async () => data,
    text: async () => JSON.stringify(data),
    headers: { get: () => 'application/json' },
    ...init,
});

beforeEach(() => {
    global.fetch = jest.fn(async () => defaultResponse());
});

afterEach(() => {
    jest.clearAllMocks();
});

export { defaultResponse };
