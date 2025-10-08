from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, Optional
from flask_wtf.file import FileField, FileAllowed

class RegisterForm(FlaskForm):
    email = StringField('E-posta', validators=[DataRequired(), Email()])
    password = PasswordField('Şifre', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Kayıt Ol')

class LoginForm(FlaskForm):
    email = StringField('E-posta', validators=[DataRequired(), Email()])
    password = PasswordField('Şifre', validators=[DataRequired()])
    submit = SubmitField('Giriş')

class TweetForm(FlaskForm):
    body = TextAreaField('Ne oluyor?', validators=[DataRequired(), Length(max=280)])
    submit = SubmitField('Tweetle')

class CommentForm(FlaskForm):
    body = StringField('Yorum yaz', validators=[DataRequired(), Length(max=280)])
    submit = SubmitField('Gönder')

class ProfileForm(FlaskForm):
    username = StringField('Kullanıcı adı', validators=[Optional(), Length(min=3, max=30)])
    bio = TextAreaField('Biyografi', validators=[Optional(), Length(max=280)])
    avatar = FileField('Profil fotoğrafı', validators=[FileAllowed(['jpg','jpeg','png','webp'], 'Görsel dosya seçin')])
    submit = SubmitField('Kaydet')
