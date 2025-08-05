from typing import Any

from pydantic import BaseModel


class BaseEntity(BaseModel):
    def dict(self, *args, **kwargs) -> dict[str, Any]:
        kwargs.pop("exclude_none", None)
        return super().model_dump(*args, **kwargs, exclude_none=True)

    class Config:
        from_attributes = True
