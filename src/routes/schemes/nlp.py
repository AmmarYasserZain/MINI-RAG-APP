from typing import Optional
from pydantic import BaseModel, Field


class PushRequest(BaseModel):
    do_reset: Optional[int] = 0

class SearchRequest(BaseModel):
    text: str
    limit: Optional[int] = 5
