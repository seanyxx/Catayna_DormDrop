from app import db, login_manager
from flask_login import UserMixin
from datetime import datetime


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(60), nullable=False)
    profile_image = db.Column(db.String(40), nullable=False, default='default_avatar.png')
    bio = db.Column(db.String(30), nullable=True, default='Hello! I am a student here.')
    security_question = db.Column(db.String(150), nullable=False)
    security_answer_hash = db.Column(db.String(60), nullable=False)
    items = db.relationship('Item', backref='owner', lazy=True, cascade="all, delete-orphan")
    watchlists = db.relationship('Watchlist', backref='user', lazy=True, cascade="all, delete-orphan")


class Item(db.Model):
    __tablename__ = 'items'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    image_path = db.Column(db.String(40), nullable=False, default='default_item.png')
    status = db.Column(db.String(20), nullable=False, default='Available')
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    watchlisted_by = db.relationship('Watchlist', backref='item', lazy=True, cascade="all, delete-orphan")


class Watchlist(db.Model):
    __tablename__ = 'watchlists'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id'), nullable=False)
    __table_args__ = (db.UniqueConstraint('user_id', 'item_id', name='_user_item_uc'),)


class Message(db.Model):
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    # Required timestamp for every message
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id'), nullable=False)

    # Relationships mapped to determine contextual headers (Buyer/Seller/Item)
    sender = db.relationship('User', foreign_keys=[sender_id], backref='messages_sent')
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='messages_received')
    item = db.relationship('Item', foreign_keys=[item_id])