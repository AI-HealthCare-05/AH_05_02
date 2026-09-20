from pydantic import BaseModel, Field


class AvatarEquipRequest(BaseModel):
    item_ids: list[int] = Field(default_factory=list, max_length=10)
