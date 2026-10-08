"""Article deduplication: URL normalization, title canonicalization, and detection."""

import re
import urllib.parse

# Known marketing and tracking parameters to strip from URLs
TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "utm_id",
    "gclid",
    "fbclid",
    "ref",
    "ref_src",
    "_ga",
    "_gl",
    "mc_cid",
    "mc_eid",
}

# Regex to detect and strip trailing publisher/outlet attribution (e.g. ' - Reuters', ' | BBC News')
OUTLET_SUFFIX_PATTERN = re.compile(
    r"\s+[-|—–]+\s+[A-Za-z0-9\s.&'\"]+$",
    flags=re.IGNORECASE,
)

# Regex to strip all punctuation and non-alphanumeric characters (preserving spaces)
PUNCTUATION_PATTERN = re.compile(r"[^\w\s]", flags=re.UNICODE)


def normalize_url(url: str) -> str:
    """Normalize a URL by canonicalizing scheme/domain and stripping tracking query params."""
    if not url:
        return ""

    parsed = urllib.parse.urlparse(url.strip())
    scheme = (parsed.scheme or "http").lower()
    netloc = parsed.netloc.lower()

    # Normalize path: remove redundant trailing slash (unless path is empty or '/')
    path = parsed.path
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")

    # Filter out tracking query parameters and sort remaining keys
    query_params = urllib.parse.parse_qsl(parsed.query, keep_blank_values=False)
    clean_params = sorted((k, v) for k, v in query_params if k.lower() not in TRACKING_PARAMS)
    query = urllib.parse.urlencode(clean_params)

    # Reconstruct canonical URL (strip fragment)
    return urllib.parse.urlunparse((scheme, netloc, path, parsed.params, query, ""))


def normalize_title(title: str) -> str:
    """Normalize a headline title for near-duplicate detection.

    Steps:
    1. Strip trailing outlet attributions (e.g. ' - Reuters', ' | BBC News').
    2. Convert to lowercase.
    3. Remove punctuation.
    4. Collapse whitespace.
    """
    if not title:
        return ""

    cleaned = title.strip()

    # Step 1: Strip trailing outlet suffixes
    cleaned = OUTLET_SUFFIX_PATTERN.sub("", cleaned)

    # Step 2: Convert to lowercase
    cleaned = cleaned.lower()

    # Step 3: Remove punctuation
    cleaned = PUNCTUATION_PATTERN.sub(" ", cleaned)

    # Step 4: Collapse whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    return cleaned
