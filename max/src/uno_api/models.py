from typing import Literal

from pydantic import BaseModel, Field


class CreateGameRequest(BaseModel):
    player_name: str = Field(min_length=1, max_length=40)


class JoinGameRequest(BaseModel):
    player_name: str = Field(min_length=1, max_length=40)


class PlayerActionRequest(BaseModel):
    player_id: str = Field(min_length=1)
    action: Literal["play", "draw", "pass", "rule_change"]
    card_index: int | None = Field(default=None, ge=0)
    chosen_color: Literal["red", "yellow", "green", "blue"] | None = None
    declare_uno: bool = False


class MutableRulePayload(BaseModel):
    id: str | None = Field(default=None, min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=800)
    type: str = Field(default="custom", max_length=60)
    condition: dict = Field(default_factory=dict)
    effect: dict = Field(default_factory=dict)


class AddRuleRequest(BaseModel):
    player_id: str = Field(min_length=1)
    rule: MutableRulePayload


class ModifyRuleRequest(BaseModel):
    player_id: str = Field(min_length=1)
    updates: dict


class RemoveRuleRequest(BaseModel):
    player_id: str = Field(min_length=1)


class ApiMessage(BaseModel):
    message: str

