"""
cloud_detector.py — Identify cloud SDK usage from import edges.
"""

from dataclasses import dataclass
from synaptic.parser import ImportEdge

# Map root package prefixes → (provider, service label)
CLOUD_SIGNATURES: dict[str, tuple[str, str]] = {
    "boto3":            ("AWS", "boto3"),
    "botocore":         ("AWS", "botocore"),
    "aiobotocore":      ("AWS", "aiobotocore"),
    "google.cloud":     ("GCP", "google-cloud"),
    "google.api_core":  ("GCP", "google-api-core"),
    "firebase_admin":   ("GCP", "firebase-admin"),
    "googleapiclient":  ("GCP", "google-api-python-client"),
    "azure":            ("Azure", "azure-sdk"),
    "msrest":           ("Azure", "msrest"),
}


@dataclass
class CloudDependency:
    source: str       # module that imports the SDK
    provider: str     # AWS | GCP | Azure
    sdk: str          # human-readable SDK name
    raw_import: str   # original import target string


def detect(edges: list[ImportEdge]) -> list[CloudDependency]:
    """Return CloudDependency entries found in the import edge list."""
    found: list[CloudDependency] = []

    for edge in edges:
        for prefix, (provider, sdk) in CLOUD_SIGNATURES.items():
            if edge.target == prefix or edge.target.startswith(prefix + "."):
                found.append(
                    CloudDependency(
                        source=edge.source,
                        provider=provider,
                        sdk=sdk,
                        raw_import=edge.target,
                    )
                )
                break  # first match wins

    return found
