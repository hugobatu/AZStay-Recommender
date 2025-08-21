from sqlalchemy import Column, String, Integer, Float, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID
from .db import Base

class UserRecommendation(Base):
  __tablename__ = "user_recommendations"
  user_id = Column(UUID(as_uuid=False), primary_key=True)
  property_id = Column(UUID(as_uuid=False), primary_key=True)
  score = Column(Float, nullable=False)
  rank = Column(Integer, nullable=False)
  generated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

class PropertySimilarity(Base):
  __tablename__ = "property_similarities"
  property_a = Column(UUID(as_uuid=False), primary_key=True)
  property_b = Column(UUID(as_uuid=False), primary_key=True)
  sim = Column(Float, nullable=False)
  generated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)