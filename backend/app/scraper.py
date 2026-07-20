"""
Article scraper for Shongkhep AI.

Strategy (in order of preference):
  1. newspaper3k  — handles most news sites, extracts clean article text
  2. BeautifulSoup fallback — extracts <p> tags when newspaper3k fails
  3. Raise ScraperError if both fail or content is too short

Supports Bangla news sites:
  prothomalo.com, kalerkantho.com, bdnews24.com, thedailystar.net,
  samakal.com, jugantor.com, ittefaq.com.bd, and most others.
"""
import re
import logging
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ─── Config ───────────────────────────────────────────────────────────────────

MIN_ARTICLE_LENGTH = 100   # chars — reject pages with too little text
MAX_ARTICLE_LENGTH = 10000  # chars — truncate to summarizer limit
REQUEST_TIMEOUT    = 15     # seconds

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9,bn;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# CSS selectors for common Bangla + English news sites
SITE_SELECTORS = {
    "prothomalo.com":    ["div.story-element-text", "div.article-body", "article"],
    "kalerkantho.com":   ["div.detail-body-text", "div.news-details"],
    "bdnews24.com":      ["div.print-no-display", "div.article-body"],
    "thedailystar.net":  ["div.field-items", "div#content-area"],
    "samakal.com":       ["div.details-body", "div.news-details-text"],
    "jugantor.com":      ["div.news-details-content"],
    "ittefaq.com.bd":    ["div.news-details"],
    "bbc.com":           ["article", "div[data-component='text-block']"],
    "reuters.com":       ["div.article-body", "div[class*='ArticleBody']"],
}


class ScraperError(Exception):
    """Raised when article text cannot be extracted."""
    pass


@dataclass
class ArticleResult:
    url: str
    title: str
    text: str
    source_domain: str
    char_count: int
    language_hint: str  # "bn" | "en" | "auto"


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_domain(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return ""


def _clean_text(text: str) -> str:
    """Strip excess whitespace and normalise line breaks."""
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    return text.strip()


def _detect_language_hint(domain: str, text: str) -> str:
    """Quick heuristic: if domain or text is mostly Bangla, return 'bn'."""
    bangla_domains = {
        "prothomalo.com", "kalerkantho.com", "samakal.com",
        "jugantor.com", "ittefaq.com.bd", "bd-pratidin.com",
    }
    if domain in bangla_domains:
        return "bn"
    bangla_chars = len(re.findall(r'[\u0980-\u09FF]', text))
    total_alpha  = len(re.findall(r'[a-zA-Z\u0980-\u09FF]', text))
    if total_alpha and bangla_chars / total_alpha > 0.3:
        return "bn"
    return "en"


# ─── Strategy 1: newspaper3k ─────────────────────────────────────────────────

def _scrape_with_newspaper(url: str) -> Optional[tuple[str, str]]:
    """
    Returns (title, text) or None if newspaper3k fails.
    newspaper3k handles most news sites automatically.
    """
    try:
        from newspaper import Article
        article = Article(url, language="bn")
        article.download()
        article.parse()
        text = _clean_text(article.text)
        title = article.title or ""
        if len(text) >= MIN_ARTICLE_LENGTH:
            return title, text
        return None
    except Exception as exc:
        logger.debug("newspaper3k failed for %s: %s", url, exc)
        return None


# ─── Strategy 2: BeautifulSoup ────────────────────────────────────────────────

def _scrape_with_bs4(url: str, html: str, domain: str) -> Optional[tuple[str, str]]:
    """
    Returns (title, text) extracted via BeautifulSoup.
    Uses site-specific selectors where known, falls back to <p> tags.
    """
    try:
        soup = BeautifulSoup(html, "lxml")

        # Title
        title = ""
        title_tag = soup.find("h1") or soup.find("title")
        if title_tag:
            title = title_tag.get_text(strip=True)

        # Remove noise elements
        for tag in soup(["script", "style", "nav", "footer", "header",
                         "aside", "figure", "figcaption", "iframe",
                         "noscript", "form", "button", "svg"]):
            tag.decompose()

        # Try site-specific selectors first
        text = ""
        selectors = SITE_SELECTORS.get(domain, [])
        for selector in selectors:
            container = soup.select_one(selector)
            if container:
                paragraphs = container.find_all(["p", "div"])
                text = "\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
                if len(text) >= MIN_ARTICLE_LENGTH:
                    break

        # Generic fallback — all <p> tags
        if len(text) < MIN_ARTICLE_LENGTH:
            paragraphs = soup.find_all("p")
            text = "\n".join(p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 40)

        text = _clean_text(text)
        if len(text) >= MIN_ARTICLE_LENGTH:
            return title, text
        return None

    except Exception as exc:
        logger.debug("BS4 scraping failed for %s: %s", url, exc)
        return None


# ─── Main scrape function ─────────────────────────────────────────────────────

def scrape_article(url: str) -> ArticleResult:
    """
    Fetch and extract article text from the given URL.

    Raises:
        ScraperError: if the URL is unreachable or text cannot be extracted.
    """
    # Validate URL
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ScraperError("URL must start with http:// or https://")

    domain = _get_domain(url)
    logger.info("Scraping article from %s", domain)

    # ── Strategy 1: newspaper3k ───────────────────────────────────────────────
    result = _scrape_with_newspaper(url)
    if result:
        title, text = result
        text = text[:MAX_ARTICLE_LENGTH]
        lang_hint = _detect_language_hint(domain, text)
        logger.info("newspaper3k OK — %d chars from %s", len(text), domain)
        return ArticleResult(
            url=url, title=title, text=text,
            source_domain=domain, char_count=len(text),
            language_hint=lang_hint,
        )

    # ── Strategy 2: BS4 fallback ──────────────────────────────────────────────
    try:
        with httpx.Client(
            timeout=REQUEST_TIMEOUT,
            headers=HEADERS,
            follow_redirects=True,
        ) as client:
            resp = client.get(url)
            resp.raise_for_status()
            html = resp.text
    except httpx.TimeoutException:
        raise ScraperError(f"Request timed out after {REQUEST_TIMEOUT}s — site may be slow or blocked.")
    except httpx.HTTPStatusError as exc:
        raise ScraperError(f"HTTP {exc.response.status_code} — could not fetch article.")
    except Exception as exc:
        raise ScraperError(f"Could not reach URL: {exc}")

    result = _scrape_with_bs4(url, html, domain)
    if result:
        title, text = result
        text = text[:MAX_ARTICLE_LENGTH]
        lang_hint = _detect_language_hint(domain, text)
        logger.info("BS4 OK — %d chars from %s", len(text), domain)
        return ArticleResult(
            url=url, title=title, text=text,
            source_domain=domain, char_count=len(text),
            language_hint=lang_hint,
        )

    raise ScraperError(
        "Could not extract article text from this URL. "
        "The site may require login, use JavaScript rendering, or block bots."
    )
