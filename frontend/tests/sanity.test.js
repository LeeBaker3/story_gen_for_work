import { screen } from '@testing-library/dom';

describe('sanity', () => {
    test('jsdom renders basic DOM', () => {
        document.body.innerHTML = `<main><h1 data-testid="title">Hello</h1></main>`;
        const title = screen.getByTestId('title');
        expect(title).toHaveTextContent('Hello');
    });

    test('fetch is mocked by default', async () => {
        const res = await fetch('/api/health');
        expect(res.ok).toBe(true);
        expect(res.status).toBe(200);
        const data = await res.json();
        expect(data).toEqual({});
    });
});
