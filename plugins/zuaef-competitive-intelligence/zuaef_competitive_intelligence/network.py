"""Public-network guard, bounded fetch and HTML/PDF text extraction.

Deterministic host-owned transport/security layer (PRD FR-4/FR-5). The tool
surface never trusts a model-supplied URL: scheme, credentials, resolved
destination addresses and every redirect hop are validated before bytes are
accepted. Extraction converts bounded server-rendered HTML or public PDFs
into useful text; empty extraction is a failure, not successful evidence.
"""

from __future__ import annotations

import io
import ipaddress
import os
import socket
import threading
import xml.etree.ElementTree as ET  # noqa: F401  (pypdf compat import surface)
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup

ALLOWED_CONTENT_TYPES = ("text/html", "text/plain", "application/pdf")

_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) zuaef-competitive-intelligence/0.1 "
    "(public research reader)"
)


class NetworkError(RuntimeError):
    """A fetch/extraction failure with a stable machine code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class FetchedDocument:
    """What a successful bounded fetch produced: identity + bytes."""

    final_url: str
    content_type: str
    data: bytes


_PROXY_ENV_LOCK = threading.Lock()


# ── public-address guard ────────────────────────────────────────────────────


def _is_public_address(address: tuple[str, int] | tuple[str, int, int, int]) -> bool:
    """IPv4/IPv6 socket address is a routable public destination."""
    host = address[0]
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False  # unevaluated hostname is never accepted as an address
    if ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_reserved:
        return False
    return not (ip.is_multicast or ip.is_unspecified)


def validate_public_url(url: str) -> httpx.URL:
    """Validate one absolute http(s) URL without touching the network.

    Raises :class:`NetworkError` (code ``URL_UNSAFE``) for a non-http(s)
    scheme, embedded credentials, unparsable URL or a host that is a
    loopback/private/link-local/reserved literal. DNS resolution is checked
    separately by :func:`assert_public_destination` at fetch time.
    """
    try:
        parsed = httpx.URL(url)
    except Exception as exc:
        raise NetworkError("URL_UNSAFE", f"could not parse URL {url!r}: {exc}") from exc
    if not parsed.is_absolute_url:
        raise NetworkError("URL_UNSAFE", f"URL must be absolute http(s), got {url!r}")
    if parsed.scheme not in ("http", "https"):
        raise NetworkError(
            "URL_UNSAFE",
            f"scheme {parsed.scheme!r} is not allowed; only http/https",
        )
    if parsed.username or parsed.password:
        raise NetworkError("URL_UNSAFE", "credential-bearing URLs are not allowed")
    host = parsed.host or ""
    lowered = host.lower().rstrip(".")
    if lowered in {"localhost", "localhost.localdomain"}:
        raise NetworkError("URL_UNSAFE", f"loopback host {host!r} is not allowed")
    # Literal non-public IPs are rejected here without DNS.
    try:
        ip = ipaddress.ip_address(lowered)
    except ValueError:
        pass
    else:
        if not _is_public_address((str(ip), 0)):
            raise NetworkError(
                "URL_UNSAFE", f"destination {host!r} is not a public address"
            )
    return parsed


def assert_public_destination(url: httpx.URL) -> None:
    """Resolve the host and require AT LEAST ONE public resolved address.

    Boundary contract: literal loopback/private/link-local/reserved IPs are
    already refused by :func:`validate_public_url` without DNS. For DNS
    hostnames this check requires at least one public record. A hostname
    whose records are all non-public (hostile split-horizon/rebinding DNS)
    is refused.

    Mixed records (one public + poisoned/placeholder non-public records, as
    seen under local TUN resolvers) are accepted: with proxy egress the
    connection resolves remotely on the proxy, so a poisoned local record
    cannot reach a private destination. Operators who deploy direct
    egress should additionally restrict outbound routing at the network
    boundary (the classic rebinding control lives in the proxy/firewall,
    not in the client).
    """
    host = (url.host or "").lower().rstrip(".")
    port = url.port or (443 if url.scheme == "https" else 80)
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise NetworkError(
            "DNS_RESOLUTION_FAILED",
            f"could not resolve host {host!r}: {exc}",
        ) from exc
    addresses = {str(info[4][0]) for info in infos}
    if not addresses:
        raise NetworkError("DNS_RESOLUTION_FAILED", f"no addresses for host {host!r}")
    if not any(_is_public_address((address, port)) for address in addresses):
        raise NetworkError(
            "URL_UNSAFE",
            f"host {host!r} has no public resolved address "
            f"(got {sorted(addresses)})",
        )


def _proxy_egress_enabled() -> bool:
    """True when the deployment routes outbound traffic through a proxy.

    Under proxy egress the proxy owns DNS and connect (remote DNS for
    socks5h/http CONNECT), so local resolver records are untrustworthy
    anyway (common TUN clients serve fake-IP records). DNS-based
    destination validation then does not apply; the operator's proxy/
    firewall is the egress boundary. Without any proxy environment,
    direct egress keeps the DNS validation.
    """
    from urllib.request import getproxies

    return any(getproxies().get(scheme) for scheme in ("http", "https", "all"))


def _validate_fetch_target(url: str) -> httpx.URL:
    parsed = validate_public_url(url)
    if not _proxy_egress_enabled():
        assert_public_destination(parsed)
    return parsed


# ── bounded fetch ───────────────────────────────────────────────────────────


def fetch_document(
    url: str,
    client: httpx.Client,
    *,
    max_bytes: int,
    max_redirects: int = 5,
    allowed_types: tuple[str, ...] = ALLOWED_CONTENT_TYPES,
) -> FetchedDocument:
    """GET one public URL with bounded redirects/bytes/timeout and allowed
    content types. Every redirect hop is re-validated (scheme, credentials,
    public destination) before it is followed.
    """
    _validate_fetch_target(url)
    current = str(httpx.URL(url))
    hops = 0
    while True:
        if hops > max_redirects:
            raise NetworkError(
                "TOO_MANY_REDIRECTS",
                f"more than {max_redirects} redirects from {url!r}",
            )
        hops += 1
        _validate_fetch_target(current)
        try:
            response = client.get(
                current,
                headers={"User-Agent": _UA, "Accept": "*/*"},
                follow_redirects=False,
            )
        except httpx.TimeoutException as exc:
            raise NetworkError(
                "FETCH_TIMEOUT", f"timed out fetching {current!r}: {exc}"
            ) from exc
        except httpx.HTTPError as exc:
            raise NetworkError(
                "FETCH_BLOCKED",
                f"network error fetching {current!r}: {type(exc).__name__}: {exc}",
            ) from exc
        if response.status_code in (301, 302, 303, 307, 308):
            location = response.headers.get("location")
            if not location:
                raise NetworkError(
                    "FETCH_BLOCKED",
                    f"redirect from {current!r} carries no Location header",
                )
            current = str(httpx.URL(current).join(location))
            continue
        if response.status_code >= 400:
            raise NetworkError(
                "FETCH_BLOCKED",
                f"GET {current!r} returned HTTP {response.status_code}",
            )
        break

    content_type = (response.headers.get("content-type") or "").split(";", 1)[0]
    content_type = content_type.strip().lower()
    if content_type not in allowed_types:
        raise NetworkError(
            "UNSUPPORTED_CONTENT",
            f"content type {content_type or '<missing>'!r} is not supported "
            f"(allowed: {', '.join(allowed_types)})",
        )
    data = response.content
    if len(data) > max_bytes:
        raise NetworkError(
            "DOWNLOAD_TOO_LARGE",
            f"response from {current!r} is {len(data)} bytes, over the "
            f"{max_bytes}-byte cap",
        )
    return FetchedDocument(
        final_url=str(response.url),
        content_type=content_type,
        data=data,
    )


# ── extraction ──────────────────────────────────────────────────────────────


def extract_document(
    document: FetchedDocument,
) -> tuple[str, str]:
    """Return ``(title, useful_text)`` for an allowed fetched document.

    ``title`` is the document title when extractable (empty string stays
    empty — never fabricated). Empty/whitespace-only useful text raises
    ``PARSE_EMPTY``: an unreadable page is not successful evidence.
    """
    if document.content_type == "application/pdf":
        text = _pdf_text(document.data)
        return "", text
    raw = document.data.decode("utf-8", errors="replace")
    title, text = _html_document(raw)
    return title, text


def _html_document(raw: str) -> tuple[str, str]:
    soup = BeautifulSoup(raw, "html.parser")
    title = soup.title.get_text(strip=True) if soup.title else ""
    for tag in soup(["script", "style", "noscript", "svg", "template"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines()]
    body = "\n".join(line for line in lines if line)
    if not body:
        raise NetworkError("PARSE_EMPTY", "HTML contained no extractable body text")
    return title, body


def _pdf_text(data: bytes) -> str:
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        parts: list[str] = []
        for page in reader.pages[:500]:
            try:
                text = page.extract_text() or ""
            except Exception:  # noqa: BLE001 — per-page extraction is best effort
                text = ""
            parts.append(text)
    except Exception as exc:
        raise NetworkError(
            "PARSE_EMPTY", f"PDF could not be parsed: {type(exc).__name__}: {exc}"
        ) from exc
    body = "\n".join(part.strip() for part in parts if part.strip())
    if not body:
        raise NetworkError("PARSE_EMPTY", "PDF contained no extractable text")
    return body


_ALLOWED_IMAGE_TYPES = ("image/png", "image/jpeg", "image/webp", "image/gif")


def fetch_binary(
    url: str,
    client: httpx.Client,
    *,
    max_bytes: int,
    allowed_types: tuple[str, ...] = _ALLOWED_IMAGE_TYPES,
) -> FetchedDocument:
    """Same guard/fetch discipline for binary assets (images).

    Only image content types are accepted; any other byte payload is
    refused so an asset download can never drag a non-image file into the
    artifact tree.
    """
    document = fetch_document(
        url,
        client,
        max_bytes=max_bytes,
        allowed_types=allowed_types,
    )
    if document.content_type not in allowed_types:
        raise NetworkError(
            "UNSUPPORTED_CONTENT",
            f"content type {document.content_type!r} is not an allowed image "
            f"type ({', '.join(allowed_types)})",
        )
    return document


def _normalize_proxy_value(value: str) -> str:
    """curl-style ``socks://host:port`` -> httpx ``socks5h://host:port``."""
    scheme, _, rest = value.partition("://")
    if scheme.lower() == "socks" and rest:
        return f"socks5h://{rest}"
    return value


def _is_ipv4(hostname: str) -> bool:
    try:
        return isinstance(ipaddress.ip_address(hostname), ipaddress.IPv4Address)
    except ValueError:
        return False


def _is_ipv6(hostname: str) -> bool:
    try:
        return isinstance(ipaddress.ip_address(hostname), ipaddress.IPv6Address)
    except ValueError:
        return False


def make_client(timeout_seconds: float, *, env_proxies: bool = True) -> httpx.Client:
    """Bounded httpx client for this plugin's network surface.

    ``env_proxies=True`` (production): environment proxies are honored with
    the curl-style ``socks://`` shorthand normalized to httpx's
    ``socks5h://`` for the duration of client construction (httpx reads the
    environment once at ``Client.__init__`` and keeps its own NO_PROXY
    handling intact). ``env_proxies=False`` (tests): a clean client for mock
    transports.
    """
    if not env_proxies:
        return httpx.Client(
            timeout=timeout_seconds,
            limits=httpx.Limits(max_connections=8),
            trust_env=False,
            follow_redirects=False,
        )
    with _PROXY_ENV_LOCK:
        changed: list[str] = []
        saved: dict[str, str] = {}
        for name in (
            "ALL_PROXY", "HTTPS_PROXY", "HTTP_PROXY",
            "all_proxy", "https_proxy", "http_proxy",
        ):
            value = os.getenv(name)
            if value and value.lower().startswith("socks://"):
                saved[name] = value
                os.environ[name] = "socks5h://" + value[len("socks://"):]
                changed.append(name)
        try:
            return httpx.Client(
                timeout=timeout_seconds,
                limits=httpx.Limits(max_connections=8),
                trust_env=True,
                follow_redirects=False,
            )
        finally:
            for name in changed:
                os.environ[name] = saved[name]
