from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# 初始化 SQLAlchemy
db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    age = db.Column(db.Integer)
    gender = db.Column(db.String(10))
    job = db.Column(db.String(50))
    role = db.Column(db.String(20), nullable=False)
    rating = db.Column(db.Float, default=0.0)
    avatar = db.Column(db.String(255))

    # 建立 ORM 關聯 (not entity)
    # 一個房東(User)可以擁有多個房屋(House)
    houses = db.relationship('House', backref='landlord_user', lazy=True)
    # 一個租客(User)可以擁有多個房屋評價(HouseFeedback)
    feedbacks = db.relationship('HouseFeedback', backref='renter_user', lazy=True)
    # 一個租客(User)可以擁有一個租客需求(RenterPreference)
    preference = db.relationship('RenterPreference', backref='renter_user', uselist=False, lazy=True)

class House(db.Model):
    __tablename__ = 'houses'
    
    house_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    landlord_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    area = db.Column(db.String(50), nullable=False)
    size = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    equipment = db.Column(db.Text)
    visibility = db.Column(db.Boolean, default=True, nullable=False)
    image = db.Column(db.String(500))

    # 建立 ORM 關聯
    # 一個房屋可以擁有多個評價
    house_feedbacks = db.relationship('HouseFeedback', backref='house', lazy=True)

class HouseFeedback(db.Model):
    __tablename__ = 'house_feedbacks'
    
    house_id = db.Column(db.Integer, db.ForeignKey('houses.house_id'), primary_key=True)
    renter_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), primary_key=True)
    score = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    time = db.Column(db.String(50), default=lambda: datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

class HousePreference(db.Model):
    __tablename__ = 'house_preferences'
    
    hp_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    lease_term = db.Column(db.String(50))
    gender = db.Column(db.String(20))
    smoke = db.Column(db.Boolean, default=False)
    pet = db.Column(db.Boolean, default=False)

    # 建立 ORM 關聯
    renter_preferences = db.relationship('RenterPreference', backref='house_pref', lazy=True)

class RenterPreference(db.Model):
    __tablename__ = 'renter_preferences'
    
    rp_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    renter_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), unique=True, nullable=False)
    hp_id = db.Column(db.Integer, db.ForeignKey('house_preferences.hp_id'), nullable=False)
    min_budget = db.Column(db.Integer)
    max_budget = db.Column(db.Integer)
    move_date = db.Column(db.String(50))
    room_type = db.Column(db.String(50))
    preferred_area = db.Column(db.String(50))

class Favorite(db.Model):
    __tablename__ = 'favorites'
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), primary_key=True)
    house_id = db.Column(db.Integer, db.ForeignKey('houses.house_id'), primary_key=True)
    created_at = db.Column(db.String(50), default=lambda: datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    # 建立 ORM 關聯
    user = db.relationship('User', backref=db.backref('my_favorites', lazy='dynamic'))
    house = db.relationship('House', backref=db.backref('favorited_by', lazy='dynamic'))