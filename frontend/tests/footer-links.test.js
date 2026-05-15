import fs from 'node:fs';
import path from 'node:path';

const expectedFooterLinks = [
    ['Privacy', '/legal/privacy-policy'],
    ['Terms', '/legal/terms-of-service'],
    ['Acceptable Use', '/legal/acceptable-use-policy'],
    ['Copyright/IP', '/legal/copyright-ip-policy'],
    ['Support', '/legal/support-policy'],
    ['Contact', '/legal/support-policy'],
    ['Refunds', '/legal/refund-policy'],
    ['Status', '/legal/service-status'],
];

function mountHtml(relativePath) {
    const htmlPath = path.resolve(process.cwd(), relativePath);
    const html = fs.readFileSync(htmlPath, 'utf8');

    document.documentElement.innerHTML = html;
}

function readFooterLinks() {
    const footer = document.querySelector('footer.app-footer');
    const links = Array.from(
        footer.querySelectorAll('.app-footer__nav a')
    ).map((link) => [link.textContent.trim(), link.getAttribute('href')]);

    return { footer, links };
}

describe('legal/support footer links', () => {
    afterEach(() => {
        document.documentElement.innerHTML = '';
    });

    test('main app HTML exposes the required footer links', () => {
        mountHtml('frontend/index.html');

        const { footer, links } = readFooterLinks();

        expect(footer).not.toBeNull();
        expect(footer.querySelector('.app-footer__brand').textContent).toContain(
            'Story Generator'
        );
        expect(links).toEqual(expectedFooterLinks);
    });

    test('admin HTML exposes the required footer links', () => {
        mountHtml('frontend/admin.html');

        const { footer, links } = readFooterLinks();

        expect(footer).not.toBeNull();
        expect(footer.querySelector('.app-footer__brand').textContent).toContain(
            'Story Generator Admin'
        );
        expect(links).toEqual(expectedFooterLinks);
    });
});