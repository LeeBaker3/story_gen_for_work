from fastapi.testclient import TestClient

from backend.main import app


def test_legal_docs_are_rendered_as_html_pages() -> None:
    """Render the repository legal pack as HTML at /legal."""

    client = TestClient(app)

    expected_docs = {
        "/legal/privacy-policy": "Privacy Policy",
        "/legal/terms-of-service": "Terms of Service",
        "/legal/acceptable-use-policy": "Acceptable Use / Content Policy",
        "/legal/copyright-ip-policy": "Copyright And IP Policy",
        "/legal/support-policy": "Support / Contact Policy",
        "/legal/refund-policy": "Refund Policy",
        "/legal/service-status": "Service Status",
    }

    for path, title in expected_docs.items():
        response = client.get(path)

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")
        assert '<article class="legal-doc-content">' in response.text
        assert title in response.text


def test_legal_docs_rewrite_internal_markdown_links() -> None:
    """Rewrite relative markdown links to the rendered legal routes."""

    client = TestClient(app)

    response = client.get("/legal/privacy-policy")

    assert response.status_code == 200
    assert 'href="/legal/subprocessors"' in response.text
    assert 'href="subprocessors.md"' not in response.text


def test_legacy_markdown_urls_redirect_to_rendered_pages() -> None:
    """Preserve old markdown URLs through a redirect to the HTML route."""

    client = TestClient(app)

    response = client.get("/legal/privacy-policy.md", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/legal/privacy-policy"