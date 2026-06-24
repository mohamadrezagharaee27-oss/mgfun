from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import (StringField, PasswordField, BooleanField, TextAreaField,
                     SelectField, SubmitField)
from wtforms.validators import (DataRequired, Email, EqualTo, Length,
                                ValidationError, Optional)
from models import User

CATEGORIES = [
    ('General', 'General'),
    ('Education', 'Education'),
    ('Entertainment', 'Entertainment'),
    ('Music', 'Music'),
    ('Gaming', 'Gaming'),
    ('Sports', 'Sports'),
    ('Technology', 'Technology'),
    ('News', 'News'),
    ('Travel', 'Travel'),
    ('Food', 'Food'),
    ('Art', 'Art'),
    ('Other', 'Other'),
]

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[
        DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[
        DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(), EqualTo('password')])
    submit = SubmitField('Create Account')

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already taken.')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Keep me logged in')
    submit = SubmitField('Sign In')


class UploadForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=5000)])
    category = SelectField('Category', choices=CATEGORIES)
    file = FileField('File', validators=[
        FileRequired(),
        FileAllowed(['mp4', 'avi', 'mov', 'mkv', 'webm', 'flv',
                     'jpg', 'jpeg', 'png', 'gif', 'webp', 'pdf'],
                    'Only video, image, or PDF files are allowed.')
    ])
    submit = SubmitField('Upload')


class CommentForm(FlaskForm):
    body = TextAreaField('Comment', validators=[DataRequired(), Length(min=1, max=2000)])
    submit = SubmitField('Post')


class ProfileForm(FlaskForm):
    bio = TextAreaField('Bio', validators=[Optional(), Length(max=500)])
    avatar = FileField('Profile Picture', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png', 'webp'], 'Images only.')
    ])
    submit = SubmitField('Save Changes')


class SearchForm(FlaskForm):
    q = StringField('Search', validators=[DataRequired()])
    submit = SubmitField('Search')
