# Trading Platform Experiment

Personal project where I tried to copy the flow of a basic trading app. You can sign up, trade a handful of pretend resources and watch the balance jump around as the prices move.

## Main bits
- sign up and log in with JWT tokens
- five sample resources with random price shifts every few seconds
- simple tables for holdings, history and cash balance
- a pie chart so it looks less like homework

## Stack
- FastAPI, SQLite, SQLAlchemy, PyJWT, bcrypt
- Plain HTML, CSS, vanilla JavaScript and Chart.js for the chart

## Running it locally
This is what I normally do on macOS:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn server.app:app --reload
```

Then open `frontend/index.html` with Live Server or just double click it. The database gets created automatically the first time the app runs.

If you want a ready-made login, the seed data includes `testuser / password123`.

## Quick notes
- Prices jump using a tiny random change, so losses happen quite often.
- If the API calls fail the frontend falls back to hard-coded sample data, which saved me more than once during demos.
- Balances and chart data sometimes lag for a second because of the fetch cycle; refreshing sorts it.
