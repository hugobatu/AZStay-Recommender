# AZStay-Recommender

A recommendation system for **AZStay** that suggests properties (houses/rooms) to users based on their booking history, favorites, and reviews.  
The system uses **Collaborative Filtering** and **Cosine Similarity** to generate personalized recommendations.

---

## Features
- Collects user interactions (bookings, favorites, reviews).  
- Builds a **User-Item Matrix** to represent preferences.  
- Computes **Item-Item Cosine Similarity** to find similar properties.  
- Generates personalized scores for unseen properties.  
- Returns **Top-N Recommendations** for each user.

---

## Tech Stack
- **Python 3.9+**
- **FastAPI** (backend API service)
- **SQLAlchemy** (database ORM)
- **PostgreSQL** (data storage)
- **NumPy / Pandas** (data processing)
- **Scikit-learn** (cosine similarity calculation)

---

## ⚙️ Setup & Run

### 1. Clone the repo
```bash
git clone https://github.com/your-username/AZStay-Recommender.git
cd AZStay-Recommender
```
### 2. Run startapp.bat
```bash
startapp.bat
```
