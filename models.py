from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    username = db.Column(db.String(80), unique=True, index=True)
    bio = db.Column(db.Text)
    avatar = db.Column(db.String(255))

    tweets = db.relationship('Tweet', backref='author', lazy=True, cascade="all,delete-orphan")
    likes = db.relationship('Like', backref='user', lazy=True, cascade="all,delete-orphan")
    comments = db.relationship('Comment', backref='user', lazy=True, cascade="all,delete-orphan")

class Tweet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String(280), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    comments = db.relationship('Comment', backref='tweet', lazy=True, cascade="all,delete-orphan")
    likes = db.relationship('Like', backref='tweet', lazy=True, cascade="all,delete-orphan")

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String(280), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    tweet_id = db.Column(db.Integer, db.ForeignKey('tweet.id'), nullable=False)

class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    tweet_id = db.Column(db.Integer, db.ForeignKey('tweet.id'), nullable=False)

    __table_args__ = (db.UniqueConstraint('user_id', 'tweet_id', name='uq_user_tweet_like'),)
