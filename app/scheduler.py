from .db import SessionLocal
from .models import UserRecommendation, PropertySimilarity
from .recommender import generate_recommendations, compute_item_item_similarity, fetch_interactions
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler

def _recompute_once(db: Session, topn=20, topk_sim=100):
  # compute user recs
  recs, _ = generate_recommendations(db, topn=topn, topk_sim=topk_sim)

  # wipe & upsert (simple approach; switch to diff/merge if tables large)
  db.query(UserRecommendation).delete()

  # bulk insert
  bulk_rows = []
  for user_id, items in recs.items():
    for rank, (pid, score) in enumerate(items, start=1):
      bulk_rows.append(UserRecommendation(
        user_id=user_id,
        property_id=pid,
        score=score,
        rank=rank
      ))
  if bulk_rows:
      db.bulk_save_objects(bulk_rows)
  db.commit()

  # compute & store item-item similarities (optional; helpful for detail pages)
  inter = fetch_interactions(db)
  sims = compute_item_item_similarity(inter, topk=topk_sim) if not inter.empty else {}

  db.query(PropertySimilarity).delete()
  sim_rows = []
  for a, pairs in sims.items():
    for b, sim in pairs:
      sim_rows.append(PropertySimilarity(property_a=a, property_b=b, sim=sim))
  if sim_rows:
    db.bulk_save_objects(sim_rows)
  db.commit()

def run_recompute_job():
  db = SessionLocal()
  try:
    _recompute_once(db)
  finally:
    db.close()

def start_scheduler():
  scheduler = BackgroundScheduler()
  # hourly recompute; adjust as needed
  scheduler.add_job(run_recompute_job, "interval", hours=3, id="recs-hourly")
  scheduler.start()