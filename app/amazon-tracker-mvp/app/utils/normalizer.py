"""URL/ASIN parsing and normalization for supported Amazon marketplaces."""

import re
from dataclasses import dataclass
from urllib.parse import urlparse

MARKETPLACE_DOMAINS: dict[str, str] = {
    "www.amazon.ae": "AE",
    "amazon.ae": "AE",
    "www.amazon.sa": "SA",
    "amazon.sa": "SA",
    "www.amazon.com.au": "AU",
    "amazon.com.au": "AU",
}

MARKETPLACE_TO_DOMAIN: dict[str, str] = {
    "AE": "www.amazon.ae",
    "SA": "www.amazon.sa",
    "AU": "www.amazon.com.au",
}

ASIN_PATTERN = re.compile(r"^[A-Z0-9]{10}$")

# Matches /dp/ASIN or /gp/product/ASIN, capturing the ASIN segment
_URL_ASIN_PATTERN = re.compile(r"/(?:dp|gp/product)/([A-Z0-9]{10})(?:/|$|\?)")


@dataclass(frozen=True)
class NormalizedProduct:
    """Immutable representation of a validated (marketplace, ASIN, canonical URL) triple."""

    marketplace: str  # "AE", "SA", "AU"
    asin: str  # 10-char alphanumeric
    url: str  # canonical URL


def normalize_input(input_str: str, marketplace: str | None = None) -> NormalizedProduct:
    """Accept a Product URL or bare ASIN (+ marketplace) and return a NormalizedProduct.

    Raises:
        ValueError: If the ASIN format is invalid, the marketplace is unsupported,
                    or a bare ASIN is given without a marketplace.
    """
    input_str = input_str.strip()

    # Determine whether the input looks like a URL
    if input_str.startswith("http://") or input_str.startswith("https://"):
        asin = extract_asin_from_url(input_str)
        detected_marketplace = detect_marketplace_from_url(input_str)
        url = build_canonical_url(detected_marketplace, asin)
        return NormalizedProduct(marketplace=detected_marketplace, asin=asin, url=url)

    # Treat as bare ASIN
    asin = input_str.upper()
    if not ASIN_PATTERN.match(asin):
        raise ValueError(f"Invalid ASIN format: '{input_str}'. ASIN must be exactly 10 alphanumeric characters.")

    if marketplace is None:
        raise ValueError("Marketplace is required when providing a bare ASIN.")

    marketplace = marketplace.upper()
    if marketplace not in MARKETPLACE_TO_DOMAIN:
        raise ValueError(
            f"Unsupported marketplace: '{marketplace}'. Supported: {', '.join(sorted(MARKETPLACE_TO_DOMAIN))}."
        )

    url = build_canonical_url(marketplace, asin)
    return NormalizedProduct(marketplace=marketplace, asin=asin, url=url)


def extract_asin_from_url(url: str) -> str:
    """Extract ASIN from Amazon product URL patterns ``/dp/ASIN`` and ``/gp/product/ASIN``.

    Raises:
        ValueError: If no valid ASIN can be found in the URL path.
    """
    parsed = urlparse(url)
    match = _URL_ASIN_PATTERN.search(parsed.path)
    if not match:
        raise ValueError(f"Cannot extract ASIN from URL: '{url}'. Expected /dp/ASIN or /gp/product/ASIN pattern.")
    return match.group(1)


def detect_marketplace_from_url(url: str) -> str:
    """Detect marketplace code from the URL domain.

    Raises:
        ValueError: If the domain is not a supported Amazon marketplace.
    """
    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    marketplace = MARKETPLACE_DOMAINS.get(hostname)
    if marketplace is None:
        raise ValueError(
            f"Unsupported marketplace domain: '{hostname}'. "
            f"Supported domains: {', '.join(sorted(MARKETPLACE_DOMAINS))}."
        )
    return marketplace


def build_canonical_url(marketplace: str, asin: str) -> str:
    """Build canonical product URL: ``https://{domain}/dp/{asin}``.

    Raises:
        ValueError: If the marketplace is not supported or the ASIN format is invalid.
    """
    marketplace = marketplace.upper()
    if marketplace not in MARKETPLACE_TO_DOMAIN:
        raise ValueError(
            f"Unsupported marketplace: '{marketplace}'. Supported: {', '.join(sorted(MARKETPLACE_TO_DOMAIN))}."
        )
    asin = asin.upper()
    if not ASIN_PATTERN.match(asin):
        raise ValueError(f"Invalid ASIN format: '{asin}'. ASIN must be exactly 10 alphanumeric characters.")
    domain = MARKETPLACE_TO_DOMAIN[marketplace]
    return f"https://{domain}/dp/{asin}"
