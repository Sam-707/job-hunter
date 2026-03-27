"""
Fetch a job URL and extract structured content.

Strategy (in order):
1. trafilatura — best for article-style content, good at removing nav/footer noise
2. BeautifulSoup fallback — targeted tag extraction when trafilatura gets too little
3. Raw fallback — store raw HTML content, flag as low-confidence

Returns a dict compatible with ExtractedJobData schema.
"""
import re
from typing import Any

import httpx
import trafilatura
from bs4 import BeautifulSoup

from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# Salary patterns for common formats
SALARY_PATTERNS = [
    r"\$[\d,]+(?:\s*[-–]\s*\$[\d,]+)?(?:\s*(?:per|/)\s*(?:year|yr|month|mo|hour|hr))?",
    r"€[\d,.]+(?:\s*[-–]\s*€[\d,.]+)?(?:\s*(?:per|/)\s*(?:year|yr|month|mo))?",
    r"£[\d,]+(?:\s*[-–]\s*£[\d,]+)?(?:\s*(?:per|/)\s*(?:year|yr|month|mo))?",
    r"[\d,]+(?:\s*[-–]\s*[\d,]+)?\s*(?:EUR|USD|GBP|CAD|AUD)(?:\s*(?:per|/)\s*(?:year|yr|month|mo))?",
    r"[\d,.]+[kK]\s*[-–]\s*[\d,.]+[kK]",
]

EXPERIENCE_PATTERN = re.compile(
    r"(\d+)\+?\s*(?:to|-)\s*(\d+)?\s*years?\s+(?:of\s+)?(?:professional\s+)?experience"
    r"|(\d+)\+?\s*years?\s+(?:of\s+)?(?:professional\s+)?experience",
    re.IGNORECASE,
)


async def fetch_and_extract(url: str) -> dict[str, Any]:
    """Fetch a URL and return structured extraction results."""
    raw_html = await _fetch_url(url)
    if raw_html is None:
        return _failure_result("fetch_failed", f"Could not retrieve URL: {url}")

    # Truncate if too large
    if len(raw_html) > settings.extractor_max_content_bytes:
        raw_html = raw_html[: settings.extractor_max_content_bytes]

    result = _try_trafilatura(url, raw_html)
    if result["extraction_confidence"] != "high":
        bs4_result = _try_bs4(url, raw_html)
        # Merge: prefer whichever has more fields populated
        result = _merge_results(result, bs4_result)

    result["raw_content"] = raw_html[:50_000]  # store truncated raw for debugging
    return result


async def _fetch_url(url: str) -> str | None:
    try:
        async with httpx.AsyncClient(
            headers=HEADERS,
            follow_redirects=True,
            timeout=settings.extractor_timeout_seconds,
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.text
    except httpx.HTTPStatusError as e:
        logger.warning("url_fetch_http_error", url=url, status=e.response.status_code)
        return None
    except Exception as e:
        logger.warning("url_fetch_error", url=url, error=str(e))
        return None


def _try_trafilatura(url: str, html: str) -> dict[str, Any]:
    try:
        text = trafilatura.extract(
            html,
            url=url,
            include_tables=True,
            include_links=False,
            favor_recall=True,
            deduplicate=True,
        )
        if not text or len(text.strip()) < 200:
            return _failure_result("trafilatura", "Extracted too little content")

        result = _parse_text_to_fields(text)
        result["description"] = text.strip()
        result["extraction_method"] = "trafilatura"
        result["extraction_confidence"] = "medium" if len(text) < 500 else "high"
        return result
    except Exception as e:
        logger.warning("trafilatura_error", error=str(e))
        return _failure_result("trafilatura", str(e))


def _try_bs4(url: str, html: str) -> dict[str, Any]:
    try:
        soup = BeautifulSoup(html, "lxml")

        # Remove noise
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        # Try to find job-specific containers
        description_text = _extract_description_bs4(soup)
        if not description_text:
            description_text = soup.get_text(separator="\n", strip=True)

        result = _parse_text_to_fields(description_text)
        result["description"] = description_text[:10_000]
        result["extraction_method"] = "bs4"
        result["extraction_confidence"] = "medium" if len(description_text) > 300 else "low"
        return result
    except Exception as e:
        logger.warning("bs4_error", error=str(e))
        return _failure_result("bs4", str(e))


def _extract_description_bs4(soup: BeautifulSoup) -> str:
    """Try common job-posting selectors before falling back to full text."""
    selectors = [
        '[class*="job-description"]',
        '[class*="jobDescription"]',
        '[class*="posting-description"]',
        '[id*="job-description"]',
        '[class*="description"]',
        "article",
        "main",
    ]
    for sel in selectors:
        el = soup.select_one(sel)
        if el:
            text = el.get_text(separator="\n", strip=True)
            if len(text) > 200:
                return text
    return ""


def _parse_text_to_fields(text: str) -> dict[str, Any]:
    """Extract structured fields from free-form job text."""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    result: dict[str, Any] = {
        "title": None,
        "company": None,
        "location": None,
        "employment_type": None,
        "work_mode": None,
        "salary_raw": None,
        "salary_min": None,
        "salary_max": None,
        "salary_currency": None,
        "requirements": [],
        "responsibilities": [],
        "nice_to_have": [],
        "required_experience_years": None,
    }

    # Salary
    salary_match = _find_salary(text)
    if salary_match:
        result["salary_raw"] = salary_match["raw"]
        result["salary_min"] = salary_match.get("min")
        result["salary_max"] = salary_match.get("max")
        result["salary_currency"] = salary_match.get("currency")

    # Work mode
    text_lower = text.lower()
    if any(w in text_lower for w in ["fully remote", "100% remote", "work from home", "remote-first"]):
        result["work_mode"] = "remote"
    elif "hybrid" in text_lower:
        result["work_mode"] = "hybrid"
    elif any(w in text_lower for w in ["on-site", "onsite", "in-office", "in office"]):
        result["work_mode"] = "onsite"

    # Employment type
    if any(w in text_lower for w in ["full-time", "full time", "permanent"]):
        result["employment_type"] = "full-time"
    elif any(w in text_lower for w in ["part-time", "part time"]):
        result["employment_type"] = "part-time"
    elif "contract" in text_lower or "freelance" in text_lower:
        result["employment_type"] = "contract"
    elif "internship" in text_lower or "intern" in text_lower:
        result["employment_type"] = "internship"

    # Experience years
    exp_match = EXPERIENCE_PATTERN.search(text)
    if exp_match:
        groups = exp_match.groups()
        if groups[0]:
            result["required_experience_years"] = float(groups[0])
        elif groups[2]:
            result["required_experience_years"] = float(groups[2])

    # Bullet-list extraction for requirements/responsibilities
    result["requirements"] = _extract_section(text, ["requirements", "qualifications", "what you bring", "you have", "you need"])
    result["responsibilities"] = _extract_section(text, ["responsibilities", "what you'll do", "your role", "you will", "duties"])
    result["nice_to_have"] = _extract_section(text, ["nice to have", "preferred", "bonus", "plus if you have"])

    return result


def _extract_section(text: str, keywords: list[str]) -> list[str]:
    """Find a section by keyword and extract its bullet items."""
    lines = text.split("\n")
    items = []
    in_section = False

    for i, line in enumerate(lines):
        line_lower = line.lower().strip()
        if any(kw in line_lower for kw in keywords):
            in_section = True
            continue
        if in_section:
            # End section on next header-like line
            if line_lower and not line.startswith(("•", "-", "*", "·")) and len(line) < 80 and i > 0:
                next_is_header = not lines[i].startswith((" ", "\t", "•", "-", "*"))
                if next_is_header and any(c.isupper() for c in line[:3]):
                    break
            stripped = line.lstrip("•-*· ").strip()
            if stripped and len(stripped) > 10:
                items.append(stripped)
            if len(items) > 30:  # safety cap
                break

    return items[:20]


def _find_salary(text: str) -> dict | None:
    for pattern in SALARY_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            raw = match.group(0).strip()
            nums = re.findall(r"[\d,]+", raw.replace(".", ""))
            nums = [int(n.replace(",", "")) for n in nums if n.replace(",", "").isdigit()]

            currency = "USD"
            if "€" in raw or "EUR" in raw:
                currency = "EUR"
            elif "£" in raw or "GBP" in raw:
                currency = "GBP"

            # Normalize k-suffixed salaries
            if re.search(r"[kK]", raw):
                nums = [n * 1000 if n < 1000 else n for n in nums]

            return {
                "raw": raw,
                "min": nums[0] if nums else None,
                "max": nums[1] if len(nums) > 1 else None,
                "currency": currency,
            }
    return None


def _merge_results(primary: dict, secondary: dict) -> dict:
    """Fill None fields in primary from secondary."""
    merged = primary.copy()
    for key, val in secondary.items():
        if not merged.get(key) and val:
            merged[key] = val
    return merged


def _failure_result(method: str, reason: str) -> dict[str, Any]:
    return {
        "title": None,
        "company": None,
        "location": None,
        "employment_type": None,
        "work_mode": None,
        "salary_raw": None,
        "salary_min": None,
        "salary_max": None,
        "salary_currency": None,
        "description": None,
        "requirements": [],
        "responsibilities": [],
        "nice_to_have": [],
        "required_experience_years": None,
        "extraction_method": method,
        "extraction_confidence": "failed",
        "_failure_reason": reason,
    }
