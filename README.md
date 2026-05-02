# 🎓 TrainMaster

A full-stack quiz-bowl training platform with AI-powered answer validation, real-time duel mode, and a global leaderboard.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Quick Start (Local)](#quick-start-local)
- [Environment Variables](#environment-variables)
- [Answer Validation System](#answer-validation-system)
- [Quiz JSON Format](#quiz-json-format)
- [API Overview](#api-overview)
- [Deployment (Free Tier)](#deployment-free-tier)
- [Making the First Admin](#making-the-first-admin)
- [Database Migration (SQLite → PostgreSQL)](#database-migration-sqlite--postgresql)

---

## Features

- **Solo Mode** – Take a quiz once for score; timer enforced per question; correct answer revealed after each submission.
- **Duel Mode** – Real-time 1v1 via WebSockets; invite code sharing; first correct answer wins the point.
- **Hybrid AI Validation** – Fuzzy string matching (rapidfuzz) + semantic similarity (sentence-transformers SBERT). No multiple choice — free-text answers only.
- **Flagging System** – Users can dispute a rejected answer; admins review and award points retroactively.
- **Global Leaderboard** – Persistent, updated on every quiz completion.
- **Admin Panel** – Create/edit/delete quizzes via UI or JSON upload; review flags; manage users; view stats.
- **Email Notifications** – Users are emailed when a new quiz is published (SMTP, free Gmail/SendGrid).
- **JWT Auth** – Access + refresh tokens; RBAC (user / admin).

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, TypeScript, Tailwind CSS, Zustand |
| Backend | FastAPI (async), SQLAlchemy 2, Alembic |
| Database | SQLite (dev) → PostgreSQL (prod) |
| Real-time | FastAPI WebSockets |
| AI validation | rapidfuzz + sentence-transformers (local) or HuggingFace Inference API |
| Auth | JWT (python-jose) + bcrypt |
| Logging | structlog (JSON in prod, pretty in dev) |
| Deployment | Render / Railway (backend) · Vercel / Netlify (frontend) |

---

## Project Structure

```
trainmaster/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, CORS, lifespan
│   │   ├── core/
│   │   │   ├── config.py        # All settings via env vars
│   │   │   ├── database.py      # Async SQLAlchemy engine + session
│   │   │   ├── security.py      # JWT helpers, password hashing, deps
│   │   │   └── logging.py       # structlog configuration
│   │   ├── models/
│   │   │   └── __init__.py      # All ORM models (User, Quiz, Attempt, …)
│   │   ├── schemas/
│   │   │   └── __init__.py      # Pydantic v2 request/response schemas
│   │   ├── routers/
│   │   │   ├── auth.py          # /api/auth/*
│   │   │   ├── quizzes.py       # /api/quizzes/*
│   │   │   ├── attempts.py      # /api/attempts/*
│   │   │   ├── leaderboard.py   # /api/leaderboard
│   │   │   ├── flags.py         # /api/flags/*
│   │   │   ├── admin.py         # /api/admin/*
│   │   │   └── duel.py          # /ws/duel/* (WebSocket + REST helpers)
│   │   └── services/
│   │       ├── validation.py    # Hybrid fuzzy + SBERT answer validation
│   │       └── email.py         # SMTP email notifications
│   ├── requirements.txt
│   ├── runtime.txt
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # Router, auth guards
│   │   ├── main.tsx
│   │   ├── index.css
│   │   ├── components/
│   │   │   └── Layout.tsx       # Sidebar navigation
│   │   ├── pages/
│   │   │   ├── LoginPage.tsx
│   │   │   ├── RegisterPage.tsx
│   │   │   ├── DashboardPage.tsx
│   │   │   ├── QuizPage.tsx     # Solo quiz player with timer + flagging
│   │   │   ├── LeaderboardPage.tsx
│   │   │   ├── ProfilePage.tsx
│   │   │   ├── DuelPage.tsx     # WebSocket duel UI
│   │   │   └── AdminPage.tsx    # Full admin panel
│   │   ├── services/
│   │   │   └── api.ts           # Axios instance + all API helpers
│   │   └── store/
│   │       └── auth.ts          # Zustand auth store
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── .env.example
│
├── requirements.txt             # Root-level (mirrors backend, for Render)
├── runtime.txt                  # Python 3.11.9
└── README.md
```

---

## Quick Start (Local)

### Prerequisites

- Python 3.11+
- Node.js 18+

### Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env – at minimum set SECRET_KEY

# Run (SQLite database created automatically on first start)
uvicorn app.main:app --reload --port 8000
```

API docs available at: http://localhost:8000/docs

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Configure environment (optional – Vite proxy handles /api in dev)
cp .env.example .env.local

# Run dev server
npm run dev
```

App available at: http://localhost:5173

---

## Environment Variables

Copy `backend/.env.example` to `backend/.env` and fill in:

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | ✅ | JWT signing secret. Generate: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `DATABASE_URL` | ✅ | SQLite: `sqlite+aiosqlite:///./trainmaster.db` · PostgreSQL: `postgresql+asyncpg://user:pass@host/db` |
| `CORS_ORIGINS` | ✅ | JSON array of allowed origins e.g. `["https://myapp.vercel.app"]` |
| `SMTP_HOST` | Optional | SMTP host for email notifications (e.g. `smtp.gmail.com`) |
| `SMTP_PORT` | Optional | Usually `587` (STARTTLS) |
| `SMTP_USER` | Optional | Your email address |
| `SMTP_PASSWORD` | Optional | App password (Gmail) or API key (SendGrid) |
| `VALIDATION_BACKEND` | Optional | `local` (default) or `huggingface` |
| `HUGGINGFACE_API_KEY` | Optional | Required only if `VALIDATION_BACKEND=huggingface` |
| `FUZZY_THRESHOLD` | Optional | 0–100, default `80`. Lower = more lenient. |
| `SEMANTIC_THRESHOLD` | Optional | 0–1, default `0.75`. Lower = more lenient. |

**Gmail SMTP setup:**
1. Enable 2-Factor Authentication on your Google account.
2. Go to myaccount.google.com/apppasswords.
3. Generate an App Password for "Mail".
4. Use that 16-character password as `SMTP_PASSWORD`.

---

## Answer Validation System

Answers go through a two-layer pipeline:

**Layer 1 – Fuzzy matching (always runs, instant)**
- Normalises both strings: lowercase, strip punctuation, collapse whitespace.
- Computes Levenshtein ratio, token-set ratio, and partial ratio via `rapidfuzz`.
- Checks against `correct_answer` and all `alt_answers` (pipe-separated).
- If score ≥ `FUZZY_THRESHOLD` → accept immediately without hitting the model.

**Layer 2 – Semantic similarity (runs only when fuzzy is inconclusive)**
- Uses `paraphrase-MiniLM-L6-v2` (~80 MB, Apache 2 licence) via `sentence-transformers`.
- Computes cosine similarity between answer embeddings.
- If score ≥ `SEMANTIC_THRESHOLD` → accept.
- Alternatively, set `VALIDATION_BACKEND=huggingface` to use the HuggingFace Inference API instead of the local model (useful on memory-constrained free-tier hosts).

**Tuning tips:**
- For science/maths (exact terminology matters): raise both thresholds (85 / 0.80).
- For history/geography (more paraphrasing): lower semantic threshold (0.65).
- Add common synonyms and abbreviations to `alt_answers` to reduce false negatives.

---

## Quiz JSON Format

Use this format when uploading quizzes via the admin panel's "Upload JSON" feature:

```json
{
  "title": "World Capitals",
  "description": "Test your geography knowledge",
  "timer_seconds": 20,
  "questions": [
    {
      "prompt": "What is the capital of France?",
      "correct_answer": "Paris",
      "alt_answers": "paris|PARIS"
    },
    {
      "prompt": "What is the capital of Japan?",
      "correct_answer": "Tokyo",
      "alt_answers": "tokyo|Tōkyō"
    }
  ]
}
```

Fields:
- `title` – required
- `description` – optional
- `timer_seconds` – optional, default 30 (5–300)
- `questions[].prompt` – required
- `questions[].correct_answer` – required
- `questions[].alt_answers` – optional, pipe-separated string of accepted alternatives

---

## API Overview

All endpoints are documented interactively at `/docs` (Swagger UI).

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/auth/register` | — | Create account |
| POST | `/api/auth/login` | — | Get token pair |
| GET | `/api/auth/me` | User | Current user info |
| GET | `/api/quizzes` | User | List active quizzes |
| GET | `/api/quizzes/{id}` | User | Quiz detail + questions |
| POST | `/api/quizzes/{id}/start` | User | Start attempt (one per user) |
| POST | `/api/quizzes/{id}/answer` | User | Submit answer, get result |
| POST | `/api/quizzes/{id}/finish` | User | Complete attempt, update leaderboard |
| GET | `/api/leaderboard` | User | Global rankings |
| POST | `/api/flags` | User | Flag a disputed answer |
| POST | `/api/admin/quizzes` | Admin | Create quiz |
| POST | `/api/admin/quizzes/upload` | Admin | Upload quiz as JSON file |
| GET | `/api/admin/flags` | Admin | List pending flags |
| POST | `/api/admin/flags/{id}/review` | Admin | Accept / reject flag |
| GET | `/api/admin/stats` | Admin | Platform statistics |
| WS | `/ws/duel/{invite_code}?token=JWT` | User | Duel WebSocket |

---

## Deployment (Free Tier)

### Backend → Render

1. Push your code to GitHub.
2. Go to [render.com](https://render.com) → New → Web Service.
3. Connect your repo.
4. Set:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Root directory:** `backend`
5. Add all environment variables from `.env.example` in the Render dashboard.
6. For the database, use Render's free PostgreSQL add-on and set `DATABASE_URL` to the provided connection string (swap `postgresql://` → `postgresql+asyncpg://`).

### Frontend → Vercel

1. Go to [vercel.com](https://vercel.com) → New Project → import your repo.
2. Set **Root Directory** to `frontend`.
3. Add environment variable: `VITE_API_URL=https://your-render-service.onrender.com`
4. Deploy.

### Alternative: Railway

Railway supports both services in one project:
1. New project → Deploy from GitHub.
2. Add two services: one pointing to `backend/`, one to `frontend/`.
3. Railway auto-detects `runtime.txt` and `package.json`.
4. Set environment variables per service.

---

## Making the First Admin

After registering your account, connect to the database and set `is_admin = 1`:

**SQLite (local):**
```bash
sqlite3 backend/trainmaster.db
UPDATE users SET is_admin = 1 WHERE email = 'your@email.com';
.quit
```

**PostgreSQL (production via Render shell):**
```sql
UPDATE users SET is_admin = true WHERE email = 'your@email.com';
```

---

## Database Migration (SQLite → PostgreSQL)

The project is wired for Alembic migrations. To switch to PostgreSQL:

1. Update `DATABASE_URL` in `.env`:
   ```
   DATABASE_URL=postgresql+asyncpg://user:password@host:5432/trainmaster
   ```

2. Generate initial migration:
   ```bash
   cd backend
   alembic init alembic
   # Edit alembic/env.py to import Base from app.core.database
   alembic revision --autogenerate -m "initial"
   alembic upgrade head
   ```

The ORM models use only standard SQL types (Integer, String, Text, Boolean, DateTime, Float) so migration is seamless.

---

## Scoring

- Each correct answer awards **10 points** (configurable via `POINTS_PER_CORRECT` in `.env`).
- No speed bonus in solo mode.
- Duel mode: first player to answer correctly wins the point for that question.
- Admin can grant or revoke points manually from the admin panel.
- Points from accepted flags are awarded retroactively.

---

## License

MIT — free to use, modify, and deploy.
