"""MkDocs hook: internal design records stay in the repository, not on the site.

The folders and pages in INTERNAL are excluded from the build (`exclude_docs` in mkdocs.yml).
A published page that links to one of them gets the link rewritten to the file on GitHub,
for Markdown links and for raw HTML `href`s (written as site URLs, so `../specs/x/` is read as
`specs/x.md`).

Spec: docs/specs/documentation-system.md §1.
"""
from __future__ import annotations

import posixpath
import re

INTERNAL = ("specs/", "decisions/", "reviews/", "research/", "playbooks/", "plans/", "progress/W", "map.md")
REPO = "https://github.com/spectio-org/spectio/blob/main/docs/"
MD_LINK = re.compile(r"(\]\()([^)\s]+)(\))")
HREF = re.compile(r'(href=")([^"]+)(")')


def _target(page_dir: str, link: str, html: bool) -> str | None:
    """The docs path a relative link points to, or None for an absolute or in-page link."""
    if re.match(r"^[a-z][a-z0-9+.-]*:", link) or link.startswith(("#", "/")):
        return None
    path = posixpath.normpath(posixpath.join(page_dir, link.split("#", 1)[0]))
    if html and not path.endswith(".md"):
        # a site URL: "specs/x/" was specs/x.md, "progress/" was progress/index.md
        path = path.rstrip("/") + ".md"
    return path


def _rewrite(page_dir: str, html: bool):
    def sub(m: re.Match) -> str:
        link = m.group(2)
        path = _target(page_dir, link, html)
        if path is None or not path.startswith(INTERNAL):
            return m.group(0)
        anchor = "#" + link.split("#", 1)[1] if "#" in link else ""
        return f"{m.group(1)}{REPO}{path}{anchor}{m.group(3)}"
    return sub


def on_page_markdown(markdown: str, page, config, files):
    uri = page.file.src_uri
    page_dir = posixpath.dirname(uri)
    # raw HTML hrefs are site URLs, relative to the page's own folder on the site
    stem = posixpath.splitext(posixpath.basename(uri))[0]
    html_dir = page_dir if stem == "index" else posixpath.join(page_dir, stem)
    markdown = MD_LINK.sub(_rewrite(page_dir, False), markdown)
    return HREF.sub(_rewrite(html_dir, True), markdown)
