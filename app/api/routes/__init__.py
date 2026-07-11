"""Shallow API composition preserving the public router contract."""

from app.api.routes.base import router
from app.api.routes.coach import *  # noqa: F403
from app.api.routes.imports import *  # noqa: F403
from app.api.routes.matches import *  # noqa: F403
from app.api.routes.recommendations import *  # noqa: F403
from app.api.routes.reports import *  # noqa: F403
from app.api.routes.serializers import *  # noqa: F403

__all__ = ("router",)
