# Car Subscription Platform - FastAPI Backend (Week 2)

This repository contains a clean FastAPI backend for the Car Subscription Platform. It is structured for a final-year project submission and includes SQLAlchemy models, JWT auth, admin routes, and subscription swap logic.

Requirements
- PostgreSQL database
- Python 3.10+


Quick start

1. Create a Python virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

2. Configure environment (see `.env.example`).

3. Create the PostgreSQL database and set `DATABASE_URL` in your `.env`.

4. Run the app with uvicorn:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

API endpoints

- POST `/signup` — register user
- POST `/login` — get JWT (use OAuth2 password flow)
- GET `/cars` — list available cars
- POST `/subscribe` — subscribe to a car (authenticated)
- POST `/swap` — swap subscription to another car (authenticated)
- GET `/admin/cars` — admin list all cars
- POST `/admin/addcar` — admin add new car

Notes
- Change `SECRET_KEY` in `app/core/config.py` or use `.env` for production.
- Ensure `DATABASE_URL` points to a running PostgreSQL instance.
