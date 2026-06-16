"""Pydantic request/response models for the API."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    password: str = ""


class ManualSignal(BaseModel):
    id: str | None = None
    title: str = ""
    url: str = ""
    author: str = ""
    platform: str = "blog"
    domain: str = ""
    org: str = ""
    text: str = ""
    talking_points: str = ""
    layers: dict[str, Any] = Field(default_factory=dict)
    kept: bool = False


class FlagUpdate(BaseModel):
    kept: bool | None = None
    dismissed: bool | None = None


class FeedbackRequest(BaseModel):
    signal_id: str | None = None
    domain: str | None = None
    was_valuable: bool


class ScorePreviewRequest(BaseModel):
    layers: dict[str, Any] = Field(default_factory=dict)


class ConfigUpdate(BaseModel):
    data: dict[str, Any]


class GenerateSignal(BaseModel):
    url: str = ""
    title: str = ""
    author: str = ""
    platform: str = ""
    domain: str = ""
    org: str = ""
    text: str = ""
    talking_points: str = ""


class GenerateRequest(BaseModel):
    output_types: list[str] = Field(default_factory=lambda: ["social-post"])
    signal: GenerateSignal = Field(default_factory=GenerateSignal)
    framework_id: str | None = None
    social_platform: str = "linkedin"
    score: float = 0.0
    tier: str = "LOG"
    layers: dict[str, Any] = Field(default_factory=dict)
    active_lens_ids: list[str] = Field(default_factory=list)
    input_mode_id: str | None = None
    persona_ids: list[str] = Field(default_factory=list)
    pov_ids: list[str] = Field(default_factory=list)
    pov_custom: str = ""
    web_research: bool = False
    variant: int = 0
    signal_id: str | None = None
