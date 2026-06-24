from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    avatar = db.Column(db.String(256), default=None)
    bio = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    uploads = db.relationship('Upload', backref='uploader', lazy='dynamic', cascade='all, delete-orphan')
    likes = db.relationship('Like', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    comments = db.relationship('Comment', backref='author', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def has_liked(self, upload_id):
        return self.likes.filter_by(upload_id=upload_id).first() is not None

    def __repr__(self):
        return f'<User {self.username}>'


class Upload(db.Model):
    __tablename__ = 'uploads'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    category = db.Column(db.String(64), default='General')
    file_type = db.Column(db.String(10), nullable=False)  # 'video', 'image', 'pdf'
    filename = db.Column(db.String(256), nullable=False)
    original_filename = db.Column(db.String(256), nullable=False)
    file_size = db.Column(db.Integer, default=0)
    thumbnail = db.Column(db.String(256), default=None)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    view_count = db.Column(db.Integer, default=0)

    likes = db.relationship('Like', backref='upload', lazy='dynamic', cascade='all, delete-orphan')
    comments = db.relationship('Comment', backref='upload', lazy='dynamic', cascade='all, delete-orphan')
    views = db.relationship('View', backref='upload', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def like_count(self):
        return self.likes.count()

    @property
    def comment_count(self):
        return self.comments.count()

    @property
    def file_path(self):
        folder = f'{self.file_type}s'
        return f'uploads/{folder}/{self.filename}'

    def to_dict(self, current_user=None):
        liked = False
        if current_user and current_user.is_authenticated:
            liked = current_user.has_liked(self.id)
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'category': self.category,
            'file_type': self.file_type,
            'filename': self.filename,
            'file_path': self.file_path,
            'thumbnail': self.thumbnail,
            'uploader': self.uploader.username,
            'uploader_id': self.user_id,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M'),
            'view_count': self.view_count,
            'like_count': self.like_count,
            'comment_count': self.comment_count,
            'liked': liked,
        }

    def __repr__(self):
        return f'<Upload {self.title}>'


class Like(db.Model):
    __tablename__ = 'likes'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    upload_id = db.Column(db.Integer, db.ForeignKey('uploads.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('user_id', 'upload_id', name='unique_user_upload_like'),)

    def __repr__(self):
        return f'<Like user={self.user_id} upload={self.upload_id}>'


class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    upload_id = db.Column(db.Integer, db.ForeignKey('uploads.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'body': self.body,
            'username': self.author.username,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M'),
        }

    def __repr__(self):
        return f'<Comment {self.id}>'


class View(db.Model):
    __tablename__ = 'views'
    id = db.Column(db.Integer, primary_key=True)
    upload_id = db.Column(db.Integer, db.ForeignKey('uploads.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<View upload={self.upload_id}>'
