"""
API package for remora_ng.

Architecture:
    Three-layer data flow: Entities → Coordinator → API Client.
    Only the coordinator should call the API client. Entities must never
    import or call the API client directly.

Exception hierarchy:
    RemoraApiClientError (base)
    ├── RemoraApiClientCommunicationError (network/timeout)
    └── RemoraApiClientAuthenticationError (401/403)

Coordinator exception mapping:
    ApiClientAuthenticationError → ConfigEntryAuthFailed (triggers reauth)
    ApiClientCommunicationError → UpdateFailed (auto-retry)
    ApiClientError             → UpdateFailed (auto-retry)
"""

from .client import (
    RemoraApiClient,
    RemoraApiClientAuthenticationError,
    RemoraApiClientCommunicationError,
    RemoraApiClientError,
)

__all__ = [
    "RemoraApiClient",
    "RemoraApiClientAuthenticationError",
    "RemoraApiClientCommunicationError",
    "RemoraApiClientError",
]
