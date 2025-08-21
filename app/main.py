from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from .db import Base, engine, SessionLocal
from .models import UserRecommendation, PropertySimilarity
from .schemas import RecommendationOut, RecommendationItem, SimilarOut
from .scheduler import start_scheduler, run_recompute_job

Base.metadata.create_all(bind=engine)

app = FastAPI(title="AZStay Recommender")

start_scheduler()

def get_db():
  db = SessionLocal()
  try:
    yield db
  finally:
    db.close()

@app.post("/jobs/recompute")
def trigger_recompute(db: Session = Depends(get_db)):
  # synchronous recompute for testing
  run_recompute_job()
  return {"status": "ok"}

@app.get("/recommendations/{user_id}", response_model=RecommendationOut)
def get_recommendations(user_id: str, db: Session = Depends(get_db)):
  rows = (db.query(UserRecommendation)
            .filter(UserRecommendation.user_id == user_id)
            .order_by(UserRecommendation.rank.asc())
            .all())
  if not rows:
    # not found yet → ask caller to hit /jobs/recompute or return empty
    return RecommendationOut(user_id=user_id, items=[])
  items = [RecommendationItem(property_id=r.property_id, score=r.score, rank=r.rank) for r in rows]
  return RecommendationOut(user_id=user_id, items=items)

@app.get("/similar/{property_id}", response_model=SimilarOut)
def similar_properties(property_id: str, db: Session = Depends(get_db)):
  rows = (db.query(PropertySimilarity)
            .filter(PropertySimilarity.property_a == property_id)
            .order_by(PropertySimilarity.sim.desc())
            .limit(20)
            .all())
  sims = [RecommendationItem(property_id=r.property_b, score=r.sim, rank=i+1) for i, r in enumerate(rows)]
  return SimilarOut(property_id=property_id, similar=sims)
