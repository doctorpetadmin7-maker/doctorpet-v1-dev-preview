"""R7.1 — Pure, bounded image-metadata recovery from ALREADY-FETCHED article HTML.

This is a review-only adapter for a future APPROVED DailyGaewon ingestion runner.
It does NOT fetch articles/images, write files/DB, grant image rights, publish
third-party photographs or change existing collector scheduling.

Triggers permitted: one newly ingested official DailyGaewon article, OR an
already-known photo URL after a documented 404/browser decode failure.
"""

from __future__ import annotations

import hashlib
import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

SOURCE = "FEED_DAILYGAEWON"
ARTICLE_RE = re.compile(
    r"^https://www\.dailygaewon\.com/news/articleView\.html\?idxno=([1-9][0-9]{1,8})$"
)
MAX_HTML_CHARS = 1_500_000
FAILED_REASONS = frozenset({"HTTP_404", "BROWSER_DECODE_FAILED"})
SUPPORTED_CONTENT_TYPES = frozenset({"text/html", "application/xhtml+xml"})


class _OgImages(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.values: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "meta":
            return
        attributes = {str(key).lower(): val for key, val in attrs if key}
        name = (attributes.get("property") or attributes.get("name") or "").lower().strip()
        if name in {"og:image", "og:image:url", "og:image:secure_url"}:
            value = attributes.get("content")
            if value:
                self.values.append(value.strip())


def _article_no(source_id: object, article_url: object) -> str | None:
    if source_id != SOURCE or not isinstance(article_url, str):
        return None
    match = ARTICLE_RE.fullmatch(article_url)
    return match.group(1) if match else None


def _allowed_image(article_url: str, article_no: str, candidate: str) -> str | None:
    if not isinstance(candidate, str) or not candidate.strip():
        return None
    try:
        link = urljoin(article_url, candidate.strip())
        u = urlsplit(link)
    except (ValueError, TypeError):
        return None
    if u.scheme != "https" or u.hostname != "www.dailygaewon.com":
        return None
    if u.username or u.password or u.port not in (None, 443) or u.query or u.fragment:
        return None
    path_pattern = (
        r"/news/thumbnail/[0-9]{6}/" + re.escape(article_no)
        + r"_[A-Za-z0-9_.-]{1,160}\.(?:jpg|jpeg|png|webp)"
    )
    if not re.fullmatch(path_pattern, u.path, re.IGNORECASE):
        return None
    return link


def propose_metadata_delta(
    *,
    source_id: str,
    article_url: str,
    page_status: int,
    page_content_type: str,
    decoded_html: str,
    previous_photo_url: str | None,
    trigger: str,
    previous_failure: str | None = None,
) -> dict:
    """Return a candidate decision; never mutate the input or publish its URL."""
    base = {
        "sourceId": source_id,
        "articleUrl": article_url,
        "trigger": trigger,
        "rightsStatus": "PUBLISHER_PERMISSION_UNCONFIRMED",
        "publishable": False,
        "dbWrites": 0,
        "imageFileDownloads": 0,
        "candidateUrl": None,
    }
    article_no = _article_no(source_id, article_url)
    if article_no is None:
        return {**base, "decision": "REJECT_UNKNOWN_SOURCE_OR_ARTICLE"}
    if trigger not in {"NEW_ARTICLE", "BROKEN_IMAGE"}:
        return {**base, "decision": "REJECT_UNAPPROVED_TRIGGER"}
    if trigger == "NEW_ARTICLE" and previous_photo_url is not None:
        return {**base, "decision": "REJECT_NEW_ARTICLE_WITH_EXISTING_PHOTO"}
    if trigger == "BROKEN_IMAGE" and (
        not previous_photo_url or previous_failure not in FAILED_REASONS
    ):
        return {**base, "decision": "REJECT_NO_PROVEN_PHOTO_FAILURE"}
    if page_status != 200:
        return {**base, "decision": "HOLD_PAGE_NOT_200"}
    if not isinstance(page_content_type, str) or (
        page_content_type.split(";", 1)[0].strip().lower() not in SUPPORTED_CONTENT_TYPES
    ):
        return {**base, "decision": "HOLD_NON_HTML_PAGE"}
    if not isinstance(decoded_html, str) or len(decoded_html) > MAX_HTML_CHARS:
        return {**base, "decision": "HOLD_UNSAFE_OR_OVERSIZED_HTML"}
    # A decoding defect cannot be healed by a silent lossy character replacement.
    if "\ufffd" in decoded_html:
        return {**base, "decision": "HOLD_LOSSY_DECODE"}
    parser = _OgImages()
    try:
        parser.feed(decoded_html)
        parser.close()
    except (ValueError, AssertionError):
        return {**base, "decision": "HOLD_MALFORMED_HTML"}
    all_candidates = {
        u for img in parser.values
        if (u := _allowed_image(article_url, article_no, img)) is not None
    }
    if len(all_candidates) > 1:
        return {**base, "decision": "HOLD_MULTIPLE_MATCHING_IMAGES"}
    if not all_candidates:
        return {**base, "decision": "HOLD_NO_SAFE_ARTICLE_IMAGE"}
    image_url = next(iter(all_candidates))
    if trigger == "BROKEN_IMAGE" and previous_photo_url == image_url:
        return {**base, "decision": "HOLD_BROKEN_URL_STILL_CURRENT"}
    return {
        **base,
        "articleNo": article_no,
        "decision": "REVIEW_NEW_IMAGE_METADATA" if trigger == "NEW_ARTICLE" else "REVIEW_REPAIRED_IMAGE_METADATA",
        "candidateUrl": image_url,
        "replacedUrl": previous_photo_url if trigger == "BROKEN_IMAGE" else None,
        "decodedHtmlSha256": hashlib.sha256(decoded_html.encode("utf-8")).hexdigest(),
        "nextStep": "MANUAL_RIGHTS_AND_MEDIA_AUDIT_THEN_OWNER_INTEGRATION",
    }
