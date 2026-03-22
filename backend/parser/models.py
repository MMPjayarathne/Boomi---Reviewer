from pydantic import BaseModel, Field
from typing import Any


class Shape(BaseModel):
    id: str
    type: str
    label: str = ""
    # Raw XML attributes for rule inspection
    properties: dict[str, Any] = Field(default_factory=dict)


class Connection(BaseModel):
    id: str
    from_shape: str
    to_shape: str
    label: str = ""


class BoomiProcess(BaseModel):
    process_id: str = ""
    process_name: str = ""
    shapes: list[Shape] = Field(default_factory=list)
    connections: list[Connection] = Field(default_factory=list)
    # Start / end shape IDs
    start_shape_id: str = ""

    def shape_by_id(self, shape_id: str) -> Shape | None:
        return next((s for s in self.shapes if s.id == shape_id), None)
