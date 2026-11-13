from typing import Literal

from pydantic import BaseModel, Field


class RecognisedItem(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    category: Literal["fresh", "packaged", "unknown"]
    confidence: float = Field(ge=0.0, le=1.0)
    label_text: list[str] = Field(default_factory=list, max_length=20)
    low_confidence: bool = False


class RecognitionResult(BaseModel):
    items: list[RecognisedItem] = Field(default_factory=list, max_length=10)
    # Always True in the MVP: the user confirms or corrects before anything
    # is saved to the pantry (blueprint: "review and correct").
    needs_confirmation: bool = True
    message: str = ""
