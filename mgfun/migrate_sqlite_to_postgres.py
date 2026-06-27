#!/usr/bin/env python3
"""
migrate_sqlite_to_postgres.py
------------------------------
Optional one-time script to copy data from an existing SQLite database
into your new PostgreSQL database.

Usage:
    DATABASE_URL="postgresql+psycopg://user:pass@host/dbname" \
    SQLITE_PATH="./instance/site.db" \
    python migrate_sqlite_to_postgres.py

The script:
1. Reads every row from SQLite
2. Creates tables in PostgreSQL (if they don't exist)
3. Inserts all rows into PostgreSQL
4. Skips rows that already exist (by primary key)
"""

import os
import sys
import sqlite3

# ── locate SQLite file ─────────────────────────────────────────────────────
SQLITE_PATH = os.environ.get("SQLITE_PATH", "./instance/site.db")
if not os.path.exists(SQLITE_PATH):
    print(f"[ERROR] SQLite file not found: {SQLITE_PATH}")
    sys.exit(1)

# ── connect to SQLite ──────────────────────────────────────────────────────
src = sqlite3.connect(SQLITE_PATH)
src.row_factory = sqlite3.Row

# ── connect to PostgreSQL via SQLAlchemy ───────────────────────────────────
from app import app, db, User, Post

with app.app_context():
    db.create_all()
    print("[INFO] PostgreSQL tables created (if not already present).")

    src_cur = src.cursor()

    # ── Users ──────────────────────────────────────────────────────────────
    src_cur.execute("SELECT * FROM users")
    users = src_cur.fetchall()
    migrated_users = 0
    for row in users:
        if not db.session.get(User, row["id"]):
            u = User(
                id=row["id"],
                username=row["username"],
                email=row["email"],
                password_hash=row["password_hash"],
                created_at=row["created_at"],
            )
            db.session.add(u)
            migrated_users += 1
    db.session.commit()
    print(f"[INFO] Migrated {migrated_users} user(s).")

    # ── Posts ──────────────────────────────────────────────────────────────
    src_cur.execute("SELECT * FROM posts")
    posts = src_cur.fetchall()
    migrated_posts = 0
    for row in posts:
        if not db.session.get(Post, row["id"]):
            p = Post(
                id=row["id"],
                title=row["title"],
                body=row["body"],
                image_url=row.get("image_url") or row.get("image"),
                pdf_url=row.get("pdf_url") or row.get("pdf"),
                audio_url=row.get("audio_url") or row.get("audio"),
                audio_type=row.get("audio_type"),
                created_at=row["created_at"],
                user_id=row["user_id"],
            )
            db.session.add(p)
            migrated_posts += 1
    db.session.commit()
    print(f"[INFO] Migrated {migrated_posts} post(s).")

src.close()
print("[DONE] Migration complete.")
