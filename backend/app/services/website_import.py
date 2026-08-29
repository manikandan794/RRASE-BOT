"""
Official website knowledge import.

Implements: Website -> Import -> Extract -> Clean -> Admin/Principal
Review -> Approve -> Knowledge Base -> RAG -> AI

This module only performs Import/Extract/Clean and saves rows with
status=PENDING. Nothing from here reaches the RAG index until a human
approves it via app/api/v1/knowledge.py - see ApprovalStatus.
"""
import logging
import re
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from app.config import get_settings

logger = logging.getLogger("rrase_college_ai.services.website_import")

MAX_PAGES = 15


class WebsiteImportError(Exception):
    pass


def _clean_html_to_text(html: str) -> tuple[str, list[str]]:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "noscript"]):
        tag.decompose()

    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    text = soup.get_text(separator="\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)
    text = "\n".join(line.strip() for line in text.split("\n") if line.strip())

    links = []
    base_netloc = None
    for a in soup.find_all("a", href=True):
        links.append(a["href"])
    return f"{title}\n{text}" if title else text, links


def import_website(base_url: str | None = None, max_pages: int = MAX_PAGES) -> list[dict]:
    """Crawls the official college site (same-domain links only, shallow),
    extracts + cleans text per page. Returns a list of dicts ready to be
    saved as WebsiteImportBatch(status=PENDING) rows - it does NOT touch
    the database itself, keeping this function easy to unit test."""
    settings = get_settings()
    base_url = base_url or settings.COLLEGE_WEBSITE_URL
    base_netloc = urlparse(base_url).netloc

    visited: set[str] = set()
    to_visit = [base_url]
    results: list[dict] = []

    with httpx.Client(timeout=15, follow_redirects=True, headers={"User-Agent": "RRASE-College-AI-Importer/1.0"}) as client:
        while to_visit and len(visited) < max_pages:
            url = to_visit.pop(0)
            if url in visited:
                continue
            visited.add(url)
            try:
                resp = client.get(url)
                resp.raise_for_status()
                content_type = resp.headers.get("content-type", "")
                if "text/html" not in content_type:
                    continue
                text, links = _clean_html_to_text(resp.text)
                if len(text.strip()) >= 50:
                    title = text.split("\n", 1)[0][:255]
                    results.append({"page_url": url, "title": title, "raw_text": text})

                for link in links:
                    absolute = urljoin(url, link)
                    parsed = urlparse(absolute)
                    if parsed.netloc == base_netloc and absolute not in visited:
                        clean_url = absolute.split("#")[0]
                        if clean_url not in to_visit:
                            to_visit.append(clean_url)
            except httpx.HTTPError as exc:
                logger.warning("Skipping %s: %s", url, exc)
                continue

    if not results:
        raise WebsiteImportError(
            f"Could not import any pages from {base_url}. The site may be "
            "unreachable from this server, or blocking automated requests."
        )
    return results
