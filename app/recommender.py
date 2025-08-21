import pandas as pd
import numpy as np
from scipy.sparse import csr_matrix
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy.orm import Session
from sqlalchemy import text

WEIGHTS = {
  "booking": 5.0,
  "favorite": 4.0,
}

def fetch_interactions(db: Session) -> pd.DataFrame:
  """
  Pulls user–property interactions from your existing tables and returns:
  columns = [user_id, property_id, weight]
  """
  # bookings
  bookings = db.execute(text("""
    SELECT renter_id AS user_id, property_id, :w AS weight
    FROM booking
    WHERE renter_id IS NOT NULL AND property_id IS NOT NULL
  """), {"w": WEIGHTS["booking"]}).fetchall()
  df_b = pd.DataFrame(bookings, columns=["user_id", "property_id", "weight"])

  # favorites
  favs = db.execute(text("""
    SELECT user_id, property_id, :w AS weight
    FROM userfavorite
  """), {"w": WEIGHTS["favorite"]}).fetchall()
  df_f = pd.DataFrame(favs, columns=["user_id", "property_id", "weight"])


  # reviews bonus (scale by rating/5)
  reviews = db.execute(text("""
    SELECT rd.user_id, r.property_id, COALESCE(CAST(rd.overall_rating AS DOUBLE PRECISION), 0) / 5.0 AS weight
    FROM review_details rd
    JOIN review r ON r.review_id = rd.review_id
    WHERE rd.user_id IS NOT NULL AND r.property_id IS NOT NULL
  """)).fetchall()
  df_reviews = pd.DataFrame(reviews, columns=["user_id", "property_id", "weight"])

  frames = [df for df in [df_b, df_f, df_reviews] if not df.empty]
  if not frames:
    return pd.DataFrame(columns=["user_id", "property_id", "weight"])
  interactions = pd.concat(frames, ignore_index=True)

  # aggregate weights
  interactions = interactions.groupby(["user_id", "property_id"], as_index=False)["weight"].sum()
  return interactions


def compute_item_item_similarity(interactions: pd.DataFrame, topk: int = 100):
  """
  Build item–item cosine similarities from user–item implicit matrix.
  Returns: dict { property_id: [(other_property_id, sim), ...] }
  """
  if interactions.empty:
    return {}

  # normalize IDs as str
  interactions["user_id"] = interactions["user_id"].astype(str)
  interactions["property_id"] = interactions["property_id"].astype(str)

  users = interactions["user_id"].unique()
  items = interactions["property_id"].unique()

  user_index = {u: i for i, u in enumerate(users)}
  item_index = {p: j for j, p in enumerate(items)}
  index_item = {j: p for p, j in item_index.items()}

  # map to indices
  rows = interactions["user_id"].map(user_index)
  cols = interactions["property_id"].map(item_index)

  # --- FIX: drop any unmapped rows ---
  mask = rows.notna() & cols.notna()
  if not mask.all():
    bad_users = interactions.loc[~rows.notna(), "user_id"].unique().tolist()
    bad_items = interactions.loc[~cols.notna(), "property_id"].unique().tolist()
    print(f"[WARN] Dropping {len(interactions) - mask.sum()} interactions with unknown IDs")
    if bad_users:
      print(f"  Unknown users: {bad_users}")
    if bad_items:
      print(f"  Unknown properties: {bad_items}")
  interactions = interactions.loc[mask]

  rows = interactions["user_id"].map(user_index).astype(int).values
  cols = interactions["property_id"].map(item_index).astype(int).values
  data = interactions["weight"].astype(float).values

  # user x item matrix
  M = csr_matrix((data, (rows, cols)), shape=(len(users), len(items)))

  # item x item cosine
  sims = cosine_similarity(M.T, dense_output=False)

  # extract topk per item
  result = {}
  for j in range(sims.shape[0]):
    row = sims.getrow(j)
    coo = zip(row.indices, row.data)
    sorted_pairs = sorted(((idx, s) for idx, s in coo if idx != j),
                          key=lambda x: x[1], reverse=True)[:topk]
    result[index_item[j]] = [(index_item[idx], float(s)) for idx, s in sorted_pairs]
  return result



def most_popular_fallback(db: Session, limit: int = 50) -> pd.DataFrame:
  """
  Popular properties by recent bookings + favorites signal.
  """
  pop = db.execute(text("""
    WITH pop AS (
      SELECT property_id, COUNT(*) FILTER (WHERE src='book')*2 + COUNT(*) FILTER (WHERE src='fav') AS score
      FROM (
        SELECT property_id, 'book' AS src FROM booking WHERE property_id IS NOT NULL
        UNION ALL
        SELECT property_id, 'fav' AS src FROM userfavorite
      ) t
      GROUP BY property_id
    )
    SELECT property_id, score
    FROM pop
    ORDER BY score DESC NULLS LAST
    LIMIT :lim
  """), {"lim": limit}).fetchall()
  return pd.DataFrame(pop, columns=["property_id", "score"])


def generate_recommendations(db: Session, topn: int = 20, topk_sim: int = 100):
  """
  1) build item–item sims
  2) score per-user recommendations from items they interacted with
  3) fill with popularity fallback
  Returns dict: { user_id: [(property_id, score), ...] }
  """
  inter = fetch_interactions(db)
  if inter.empty:
    # cold start entire system → recommend popular to everyone with history-less
    pop = most_popular_fallback(db, limit=topn)
    return {}, [(row.property_id, float(row.score)) for _, row in pop.iterrows()]

  sims = compute_item_item_similarity(inter, topk=topk_sim)

  # user -> set of interacted properties
  user_hist = (
    inter.groupby("user_id")["property_id"].apply(set).to_dict()
  )

  # precompute property weights per user (their history weights)
  hist_weights = (
    inter.groupby(["user_id", "property_id"])["weight"].sum().reset_index()
  )

  # for each user, accumulate scores from similar items of their history
  recs = {}
  for user_id, u_hist in user_hist.items():
      # weights for this user’s history
    u_hw = hist_weights[hist_weights["user_id"] == user_id][["property_id", "weight"]]
    scores = {}
    for _, row in u_hw.iterrows():
      p = str(row["property_id"])
      w = float(row["weight"])
      for (q, sim) in sims.get(p, []):
        if q in u_hist:
          continue  # don’t recommend seen
        scores[q] = scores.get(q, 0.0) + w * sim

    # rank
    ranked = sorted(
      scores.items(), key=lambda x: x[1], reverse=True)[:topn]
    recs[str(user_id)] = ranked

  # popularity fallback for users with too-short lists
  pop = most_popular_fallback(db, limit=topn)

  def pad_with_pop(user_list: list):
    have = {p for p, _ in user_list}
    for _, row in pop.iterrows():
      if len(user_list) >= topn:
        break
      pid = str(row.property_id)
      if pid not in have:
        user_list.append((pid, float(row.score)))
    return user_list
  for u in recs:
    recs[u] = pad_with_pop(recs[u])
  return recs, None