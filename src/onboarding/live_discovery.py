"""Minimal, safe live careers-page discovery helpers."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from html import unescape
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser

from bs4 import BeautifulSoup

from classifier.ats_detector import detect_ats_type

DISCOVERY_KEYWORDS = (
    "careers",
    "career",
    "jobs",
    "job",
    "join-us",
    "join us",
    "work-with-us",
    "work with us",
    "opportunities",
    "employment",
    "life-at",
    "teams",
    "open-roles",
    "open roles",
)
CAREERS_PATH_SEGMENTS = {
    "careers",
    "career",
    "jobs",
    "job",
    "join-us",
    "work-with-us",
    "opportunities",
    "employment",
    "open-roles",
}
MAX_DEFAULT_PAGES = 8
MAX_DEFAULT_DEPTH = 2


@dataclass(slots=True)
class FetchedPage:
    """Fetched HTML page metadata."""

    requested_url: str
    final_url: str
    status_code: int
    text: str
    content_type: str


@dataclass(slots=True)
class DiscoveryFinding:
    """One discovered candidate link or fallback result."""

    url: str | None
    candidate_kind: str
    confidence: str
    reason: str
    evidence: list[str] = field(default_factory=list)
    ats_type: str | None = None
    parent_url: str | None = None
    matched_text: str | None = None
    restricted: bool = False


FetchPageFunc = Callable[[str, int], FetchedPage]
RobotsAllowedFunc = Callable[[str], bool]


def _normalize_url(url: str | None) -> str | None:
    text = str(url or "").strip()
    if not text:
        return None
    parsed = urlparse(text)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    query = f"?{parsed.query}" if parsed.query else ""
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{path}{query}"


def _root_url(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"


def _same_domain(url: str, seed_domains: set[str]) -> bool:
    hostname = urlparse(url).netloc.lower()
    return any(hostname == domain or hostname.endswith(f".{domain}") for domain in seed_domains)


def _registered_seed_domains(start_urls: Iterable[str]) -> set[str]:
    return {
        urlparse(url).netloc.lower()
        for url in start_urls
        if _normalize_url(url)
    }


def _text_has_discovery_keyword(text: str) -> bool:
    return any(keyword in text.lower() for keyword in DISCOVERY_KEYWORDS)


def _path_segments(url: str, *, drop_locale_prefix: bool = False) -> list[str]:
    segments = [segment.lower() for segment in urlparse(url).path.split("/") if segment]
    if drop_locale_prefix and len(segments) > 1 and _looks_like_locale_segment(segments[0]):
        return segments[1:]
    return segments


def _looks_like_locale_segment(segment: str) -> bool:
    parts = segment.split("-")
    return len(parts) in {1, 2} and all(len(part) == 2 and part.isalpha() for part in parts)


def _is_probable_careers_index_url(url: str) -> bool:
    segments = _path_segments(url, drop_locale_prefix=True)
    if not segments:
        return False
    if not any(segment in CAREERS_PATH_SEGMENTS for segment in segments):
        return False
    if len(segments) > 3:
        return False
    if segments[-1].isdigit():
        return False
    if len(segments) >= 2 and segments[0] in CAREERS_PATH_SEGMENTS and segments[1].isdigit():
        return False
    return True


def _is_equivalent_locale_variant(parent_url: str, candidate_url: str) -> bool:
    parent_segments = _path_segments(parent_url)
    candidate_segments = _path_segments(candidate_url)
    if len(parent_segments) < 2 or len(candidate_segments) < 2:
        return False
    if not _looks_like_locale_segment(parent_segments[0]):
        return False
    if not _looks_like_locale_segment(candidate_segments[0]):
        return False
    return (
        parent_segments[0] != candidate_segments[0]
        and parent_segments[1:] == candidate_segments[1:]
    )


def _should_follow_same_domain_link(url: str, text: str, parent_url: str) -> bool:
    if not _is_probable_careers_index_url(url):
        return False
    if _is_equivalent_locale_variant(parent_url, url):
        return False
    return _text_has_discovery_keyword(text) or not _is_probable_careers_index_url(parent_url)


def _default_fetch_page(url: str, timeout_seconds: int = 8) -> FetchedPage:
    request = Request(
        url,
        headers={"User-Agent": "JobDiscoveryBrowserCopilot/0.1"},
    )
    with urlopen(request, timeout=timeout_seconds) as response:
        content_type = response.headers.get("Content-Type", "")
        payload = response.read(1_000_000)
        text = payload.decode("utf-8", errors="replace")
        return FetchedPage(
            requested_url=url,
            final_url=response.geturl(),
            status_code=getattr(response, "status", 200),
            text=text,
            content_type=content_type,
        )


def build_robots_checker() -> RobotsAllowedFunc:
    """Return a cached robots.txt guard. Fail open if robots cannot be read."""

    cache: dict[str, RobotFileParser | None] = {}

    def is_allowed(url: str) -> bool:
        root = _root_url(url)
        parser = cache.get(root)
        if parser is None and root not in cache:
            robots_url = f"{root}/robots.txt"
            robot_parser = RobotFileParser()
            robot_parser.set_url(robots_url)
            try:
                robot_parser.read()
            except OSError:
                cache[root] = None
                return True
            cache[root] = robot_parser
            parser = robot_parser
        if parser is None:
            return True
        try:
            return parser.can_fetch("*", url)
        except OSError:
            return True

    return is_allowed


def _extract_links(html: str, base_url: str) -> list[tuple[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    links: list[tuple[str, str]] = []
    for anchor in soup.find_all("a", href=True):
        href = str(anchor.get("href") or "").strip()
        if not href or href.startswith(("javascript:", "mailto:", "tel:")):
            continue
        absolute_url = _normalize_url(urljoin(base_url, href))
        if not absolute_url:
            continue
        text = unescape(anchor.get_text(" ", strip=True))
        links.append((absolute_url, text))
    return links


def _candidate_from_link(
    *,
    url: str,
    text: str,
    parent_url: str,
    same_domain: bool,
) -> DiscoveryFinding | None:
    ats_type = detect_ats_type(url)

    if ats_type == "restricted_board":
        return DiscoveryFinding(
            url=url,
            candidate_kind="restricted_board",
            confidence="low",
            reason="restricted_board_candidate",
            evidence=[
                "source=ats_link",
                f"parent_url={parent_url}",
                f"matched_text={text or '-'}",
                f"link_url={url}",
            ],
            ats_type=ats_type,
            parent_url=parent_url,
            matched_text=text,
            restricted=True,
        )

    if ats_type:
        return DiscoveryFinding(
            url=url,
            candidate_kind="job_board",
            confidence="high",
            reason="live_discovery_ats_link",
            evidence=[
                "source=ats_link",
                f"parent_url={parent_url}",
                f"matched_text={text or '-'}",
                f"link_url={url}",
            ],
            ats_type=ats_type,
            parent_url=parent_url,
            matched_text=text,
        )

    if (
        same_domain
        and _is_probable_careers_index_url(url)
        and not _is_equivalent_locale_variant(parent_url, url)
        and (
            _text_has_discovery_keyword(text)
            or not _is_probable_careers_index_url(parent_url)
        )
    ):
        return DiscoveryFinding(
            url=url,
            candidate_kind="careers_page",
            confidence="medium",
            reason="live_discovery_careers_link",
            evidence=[
                "source=homepage_link",
                f"parent_url={parent_url}",
                f"matched_text={text or '-'}",
                f"link_url={url}",
            ],
            parent_url=parent_url,
            matched_text=text,
        )

    return None


def discover_live_candidates(
    *,
    company_name: str,
    start_urls: list[str],
    max_pages: int = MAX_DEFAULT_PAGES,
    max_depth: int = MAX_DEFAULT_DEPTH,
    fetch_page: FetchPageFunc | None = None,
    robots_allowed: RobotsAllowedFunc | None = None,
) -> list[DiscoveryFinding]:
    """Discover reviewable careers or ATS links from provided start URLs only."""

    normalized_start_urls = [
        normalized
        for normalized in (_normalize_url(url) for url in start_urls)
        if normalized
    ]
    if not normalized_start_urls:
        return []

    fetch_page = fetch_page or _default_fetch_page
    robots_allowed = robots_allowed or build_robots_checker()
    seed_domains = _registered_seed_domains(normalized_start_urls)
    queue: deque[tuple[str, int]] = deque((url, 0) for url in normalized_start_urls)
    visited: set[str] = set()
    findings_by_url: dict[str, DiscoveryFinding] = {}
    pages_fetched = 0

    while queue and pages_fetched < max_pages:
        current_url, depth = queue.popleft()
        if current_url in visited:
            continue
        visited.add(current_url)

        if not robots_allowed(current_url):
            continue

        try:
            page = fetch_page(current_url, 8)
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            findings_by_url.setdefault(
                current_url,
                DiscoveryFinding(
                    url=None,
                    candidate_kind="discovery_error",
                    confidence="low",
                    reason="live_discovery_failed",
                    evidence=[
                        "source=provided_website",
                        f"parent_url={current_url}",
                        f"reason={type(exc).__name__}: {exc}",
                        f"company_name={company_name}",
                    ],
                ),
            )
            continue

        pages_fetched += 1
        final_url = _normalize_url(page.final_url) or current_url
        final_ats_type = detect_ats_type(final_url)
        if final_url != current_url and (
            final_ats_type
            or _is_probable_careers_index_url(final_url)
        ):
            findings_by_url.setdefault(
                final_url,
                DiscoveryFinding(
                    url=final_url,
                    candidate_kind="redirect_target",
                    confidence="high" if final_ats_type else "medium",
                    reason="live_discovery_redirect_target",
                    evidence=[
                        "source=careers_page_link",
                        f"parent_url={current_url}",
                        "matched_text=redirect",
                        f"link_url={final_url}",
                    ],
                    ats_type=final_ats_type,
                    parent_url=current_url,
                    matched_text="redirect",
                ),
            )

        content_type = page.content_type.lower()
        if "html" not in content_type:
            continue

        links = _extract_links(page.text, final_url)
        for link_url, link_text in links:
            same_domain = _same_domain(link_url, seed_domains)
            finding = _candidate_from_link(
                url=link_url,
                text=link_text,
                parent_url=final_url,
                same_domain=same_domain,
            )
            if finding is not None:
                findings_by_url.setdefault(finding.url or final_url, finding)
            if (
                same_domain
                and depth < max_depth
                and _should_follow_same_domain_link(link_url, link_text, final_url)
                and link_url not in visited
            ):
                queue.append((link_url, depth + 1))

    if not findings_by_url:
        for url in normalized_start_urls:
            findings_by_url[url] = DiscoveryFinding(
                url=None,
                candidate_kind="homepage_only",
                confidence="low",
                reason="missing_candidate_url",
                evidence=[
                    "source=provided_website",
                    f"parent_url={url}",
                    "reason=no_careers_or_job_board_link_detected",
                    f"pages_fetched={pages_fetched}",
                ],
            )

    return list(findings_by_url.values())
