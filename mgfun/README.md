# MgFun – Flask + PostgreSQL + Cloudinary on Render

A Flask application with persistent PostgreSQL storage and Cloudinary-backed file uploads (images, PDFs, audio). Fully compatible with Render free tier.

---

## Table of Contents
1. [Required Environment Variables](#required-environment-variables)
2. [Create a PostgreSQL Database on Render](#create-a-postgresql-database-on-render)
3. [Create a Cloudinary Account](#create-a-cloudinary-account)
4. [Deploy on Render](#deploy-on-render)
5. [Migrate from SQLite](#migrate-from-sqlite)
6. [Local Development](#local-development)
7. [Feature Overview](#feature-overview)

---

## Required Environment Variables

| Variable | Where to get it | Required |
|---|---|---|
| `SECRET_KEY` | Any random string (generate with `python -c "import secrets; print(secrets.token_hex(32))"`) | ✅ |
| `DATABASE_URL` | Render PostgreSQL → Connection String | ✅ |
| `CLOUDINARY_CLOUD_NAME` | Cloudinary Dashboard → Cloud Name | ✅ |
| `CLOUDINARY_API_KEY` | Cloudinary Dashboard → API Key | ✅ |
| `CLOUDINARY_API_SECRET` | Cloudinary Dashboard → API Secret | ✅ |

> **Note:** Render sets `DATABASE_URL` automatically when you link a database to a web service. You only need to set the Cloudinary variables manually.

---

## Create a PostgreSQL Database on Render

1. Go to [https://dashboard.render.com](https://dashboard.render.com) and sign in.
2. Click **New +** → **PostgreSQL**.
3. Fill in:
   - **Name**: `mgfun-db` (or any name)
   - **Database**: `mgfun`
   - **User**: `mgfun`
   - **Region**: Choose the same region as your web service
   - **Plan**: Free
4. Click **Create Database**.
5. After creation, copy the **Internal Database URL** (use this when the web service is in the same region).

---

## Create a Cloudinary Account

1. Go to [https://cloudinary.com](https://cloudinary.com) and sign up for a **free** account.
2. After login, go to your **Dashboard**.
3. Note down:
   - **Cloud Name**
   - **API Key**
   - **API Secret**
4. (Optional) Go to **Settings → Upload** and create an **unsigned upload preset** if you want client-side uploads in the future.

The free tier provides **25 GB storage + 25 GB bandwidth/month** — plenty for most projects.

---

## Deploy on Render

### Option A – One-click with render.yaml (recommended)

1. Push your project to GitHub/GitLab.
2. Go to [https://dashboard.render.com](https://dashboard.render.com).
3. Click **New +** → **Blueprint**.
4. Connect your repository.
5. Render detects `render.yaml` and creates both the web service and the PostgreSQL database automatically.
6. Add the Cloudinary environment variables in the web service settings:
   - `CLOUDINARY_CLOUD_NAME`
   - `CLOUDINARY_API_KEY`
   - `CLOUDINARY_API_SECRET`
7. Click **Apply** / **Deploy**.

### Option B – Manual setup

1. Push your project to GitHub/GitLab.
2. Go to **Render Dashboard → New + → Web Service**.
3. Connect your repository.
4. Set:
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120`
5. Add environment variables:
   - `SECRET_KEY` = (generate a random string)
   - `DATABASE_URL` = (from your Render PostgreSQL → Internal Database URL)
   - `CLOUDINARY_CLOUD_NAME` = ...
   - `CLOUDINARY_API_KEY` = ...
   - `CLOUDINARY_API_SECRET` = ...
6. Click **Create Web Service**.

### First deploy

On first boot, `app.py` calls `db.create_all()` inside `with app.app_context()`, which creates all tables automatically. No manual migration step needed.

---

## Migrate from SQLite

If you have existing data in an SQLite file:

```bash
# Set environment variables
export DATABASE_URL="postgresql+psycopg://user:pass@host/dbname"
export SQLITE_PATH="./instance/site.db"   # path to your old SQLite file

# Run the migration script
python migrate_sqlite_to_postgres.py
```

The script:
- Reads all rows from SQLite (`users` and `posts` tables)
- Creates PostgreSQL tables if they don't exist
- Inserts all rows, skipping any that already exist (safe to re-run)

**Note:** Local file paths stored in `image`, `pdf`, or `audio` columns from the old SQLite database will be carried over as-is. Those old local URLs will be broken on Render (since Render doesn't persist the filesystem). You'll need to re-upload those files to get Cloudinary URLs. New uploads will work correctly.

---

## Local Development

```bash
# 1. Clone the repo
git clone <your-repo-url>
cd mgfun

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set environment variables (or use a .env file with python-dotenv)
export SECRET_KEY="dev-secret-key"
export DATABASE_URL="sqlite:///local_dev.db"   # SQLite for local dev
export CLOUDINARY_CLOUD_NAME="your-cloud-name"
export CLOUDINARY_API_KEY="your-api-key"
export CLOUDINARY_API_SECRET="your-api-secret"

# 5. Run
python app.py
```

Visit [http://localhost:5000](http://localhost:5000).

> **Tip:** For local dev you can use SQLite (`DATABASE_URL=sqlite:///local_dev.db`). Just switch to the PostgreSQL URL for production.

---

## Feature Overview

| Feature | Details |
|---|---|
| Authentication | Register, login, logout with hashed passwords (Werkzeug) |
| Posts | Create, view, edit, delete posts |
| Image uploads | PNG, JPG, GIF, WEBP → stored on Cloudinary |
| PDF uploads | PDF → stored on Cloudinary, linked for download |
| Audio uploads | MP3, WAV, OGG, AAC, FLAC → stored on Cloudinary, HTML5 `<audio>` player |
| Persistent storage | All files survive Render restarts/redeploys (Cloudinary) |
| Database | PostgreSQL via psycopg (v3) + SQLAlchemy 2.x |
| Python version | 3.12 |
| Deployment | Render-ready (`render.yaml`, `Procfile`, `runtime.txt`) |

---

## File Structure

```
mgfun/
├── app.py                        # Main Flask application
├── requirements.txt
├── Procfile
├── runtime.txt
├── render.yaml
├── migrate_sqlite_to_postgres.py # One-time SQLite → Postgres migration
├── README.md
├── static/
│   └── css/
│       └── style.css
└── templates/
    ├── base.html
    ├── index.html
    ├── post.html
    ├── new_post.html
    ├── edit_post.html
    ├── login.html
    └── register.html
```
