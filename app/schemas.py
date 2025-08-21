from pydantic import BaseModel
from typing import List

class RecommendationItem(BaseModel):
  property_id: str
  score: float
  rank: int

class RecommendationOut(BaseModel):
  user_id: str
  items: List[RecommendationItem]

class SimilarOut(BaseModel):
  property_id: str
  similar: List[RecommendationItem]