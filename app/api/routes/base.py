"""Shared API router registration target."""

from fastapi import APIRouter

router = APIRouter(prefix="/api")

__all__ = ("router",)
