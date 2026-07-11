"""Compatibility facade for the canonical coach AI boundary."""

from app.services.coach.ai import *  # noqa: F403
from app.services.coach.provider import (  # noqa: F401
    AIProvider,
    CodexCliHandoffProvider,
    LocalLLMProvider,
    ai_provider_health,
    configured_model_route_identity,
    generate_ai_coach_with_provider,
    invoke_configured_structured_model,
    prepare_ai_coach_handoff,
)
