# MG FUN — Video Sharing Platform

A full-featured media sharing platform (videos, images, PDFs) built with Python Flask.

---

## Features

- User registration & login with persistent "Remember Me" sessions
- Upload videos (mp4, avi, mov, mkv, webm, flv), images (jpg, png, gif, webp), and PDFs
- View counter, like system (one per user, AJAX), comment system (AJAX)
- Search by title & description with category filtering
- User profiles and settings
- Dark, responsive UI (desktop + mobile)
- CSRF protection on all forms
- Ready for Render.com deployment with PostgreSQL

---

## Local Development

### 1. Clone & create virtual environment

```bash
git clone <your-repo-url>
cd mgfun
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env — set a strong SECRET_KEY
```

### 4. Initialize the database

```bash
flask init-db
# or
python -c "from app import app; from models import db; \
           app.app_context().__enter__(); db.create_all()"
```

### 5. Run the development server

```bash
flask run
# Visit http://127.0.0.1:5000
```

---

## Project Structure

```
mgfun/
├── app.py              # Flask application factory & all routes
├── models.py           # SQLAlchemy models (User, Upload, Like, Comment, View)
├── forms.py            # WTForms form classes
├── config.py           # Dev / prod configuration
├── requirements.txt
├── render.yaml         # Render Blueprint for one-click deploy
├── Procfile            # gunicorn start command
├── runtime.txt         # Python version pin
├── .env.example        # Environment variable template
├── static/
│   ├── css/main.css
│   ├── js/main.js
│   └── uploads/
│       ├── videos/
│       ├── images/
│       ├── pdfs/
│       └── avatars/
└── templates/
    ├── base.html
    ├── index.html
    ├── login.html
    ├── register.html
    ├── upload.html
    ├── watch.html
    ├── profile.html
    ├── settings.html
    ├── search.html
    ├── category.html
    └── errors/
        ├── 404.html
        └── 403.html
```

---

## Deploy to Render.com

### Option A — Blueprint (render.yaml) — recommended

1. Push your code to a GitHub/GitLab repo.
2. In Render Dashboard → **New** → **Blueprint**.
3. Connect your repo; Render reads `render.yaml` and:
   - Creates a **Web Service** running gunicorn
   - Creates a free **PostgreSQL database**
   - Wires `DATABASE_URL` automatically
4. After first deploy, open the **Shell** tab and run:
   ```bash
   flask init-db
   ```

### Option B — Manual

1. **New Web Service** → connect your repo.
2. Build command: `pip install -r requirements.txt`
3. Start command: `gunicorn app:app --workers 2 --bind 0.0.0.0:$PORT`
4. Add environment variables:
   | Key | Value |
   |-----|-------|
   | `FLASK_ENV` | `production` |
   | `SECRET_KEY` | (generate a strong random string) |
   | `DATABASE_URL` | (from your Render PostgreSQL instance) |
5. Create a free PostgreSQL database in Render, copy its **Internal Connection String** into `DATABASE_URL`.
6. After deploy, open Shell and run `flask init-db`.

### ⚠️ File storage note

Render's free tier has an **ephemeral filesystem** — uploaded files are lost on each deploy/restart. For production persistence, integrate an object storage service (e.g. AWS S3, Cloudflare R2, or Backblaze B2) and update the `save_file()` helper in `app.py`.

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `FLASK_ENV` | `development` or `production` | `development` |
| `SECRET_KEY` | Flask session secret | hardcoded dev key |
| `DATABASE_URL` | SQLAlchemy DB URI | SQLite (`mgfun.db`) |

---

## Database Models

| Table | Key columns |
|-------|-------------|
| `users` | id, username (unique), email (unique), password_hash, avatar, bio |
| `uploads` | id, title, description, category, file_type, filename, user_id, view_count |
| `likes` | id, user_id, upload_id — unique constraint prevents duplicates |
| `comments` | id, body, user_id, upload_id, created_at |
| `views` | id, upload_id, user_id (nullable), ip_address |

---

## Security

- Passwords hashed with Werkzeug `pbkdf2:sha256`
- CSRF tokens on every form via Flask-WTF
- File type validated by extension (and MIME type check recommended for production)
- Max upload: 500 MB
- Duplicate likes prevented by DB unique constraint + query check
- `SESSION_COOKIE_SECURE=True` in production (requires HTTPS)
- `SESSION_COOKIE_HTTPONLY=True` always

---

## Customisation Tips

- **Add S3 upload**: replace `save_file()` with `boto3.upload_fileobj()`
- **Add email verification**: integrate Flask-Mail
- **Add video thumbnails**: use `ffmpeg` to extract a frame on upload
- **Add pagination to homepage**: use `.paginate()` on all queries
- **Rate limiting**: add `Flask-Limiter` to the comment/like endpoints
