from pydantic import BaseModel
from typing import List, Optional

class ArticleOut(BaseModel):
    id: int
    url: str
    title: str
    source: str
    published_at: str
    summary: str
    class Config: from_attributes = True

class UserProfileIn(BaseModel):
    user_id: str
    interests: List[str]
