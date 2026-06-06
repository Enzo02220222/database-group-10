from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# 初始化 SQLAlchemy
db = SQLAlchemy()

# ==============================================================================
# 1. 使用者資料表 (合併 Renter 與 Landlord，加上身分與密碼)
# ==============================================================================
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
    role = db.Column(db.String(20), nullable=False) # 'renter' or 'landlord'
    rating = db.Column(db.Float, default=0.0) # 房東專用欄位：評價星等（如果是房客，此欄位 NULL）

    # 建立 ORM 關聯 (not entity)
    # 一個房東(User)可以擁有多個房屋(House)
    houses = db.relationship('House', backref='landlord_user', lazy=True)
    # 一個租客(User)可以擁有多個房屋評價(HouseFeedback)
    feedbacks = db.relationship('HouseFeedback', backref='renter_user', lazy=True)
    # 一個租客(User)可以擁有一個租客需求(RenterPreference)
    preference = db.relationship('RenterPreference', backref='renter_user', uselist=False, lazy=True)

# ==============================================================================
# 2. 房屋資料表
# ==============================================================================
class House(db.Model):
    __tablename__ = 'houses'
    
    house_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    landlord_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False) # 外鍵：連結到 users 表的 user_id 且該使用者的 role 必須是 'landlord'
    location = db.Column(db.String(200), nullable=False) # 完整地址
    area = db.Column(db.String(50), nullable=False) # 地區 (例如：鼓山區、西屯區)
    size = db.Column(db.Float, nullable=False) # 坪數
    type = db.Column(db.String(50), nullable=False) # 房型 (例如：獨立套房、整層住家)
    price = db.Column(db.Integer, nullable=False)
    equipment = db.Column(db.Text) # 設備 (例如：冷氣、洗衣機、網路)
    visibility = db.Column(db.Boolean, default=True, nullable=False) # 是否可見/上架狀態

    # 建立 ORM 關聯
    # 一個房屋可以擁有多個評價
    house_feedbacks = db.relationship('HouseFeedback', backref='house', lazy=True)

# ==============================================================================
# 3. 房屋評價資料表
# ==============================================================================
class HouseFeedback(db.Model):
    __tablename__ = 'house_feedbacks'
    
    house_id = db.Column(db.Integer, db.ForeignKey('houses.house_id'), primary_key=True)
    renter_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), primary_key=True) # 複合主鍵：同一個租客對同一個房屋只能評論一次
    score = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    time = db.Column(db.String(50), default=lambda: datetime.now().strftime('%Y-%m-%d %H:%M:%S')) # 送出評論的時間 (SQLite 以 'YYYY-MM-DD HH:MM:SS' 字串儲存)

# ==============================================================================
# 4. 房屋偏好資料表
# ==============================================================================
class HousePreference(db.Model):
    __tablename__ = 'house_preferences'
    
    hp_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    lease_term = db.Column(db.String(50)) # 租期需求
    gender = db.Column(db.String(20)) # 性別限制需求
    smoke = db.Column(db.Boolean, default=False) # 是否抽菸需求
    pet = db.Column(db.Boolean, default=False) # 是否養寵物需求

    # 建立 ORM 關聯
    renter_preferences = db.relationship('RenterPreference', backref='house_pref', lazy=True)

# ==============================================================================
# 5. 租客需求資料表
# ==============================================================================
class RenterPreference(db.Model):
    __tablename__ = 'renter_preferences'
    
    rp_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    renter_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), unique=True, nullable=False) # 外鍵：user_renter
    hp_id = db.Column(db.Integer, db.ForeignKey('house_preferences.hp_id'), nullable=False) # 外鍵：house_preference
    min_budget = db.Column(db.Integer)
    max_budget = db.Column(db.Integer)
    move_date = db.Column(db.String(50)) # 預計搬入日期
    room_type = db.Column(db.String(50)) # 期望房型

# ==============================================================================
# 6. 租客收藏房屋關聯表 (多對多)
# ==============================================================================
class Favorite(db.Model):
    __tablename__ = 'favorites'
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), primary_key=True)
    house_id = db.Column(db.Integer, db.ForeignKey('houses.house_id'), primary_key=True)    # 同一個租客對同一間房只能收藏一次
    created_at = db.Column(db.String(50), default=lambda: datetime.now().strftime('%Y-%m-%d %H:%M:%S')) # 收藏的時間（例如：依收藏時間排序）

    # 建立 ORM 關聯
    user = db.relationship('User', backref=db.backref('my_favorites', lazy='dynamic'))
    house = db.relationship('House', backref=db.backref('favorited_by', lazy='dynamic'))