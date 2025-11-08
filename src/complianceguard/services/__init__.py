"""External service integrations."""

from complianceguard.services.landing_ai import (
    LandingAIClient,
    get_landing_ai_client,
    parse_document_with_landing_ai,
)

__all__ = [
    "LandingAIClient",
    "get_landing_ai_client",
    "parse_document_with_landing_ai",
]
