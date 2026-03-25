from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='student')  # 'admin' or 'student'
    is_active_member = db.Column(db.Boolean, default=False)
    stripe_customer_id = db.Column(db.String(100), nullable=True)
    stripe_subscription_id = db.Column(db.String(100), nullable=True)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)  # Admin notes about student
    level = db.Column(db.String(20), default='beginner')  # beginner, intermediate, advanced

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.email}>'


class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(100), nullable=False)
    level = db.Column(db.String(20), default='all')  # beginner, intermediate, advanced, all
    filename = db.Column(db.String(300), nullable=True)   # for uploaded videos
    youtube_url = db.Column(db.String(500), nullable=True)  # optional YouTube embed
    thumbnail = db.Column(db.String(300), nullable=True)
    duration = db.Column(db.String(20), nullable=True)  # e.g. "12:34"
    is_published = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    view_count = db.Column(db.Integer, default=0)
    order_num = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f'<Video {self.title}>'


class VideoView(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    video_id = db.Column(db.Integer, db.ForeignKey('video.id'), nullable=False)
    watched_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed = db.Column(db.Boolean, default=False)

    user = db.relationship('User', backref='views')
    video = db.relationship('Video', backref='views')


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    emoji = db.Column(db.String(10), default='📚')
    description = db.Column(db.String(300), nullable=True)
    order_num = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f'<Category {self.name}>'


class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    stripe_payment_id = db.Column(db.String(200), nullable=True)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default='eur')
    payment_type = db.Column(db.String(50), nullable=False)  # 'enrollment', 'monthly'
    status = db.Column(db.String(50), default='pending')  # pending, completed, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='payments')

    def __repr__(self):
        return f'<Payment {self.user_id} {self.amount}>'


class Correction(db.Model):
    """Students can submit texts/recordings for Victor to correct"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    correction = db.Column(db.Text, nullable=True)  # Victor's correction
    status = db.Column(db.String(20), default='pending')  # pending, corrected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    corrected_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship('User', backref='corrections')

    def __repr__(self):
        return f'<Correction {self.title}>'
