"""Serve repository legal markdown as styled HTML pages."""

from __future__ import annotations

import html
import re
from functools import lru_cache
from pathlib import Path
from typing import Final

import markdown
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse


LEGAL_DOCS_DIR = Path(__file__).resolve().parent.parent / "docs" / "legal"
LEGAL_FOOTER_LINKS: Final[tuple[tuple[str, str], ...]] = (
    ("Privacy", "privacy-policy"),
    ("Terms", "terms-of-service"),
    ("Acceptable Use", "acceptable-use-policy"),
    ("Copyright/IP", "copyright-ip-policy"),
    ("Support", "support-policy"),
    ("Contact", "support-policy"),
    ("Refunds", "refund-policy"),
    ("Status", "service-status"),
)

_SLUG_PATTERN = re.compile(r"^[a-z0-9-]+$")
_TITLE_PATTERN = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
_LOCAL_MARKDOWN_LINK_PATTERN = re.compile(
    r'href="(?P<target>(?![a-z]+:|/|#)[^"#?]+)\.md(?P<suffix>(?:[#?][^"]*)?)"',
    re.IGNORECASE,
)

router = APIRouter()


@lru_cache(maxsize=1)
def _available_legal_docs() -> dict[str, Path]:
    """Return the current legal markdown documents keyed by route slug."""

    if not LEGAL_DOCS_DIR.exists() or not LEGAL_DOCS_DIR.is_dir():
        return {}

    return {
        path.stem: path
        for path in sorted(LEGAL_DOCS_DIR.glob("*.md"))
        if path.is_file()
    }


def _resolve_legal_doc_path(slug: str) -> Path:
    """Resolve a safe legal document slug to a markdown file path."""

    if not _SLUG_PATTERN.fullmatch(slug):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    doc_path = _available_legal_docs().get(slug)
    if doc_path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    return doc_path


def _split_markdown_title(markdown_text: str, slug: str) -> tuple[str, str]:
    """Extract the primary heading and return the remaining markdown body."""

    title_match = _TITLE_PATTERN.search(markdown_text)
    if title_match is None:
        fallback_title = slug.replace("-", " ").title()
        return fallback_title, markdown_text

    title = title_match.group(1).strip()
    body = markdown_text[title_match.end():].lstrip()
    return title, body


def _rewrite_local_markdown_links(rendered_html: str) -> str:
    """Point intra-pack markdown links at rendered legal routes."""

    def replace_match(match: re.Match[str]) -> str:
        slug = Path(match.group("target")).stem
        suffix = match.group("suffix") or ""
        return f'href="/legal/{slug}{suffix}"'

    return _LOCAL_MARKDOWN_LINK_PATTERN.sub(replace_match, rendered_html)


def _render_footer_links() -> str:
    """Render the shared legal footer link set."""

    return "\n".join(
        f'                <a href="/legal/{slug}">{html.escape(label)}</a>'
        for label, slug in LEGAL_FOOTER_LINKS
    )


def _render_legal_doc_page(title: str, body_html: str) -> str:
    """Wrap rendered legal markdown in the main application shell."""

    escaped_title = html.escape(title)
    footer_links = _render_footer_links()
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escaped_title} - Story Generator</title>
    <link rel="stylesheet" href="/static/style.css">
    <link rel="icon" type="image/x-icon" href="/static/favicon.ico">
</head>
<body>
    <header>
        <h1>Story Generator</h1>
        <nav>
            <div class="nav-buttons">
                <a href="/static/index.html" class="nav-button">Return to App</a>
                <a href="/static/admin.html" class="nav-button">Admin Panel</a>
            </div>
        </nav>
    </header>

    <main class="legal-page">
        <section class="legal-page__hero" aria-label="Legal document header">
            <p class="legal-page__eyebrow">Legal</p>
            <h2>{escaped_title}</h2>
            <p class="legal-page__summary">
                This page is rendered from the repository legal markdown so the
                published content stays aligned with the source of truth.
            </p>
        </section>

        <article class="legal-doc-content">
{body_html}
        </article>
    </main>

    <footer class="app-footer">
        <div class="app-footer__content">
            <p class="app-footer__brand">&copy; 2026 Story Generator</p>
            <nav class="app-footer__nav" aria-label="Legal, support, and trust links">
{footer_links}
            </nav>
        </div>
    </footer>
</body>
</html>
"""


@router.get("/legal/{slug}.md", include_in_schema=False)
def redirect_legacy_legal_doc(slug: str) -> RedirectResponse:
    """Redirect old markdown URLs to the rendered legal page route."""

    _resolve_legal_doc_path(slug)
    return RedirectResponse(url=f"/legal/{slug}", status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@router.get("/legal/{slug}", response_class=HTMLResponse, include_in_schema=False)
def get_legal_doc(slug: str) -> HTMLResponse:
    """Serve a styled legal page rendered from the repository markdown."""

    doc_path = _resolve_legal_doc_path(slug)
    markdown_text = doc_path.read_text(encoding="utf-8")
    title, body_markdown = _split_markdown_title(markdown_text, slug)
    rendered_html = markdown.markdown(
        body_markdown,
        extensions=["extra", "sane_lists"],
    )
    page_html = _render_legal_doc_page(
        title=title,
        body_html=_rewrite_local_markdown_links(rendered_html),
    )
    return HTMLResponse(content=page_html)