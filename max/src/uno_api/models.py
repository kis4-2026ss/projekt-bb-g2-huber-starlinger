from typing import Literal

from pydantic import BaseModel, Field


class CreateGameRequest(BaseModel):
    player_name: str = Field(min_length=1, max_length=40)


class JoinGameRequest(BaseModel):
    player_name: str = Field(min_length=1, max_length=40)


class PlayerActionRequest(BaseModel):
    player_id: str = Field(min_length=1)
    action: Literal["play", "draw", "pass"]
    card_index: int | None = Field(default=None, ge=0)
    chosen_color: Literal["red", "yellow", "green", "blue"] | None = None
    declare_uno: bool = False


class ApiMessage(BaseModel):
    message: str

