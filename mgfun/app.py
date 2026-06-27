import os
import uuid
import psycopg
from datetime import datetime
from flask import (Flask, render_template, redirect, url_for, flash,
                   request, jsonify, abort, send_from_directory)
from flask_login import (LoginManager, login_user, logout_user,
                         login_required, current_user)
from flask_wtf.csrf import CSRFProtect
from werkzeug.utils import secure_filename
from sqlalchemy import or_, desc, func

from config import config
from models import db, User, Upload, Like, Comment, View
from forms import (RegistrationForm, LoginForm, UploadForm,
                   CommentForm, ProfileForm, SearchForm)

# ── App factory ──────────────────────────────────────────────────────────────
def create_app(env=None):
    app = Flask(__name__)
    env = env or os.environ.get('FLASK_ENV', 'default')
    app.config.from_object(config[env])

    db.init_app(app)
    csrf = CSRFProtect(app)

    login_manager = LoginManager(app)
    login_manager.login_view = 'login'
    login_manager.login_message = 'Please sign in to access this page.'
    login_manager.login_message_category = 'info'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Ensure upload dirs exist
    for sub in ('videos', 'images', 'pdfs', 'avatars'):
        os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], sub), exist_ok=True)

    # ── Helpers ────────────────────────────────────────────────────────────────
    def allowed_file(filename, ftype):
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        if ftype == 'video':
            return ext in app.config['ALLOWED_VIDEO_EXTENSIONS']
        if ftype == 'image':
            return ext in app.config['ALLOWED_IMAGE_EXTENSIONS']
        if ftype == 'pdf':
            return ext in app.config['ALLOWED_PDF_EXTENSIONS']
        return False
        # audio
        if ftype == 'audio':
            return ext in app.config.get('ALLOWED_AUDIO_EXTENSIONS', set())

    def detect_file_type(filename):
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        if ext in app.config['ALLOWED_VIDEO_EXTENSIONS']:
            return 'video'
        if ext in app.config['ALLOWED_IMAGE_EXTENSIONS']:
            return 'image'
        if ext in app.config['ALLOWED_PDF_EXTENSIONS']:
            return 'pdf'
        return None

    def save_file(file_obj, file_type):
        original = secure_filename(file_obj.filename)
        ext = original.rsplit('.', 1)[-1].lower()
        unique_name = f"{uuid.uuid4().hex}.{ext}"
        folder = f"{file_type}s"
        dest = os.path.join(app.config['UPLOAD_FOLDER'], folder, unique_name)
        file_obj.save(dest)
        return unique_name, original, os.path.getsize(dest)

    # ── Context processors ────────────────────────────────────────────────────
    @app.context_processor
    def inject_search_form():
        return dict(search_form=SearchForm())

    @app.context_processor
    def inject_categories():
        from forms import CATEGORIES
        return dict(categories=[c[0] for c in CATEGORIES])

    # ── Routes ─────────────────────────────────────────────────────────────────

    @app.route('/')
    def index():
        latest = Upload.query.order_by(desc(Upload.created_at)).limit(12).all()
        most_liked = (
            db.session.query(Upload)
            .outerjoin(Like)
            .group_by(Upload.id)
            .order_by(desc(func.count(Like.id)))
            .limit(8).all()
        )
        trending = (
            db.session.query(Upload)
            .order_by(desc(Upload.view_count))
            .limit(6).all()
        )
        return render_template('index.html',
                               latest=latest,
                               most_liked=most_liked,
                               trending=trending)

    # ── Auth ───────────────────────────────────────────────────────────────────

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        form = RegistrationForm()
        if form.validate_on_submit():
            user = User(username=form.username.data, email=form.email.data)
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash('Account created! You can now sign in.', 'success')
            return redirect(url_for('login'))
        return render_template('register.html', form=form)

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(username=form.username.data).first()
            if user and user.check_password(form.password.data):
                login_user(user, remember=form.remember_me.data,
                           duration=app.config['REMEMBER_COOKIE_DURATION'])
                next_page = request.args.get('next')
                flash(f'Welcome back, {user.username}!', 'success')
                return redirect(next_page or url_for('index'))
            flash('Invalid username or password.', 'danger')
        return render_template('login.html', form=form)

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash('You have been signed out.', 'info')
        return redirect(url_for('index'))

    # ── Profile ────────────────────────────────────────────────────────────────

    @app.route('/user/<username>')
    def profile(username):
        user = User.query.filter_by(username=username).first_or_404()
        uploads = Upload.query.filter_by(user_id=user.id).order_by(desc(Upload.created_at)).all()
        return render_template('profile.html', profile_user=user, uploads=uploads)

    @app.route('/settings', methods=['GET', 'POST'])
    @login_required
    def settings():
        form = ProfileForm()
        if form.validate_on_submit():
            current_user.bio = form.bio.data
            if form.avatar.data:
                unique_name = f"{uuid.uuid4().hex}.jpg"
                dest = os.path.join(app.config['UPLOAD_FOLDER'], 'avatars', unique_name)
                form.avatar.data.save(dest)
                current_user.avatar = unique_name
            db.session.commit()
            flash('Profile updated.', 'success')
            return redirect(url_for('profile', username=current_user.username))
        form.bio.data = current_user.bio
        return render_template('settings.html', form=form)

    # ── Upload ─────────────────────────────────────────────────────────────────

    @app.route('/upload', methods=['GET', 'POST'])
    @login_required
    def upload():
        form = UploadForm()
        if form.validate_on_submit():
            f = form.file.data
            ftype = detect_file_type(f.filename)
            if not ftype:
                flash('Unsupported file type.', 'danger')
                return render_template('upload.html', form=form)

            unique_name, original, size = save_file(f, ftype)
            record = Upload(
                title=form.title.data,
                description=form.description.data,
                category=form.category.data,
                file_type=ftype,
                filename=unique_name,
                original_filename=original,
                file_size=size,
                user_id=current_user.id,
            )
            db.session.add(record)
            db.session.commit()
            flash('Upload successful!', 'success')
            return redirect(url_for('view_upload', upload_id=record.id))
        return render_template('upload.html', form=form)

    @app.route('/watch/<int:upload_id>')
    def view_upload(upload_id):
        upload_record = Upload.query.get_or_404(upload_id)
        # Record view
        ip = request.remote_addr
        view = View(upload_id=upload_record.id,
                    user_id=current_user.id if current_user.is_authenticated else None,
                    ip_address=ip)
        db.session.add(view)
        upload_record.view_count += 1
        db.session.commit()

        comment_form = CommentForm()
        comments = (Comment.query.filter_by(upload_id=upload_record.id)
                    .order_by(desc(Comment.created_at)).all())
        related = (Upload.query
                   .filter(Upload.category == upload_record.category,
                           Upload.id != upload_record.id)
                   .order_by(desc(Upload.created_at))
                   .limit(8).all())
        return render_template('watch.html',
                               upload=upload_record,
                               comment_form=comment_form,
                               comments=comments,
                               related=related)

    @app.route('/delete/<int:upload_id>', methods=['POST'])
    @login_required
    def delete_upload(upload_id):
        record = Upload.query.get_or_404(upload_id)
        if record.user_id != current_user.id:
            abort(403)
        # Remove file from disk
        path = os.path.join(app.config['UPLOAD_FOLDER'], f"{record.file_type}s", record.filename)
        if os.path.exists(path):
            os.remove(path)
        db.session.delete(record)
        db.session.commit()
        flash('Upload deleted.', 'info')
        return redirect(url_for('profile', username=current_user.username))

    # ── AJAX: Likes ────────────────────────────────────────────────────────────

    @app.route('/like/<int:upload_id>', methods=['POST'])
    @login_required
    def toggle_like(upload_id):
        record = Upload.query.get_or_404(upload_id)
        existing = Like.query.filter_by(user_id=current_user.id,
                                        upload_id=upload_id).first()
        if existing:
            db.session.delete(existing)
            liked = False
        else:
            db.session.add(Like(user_id=current_user.id, upload_id=upload_id))
            liked = True
        db.session.commit()
        return jsonify({'liked': liked, 'count': record.like_count})

    # ── AJAX: Comments ─────────────────────────────────────────────────────────

    @app.route('/comment/<int:upload_id>', methods=['POST'])
    @login_required
    def post_comment(upload_id):
        Upload.query.get_or_404(upload_id)
        data = request.get_json(silent=True) or {}
        body = (data.get('body') or '').strip()
        if not body:
            return jsonify({'error': 'Comment cannot be empty.'}), 400
        if len(body) > 2000:
            return jsonify({'error': 'Comment too long.'}), 400
        comment = Comment(body=body, user_id=current_user.id, upload_id=upload_id)
        db.session.add(comment)
        db.session.commit()
        return jsonify(comment.to_dict())

    # ── Search ─────────────────────────────────────────────────────────────────

    @app.route('/search')
    def search():
        q = request.args.get('q', '').strip()
        category = request.args.get('category', '')
        page = request.args.get('page', 1, type=int)
        results = []
        total = 0
        if q:
            query = Upload.query.filter(
                or_(
                    Upload.title.ilike(f'%{q}%'),
                    Upload.description.ilike(f'%{q}%'),
                )
            )
            if category:
                query = query.filter_by(category=category)
            query = query.order_by(desc(Upload.created_at))
            pagination = query.paginate(page=page, per_page=12, error_out=False)
            results = pagination.items
            total = pagination.total
        return render_template('search.html', results=results, q=q,
                               category=category, total=total)

    @app.route('/search/suggestions')
    def search_suggestions():
        q = request.args.get('q', '').strip()
        if len(q) < 2:
            return jsonify([])
        hits = (Upload.query
                .filter(Upload.title.ilike(f'%{q}%'))
                .limit(8).all())
        return jsonify([{'id': h.id, 'title': h.title, 'type': h.file_type} for h in hits])

    # ── Category ───────────────────────────────────────────────────────────────

    @app.route('/category/<category_name>')
    def category(category_name):
        page = request.args.get('page', 1, type=int)
        pagination = (Upload.query
                      .filter_by(category=category_name)
                      .order_by(desc(Upload.created_at))
                      .paginate(page=page, per_page=12, error_out=False))
        return render_template('category.html',
                               uploads=pagination.items,
                               category=category_name,
                               pagination=pagination)

    # ── Static uploads ─────────────────────────────────────────────────────────

    @app.route('/uploads/<path:filename>')
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    # ── Error handlers ─────────────────────────────────────────────────────────

    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(413)
    def too_large(e):
        flash('File is too large. Maximum size is 500MB.', 'danger')
        return redirect(url_for('upload'))

    # ── CLI: init DB ───────────────────────────────────────────────────────────

    @app.cli.command('init-db')
    def init_db():
        db.create_all()
        print('Database tables created.')

    return app


app = create_app()

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    
    app.run(debug=True, host='0.0.0.0', port='port')
