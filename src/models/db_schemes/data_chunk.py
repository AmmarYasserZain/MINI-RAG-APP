from typing import Optional
from bson.objectid import ObjectId
from pydantic import BaseModel, Field, field_validator


class DataChunk(BaseModel):
    id: Optional[ObjectId] = Field(None, alias="_id")
    chunk_text: str = Field(..., min_length=1)
    chunk_metadata: dict
    chunk_order: int = Field(..., gt=0)
    chunk_project_id: ObjectId


    model_config = {
        "arbitrary_types_allowed": True
    }