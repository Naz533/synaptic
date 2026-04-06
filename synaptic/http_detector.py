"""
http_detector.py — Static detection of HTTP client library usage.

We do NOT monkey-patch at runtime; instead we detect *static* import of
common HTTP libraries and flag those modules as potential HTTP callers.
"""

from dataclasses import dataclass
from synaptic.parser import ImportEdge

HTTP_SIGNATURES: dict[str, str] = {
    "requests":         "requests",
    "httpx":            "httpx",
    "aiohttp":          "aiohttp",
    "urllib.request":   "urllib",
    "urllib3":          "urllib3",
    "httplib2":         "httplib2",
    "pycurl":           "pycurl",
    "tornado.httpclient": "tornado",
}


@dataclass
class HttpDependency:
    source: str       # module that imports the HTTP library
    library: str      # human-readable library name
    raw_import: str   # original import target string


def detect(edges: list[ImportEdge]) -> list[HttpDependency]:
    """Return HttpDependency entries found in the import edge list."""
    found: list[HttpDependency] = []

    for edge in edges:
        for prefix, library in HTTP_SIGNATURES.items():
            if edge.target == prefix or edge.target.startswith(prefix + "."):
                found.append(
                    HttpDependency(
                        source=edge.source,
                        library=library,
                        raw_import=edge.target,
                    )
                )
                break

    return found
