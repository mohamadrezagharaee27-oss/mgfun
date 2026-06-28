import os
import cloudinary
import cloudinary.uploader
import cloudinary.api
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# ──────────────────────────────────────────────
# App & Config
# ──────────────────────────────────────────────
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-me-in-production")

# PostgreSQL via DATABASE_URL (Render sets this automatically)
database_url = os.environ.get("DATABASE_URL", "sqlite:///local_dev.db")
# Render sometimes returns postgres:// — SQLAlchemy 2.x requires postgresql://
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
elif database_url.startswith("postgresql://") and "psycopg" not in database_url:
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB

# Cloudinary config (reads CLOUDINARY_URL env var automatically, or use individual vars)
cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
    secure=True,
)

# ──────────────────────────────────────────────
# Extensions
# ──────────────────────────────────────────────
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

# ──────────────────────────────────────────────
# Allowed file types
# ──────────────────────────────────────────────
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
ALLOWED_PDF_EXTENSIONS   = {"pdf"}
ALLOWED_AUDIO_EXTENSIONS = {"mp3", "wav", "ogg", "aac", "flac"}

def allowed_file(filename, allowed_set):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_set

def upload_to_cloudinary(file, resource_type="auto", folder="mgfun"):
    """Upload a file object to Cloudinary and return the secure URL."""
    result = cloudinary.uploader.upload(
        file,
        resource_type=resource_type,
        folder=folder,
    )
    return result["secure_url"]

# ──────────────────────────────────────────────
# Models
# ──────────────────────────────────────────────
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80),  unique=True, nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    posts         = db.relationship("Post", backref="author", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Post(db.Model):
    __tablename__ = "posts"
    id           = db.Column(db.Integer, primary_key=True)
    title        = db.Column(db.String(200), nullable=False)
    body         = db.Column(db.Text,        nullable=False)
    image_url    = db.Column(db.String(500))   # Cloudinary URL
    pdf_url      = db.Column(db.String(500))   # Cloudinary URL
    audio_url    = db.Column(db.String(500))   # Cloudinary URL
    audio_type   = db.Column(db.String(20))    # e.g. "audio/mp3"
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    user_id      = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    def __repr__(self):
        return f"<Post {self.id}: {self.title}>"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# ──────────────────────────────────────────────
# Routes — Auth
# ──────────────────────────────────────────────
@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        if not username or not email or not password:
            flash("All fields are required.", "danger")
            return render_template("register.html")
        if User.query.filter_by(username=username).first():
            flash("Username already taken.", "danger")
            return render_template("register.html")
        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "danger")
            return render_template("register.html")
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash("Account created! Please log in.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(request.args.get("next") or url_for("index"))
        flash("Invalid username or password.", "danger")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out.", "info")
    return redirect(url_for("index"))

# ──────────────────────────────────────────────
# Routes — Posts
# ──────────────────────────────────────────────
@app.route("/")
def index():
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template("index.html", posts=posts)


@app.route("/post/<int:post_id>")
def view_post(post_id):
    post = db.get_or_404(Post, post_id)
    return render_template("post.html", post=post)


@app.route("/post/new", methods=["GET", "POST"])
@login_required
def new_post():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        body  = request.form.get("body", "").strip()
        if not title or not body:
            flash("Title and body are required.", "danger")
            return render_template("new_post.html")

        image_url = audio_url = pdf_url = audio_type = None

        # ── Image upload ──
        image_file = request.files.get("image")
        if image_file and image_file.filename:
            if not allowed_file(image_file.filename, ALLOWED_IMAGE_EXTENSIONS):
                flash("Image type not allowed.", "danger")
                return render_template("new_post.html")
            try:
                image_url = upload_to_cloudinary(image_file, resource_type="image")
            except Exception as e:
                flash(f"Image upload failed: {e}", "danger")
                return render_template("new_post.html")

        # ── PDF upload ──
        pdf_file = request.files.get("pdf")
        if pdf_file and pdf_file.filename:
            if not allowed_file(pdf_file.filename, ALLOWED_PDF_EXTENSIONS):
                flash("Only PDF files allowed.", "danger")
                return render_template("new_post.html")
            try:
                pdf_url = upload_to_cloudinary(pdf_file, resource_type="raw")
            except Exception as e:
                flash(f"PDF upload failed: {e}", "danger")
                return render_template("new_post.html")

        # ── Audio upload ──
        audio_file = request.files.get("audio")
        if audio_file and audio_file.filename:
            ext = audio_file.filename.rsplit(".", 1)[-1].lower()
            if not allowed_file(audio_file.filename, ALLOWED_AUDIO_EXTENSIONS):
                flash("Audio type not allowed. Supported: mp3, wav, ogg, aac, flac.", "danger")
                return render_template("new_post.html")
            try:
                audio_url  = upload_to_cloudinary(audio_file, resource_type="video")  # Cloudinary uses "video" for audio
                audio_type = f"audio/{ext}" if ext != "mp3" else "audio/mpeg"
            except Exception as e:
                flash(f"Audio upload failed: {e}", "danger")
                return render_template("new_post.html")

        post = Post(
            title=title, body=body,
            image_url=image_url, pdf_url=pdf_url,
            audio_url=audio_url, audio_type=audio_type,
            user_id=current_user.id,
        )
        db.session.add(post)
        db.session.commit()
        flash("Post created!", "success")
        return redirect(url_for("view_post", post_id=post.id))

    return render_template("new_post.html")


@app.route("/post/<int:post_id>/edit", methods=["GET", "POST"])
@login_required
def edit_post(post_id):
    post = db.get_or_404(Post, post_id)
    if post.user_id != current_user.id:
        flash("Not authorised.", "danger")
        return redirect(url_for("index"))

    if request.method == "POST":
        post.title = request.form.get("title", "").strip() or post.title
        post.body  = request.form.get("body",  "").strip() or post.body

        image_file = request.files.get("image")
        if image_file and image_file.filename:
            if allowed_file(image_file.filename, ALLOWED_IMAGE_EXTENSIONS):
                try:
                    post.image_url = upload_to_cloudinary(image_file, resource_type="image")
                except Exception as e:
                    flash(f"Image upload failed: {e}", "warning")

        pdf_file = request.files.get("pdf")
        if pdf_file and pdf_file.filename:
            if allowed_file(pdf_file.filename, ALLOWED_PDF_EXTENSIONS):
                try:
                    post.pdf_url = upload_to_cloudinary(pdf_file, resource_type="raw")
                except Exception as e:
                    flash(f"PDF upload failed: {e}", "warning")

        audio_file = request.files.get("audio")
        if audio_file and audio_file.filename:
            ext = audio_file.filename.rsplit(".", 1)[-1].lower()
            if allowed_file(audio_file.filename, ALLOWED_AUDIO_EXTENSIONS):
                try:
                    post.audio_url  = upload_to_cloudinary(audio_file, resource_type="video")
                    post.audio_type = f"audio/{ext}" if ext != "mp3" else "audio/mpeg"
                except Exception as e:
                    flash(f"Audio upload failed: {e}", "warning")

        db.session.commit()
        flash("Post updated.", "success")
        return redirect(url_for("view_post", post_id=post.id))

    return render_template("edit_post.html", post=post)


@app.route("/post/<int:post_id>/delete", methods=["POST"])
@login_required
def delete_post(post_id):
    post = db.get_or_404(Post, post_id)
    if post.user_id != current_user.id:
        flash("Not authorised.", "danger")
        return redirect(url_for("index"))
    db.session.delete(post)
    db.session.commit()
    flash("Post deleted.", "info")
    return redirect(url_for("index"))


# ──────────────────────────────────────────────
# Health check (useful for Render)
# ──────────────────────────────────────────────
@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200


# ──────────────────────────────────────────────
# Create tables & run
# ──────────────────────────────────────────────
with app.app_context():
    try:
        db.create_all()
        print("Database connected successfully.")
    except Exception as e:
        print("Database Error:", e)

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
