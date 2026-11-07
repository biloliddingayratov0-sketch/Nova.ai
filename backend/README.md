# NOVA AI Backend

FastAPI backend with:
- User registration and login
- JWT authentication
- PostgreSQL database
- AI image generation and image editing
- Per-user image history

## 1. Requirements

- Python 3.10+
- PostgreSQL
- An OpenAI API key with access to the configured image model

## 2. Create the database

In PostgreSQL / pgAdmin, run:

```sql
CREATE DATABASE nova_ai;
```

## 3. Configure environment

From this `backend` folder:

```bash
copy .env.example .env
```

Open `.env` and set:
- `OPENAI_API_KEY`
- `DATABASE_URL` (use your PostgreSQL username/password)
- `JWT_SECRET` (use a long random secret)
- `AI_IMAGE_MODEL` (a model available to your API account)

Do not commit `.env` or share your API key.

## 4. Install and run (Windows)

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open:
- http://127.0.0.1:8000
- http://127.0.0.1:8000/docs

## 5. Frontend connection

Run the frontend with VS Code Live Server at `http://127.0.0.1:5500`.
The API allows that origin by default. If Live Server uses another port, update
`FRONTEND_URL` in `.env` and the CORS list in `app/main.py`.

The frontend must send the JWT in the request header for protected endpoints:

```http
Authorization: Bearer YOUR_ACCESS_TOKEN
```

Login returns `access_token`. Store and handle tokens carefully; for a production
website, prefer a secure, HttpOnly cookie architecture rather than localStorage.

## 6. API endpoints

- `POST /api/auth/register` — JSON: `username`, `email`, `password`
- `POST /api/auth/login` — JSON: `email`, `password`
- `GET /api/auth/me` — authenticated profile
- `POST /api/images/generate` — multipart form: `prompt`, optional `ratio`, `style`
- `POST /api/images/edit` — multipart form: `prompt`, `image`, optional `ratio`, `style`
- `GET /api/history/` — authenticated user's history
- `DELETE /api/history/{image_id}` — delete one of the current user's history records
- `GET /health` — health check

## Notes

- Image generation and editing use the OpenAI Images API and may incur API charges.
- The image model name is configurable. Set it to a model currently available to your API account.
- `Base.metadata.create_all()` is convenient for local development. Use Alembic migrations
  before deploying a production database.
- Generated image URLs are currently served as static files. For production, use private
  object storage and signed URLs if images must remain private.
- Add rate limits, request quotas, logging, moderation, backups, and deployment secrets
  before making the service public.
