from flask import Flask, request, jsonify
from flask_cors import CORS
from sqlalchemy import inspect, text
from models import db, User
from models import Favorite, HouseFeedback

app = Flask(__name__)
CORS(app)  # 讓 Flask app 允許跨網域存取

# 1. 資料庫基礎設定
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///renthouse.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 2. 與 Flask app 綁定
db.init_app(app)


def _ensure_schema():
    """補齊舊版資料庫缺少的欄位，避免 create_all 無法自動升級既有表結構。"""
    db.create_all()

    inspector = inspect(db.engine)
    if not inspector.has_table('renter_preferences'):
        return

    existing_columns = {
        column['name']
        for column in inspector.get_columns('renter_preferences')
    }
    if 'preferred_area' not in existing_columns:
        with db.engine.begin() as connection:
            connection.execute(text(
                "ALTER TABLE renter_preferences "
                "ADD COLUMN preferred_area VARCHAR(50)"
            ))

# ==============================================================================



# ==============================================================================
# 新增功能：身份驗證與權限管理 API
# ==============================================================================



# ［1. 登入 API］
@app.route('/api/login', methods=['POST'])

def login_api():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({"message": "請填寫 Email 與密碼"}), 400
        
    # 去資料庫撈這個帳密是否存在
    user = User.query.filter_by(email=email, password=password).first()
    
    if not user:
        # 找不到代表帳密錯誤，回傳 401 狀態碼
        return jsonify({"message": "Email 或密碼錯誤"}), 401
        
    # 登入成功！把使用者的重要 Session 資訊打包回傳給前端
    return jsonify({
        "message": f"歡迎回來，{user.name}！",
        "user": {
            "user_id": user.user_id,
            "name": user.name,
            "email": user.email,
            "role": user.role # 'tenant' 或 'landlord'
        }
    }), 200

@app.route('/api/register', methods=['POST'])
def register():
    # 接收前端傳的 JSON 資料
    data = request.get_json()
    
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    phone = data.get('phone')
    role = data.get('role')
    age = data.get('age')
    gender = data.get('gender')
    job = data.get('job')
    
    # 檢查必要欄位是否存在
    if not name or not email or not password:
        return jsonify({"message": "請完整填寫必要資料"}), 400
    
    # 去資料庫查看此 Email 是否已經被註冊過
    existing_user = User.query.filter_by(email=email).first()
    
    if existing_user:
        # 找得到資料代表被註冊過了，回傳 400 錯誤與提示訊息
        return jsonify({"message": "該 Email 已被註冊"}), 400
        
    # 如果一切正常，建立新的 User 物件並存入資料庫
    new_user = User(
        name=name,
        email=email,
        password=password,   # 尚未加密
        phone=phone,
        role=role,
        age=int(age) if age else None,
        gender=gender,
        job=job
    )
    
    # 把新物件存入資料庫並提交存檔
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({"message": "註冊成功！"}), 200

# ==============================================================================

# ==============================================================================
# 新增功能：房屋資料增刪查改 (CRUD) 與篩選 API
# ==============================================================================
from models import House  # 確保有引入 House 模型

# ［1. 刊登新房源 (POST) & 讀取/篩選所有房源 (GET)］
@app.route('/api/houses', methods=['GET', 'POST'])
def handle_houses_api():
    # --- A. 刊登新房源 (Create) ---
    if request.method == 'POST':
        data = request.get_json()
        
        landlord_id = data.get('landlord_id')
        location = data.get('location')
        price = data.get('price')
        size = data.get('size')
        type_ = data.get('type')
        equipment = data.get('equipment')
        
        if not location or not price or not landlord_id:
            return jsonify({"message": "請填寫必要資料（地點、租金與房東ID）"}), 400
            
        new_house = House(
            landlord_id=int(landlord_id),
            location=location,
            area=location.split('區')[0] + '區' if '區' in location else '未知地區', # 簡易從地址抓地區
            size=float(size) if size else 5.0,
            type=type_ if type_ else '獨立套房',
            price=int(price),
            equipment=equipment if equipment else '基本家具',
            visibility=True # 預設直接上架
        )
        
        db.session.add(new_house)
        db.session.commit()
        return jsonify({"message": "房源刊登成功！", "house_id": new_house.house_id}), 201

# --- B. 讀取與條件篩選 (Read) ---
    elif request.method == 'GET':
        search_loc = request.args.get('location', '')
        max_price = request.args.get('max_price')
        
        # 基礎查詢：只抓 visibility == True (未下架) 的房子
        query = House.query.filter_by(visibility=True)
        
        if search_loc:
            query = query.filter(House.location.contains(search_loc))
        if max_price and max_price.strip() != "":
            query = query.filter(House.price <= int(max_price))
            
        houses_list = query.all()
        
        # 格式化成前端可以讀的陣列物件
        results = []
        for h in houses_list:
            results.append({
                "id": h.house_id,
                "landlord_id": h.landlord_id,
                "location": h.location,
                "price": h.price,
                # 🎯 修正一：不要塞中文字「坪」在後端！傳回純數字，讓前端 input 可以完美讀取
                "size": h.size, 
                "type": h.type,
                "equipment": h.equipment,
                # 🎯 修正二：補上 100% 絕對存在、極高畫質的預設房屋圖片網址
                "image": "https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?q=80&w=1200&auto=format&fit=crop" 
            })
        return jsonify(results), 200

# ［2. 修改房源 (PUT) & 硬刪除房源 (DELETE)］
@app.route('/api/houses/<int:house_id>', methods=['PUT', 'DELETE'])
def handle_single_house_api(house_id):
    house = House.query.get(house_id)
    if not house:
        return jsonify({"message": "找不到該房源"}), 404

    # --- C. 完整修改房源 (Update) ---
    if request.method == 'PUT':
        data = request.get_json()
        
        # 允許前端修改所有細項欄位，如果前端沒傳該欄位，就維持原樣
        house.location = data.get('location', house.location)
        house.price = int(data.get('price')) if data.get('price') is not None else house.price
        house.size = float(data.get('size')) if data.get('size') is not None else house.size
        house.type = data.get('type', house.type)
        house.equipment = data.get('equipment', house.equipment)
        
        # 順便根據新地址自動重新計算「地區(area)」
        if 'location' in data:
            house.area = data['location'].split('區')[0] + '區' if '區' in data['location'] else house.area
        
        db.session.commit()
        return jsonify({"message": "房源所有細項已成功更新！"}), 200

    # --- D. 實體硬刪除房源 (Delete) ---
    elif request.method == 'DELETE':
        # 1. 刪除：硬刪除，直接把這筆房屋資料從資料庫抹除 (Hard Delete)
        db.session.delete(house)
        db.session.commit()
        return jsonify({"message": "房源已從資料庫實體刪除！"}), 200


# ==============================================================================
# 三、互動與社交功能 API (收藏夾、評論與星等計算)
# ==============================================================================
from models import RenterPreference, HousePreference

DEFAULT_HOUSE_IMAGE = (
    "https://images.unsplash.com/photo-1505693416388-ac5ce068fe85"
    "?q=80&w=1200&auto=format&fit=crop"
)

MATCH_THRESHOLD = 50
MATCH_WEIGHTS = {
    "budget": 40,
    "room_type": 30,
    "area": 15,
    "landlord_rating": 15,
}

SIMILAR_ROOM_TYPES = {
    "獨立套房": {"獨立套房", "分租套房"},
    "分租套房": {"獨立套房", "分租套房", "雅房"},
    "雅房": {"分租套房", "雅房"},
    "整層住家": {"整層住家"},
}


def _serialize_house(h, **extra):
    payload = {
        "id": h.house_id,
        "landlord_id": h.landlord_id,
        "location": h.location,
        "area": h.area,
        "price": h.price,
        "size": h.size,
        "type": h.type,
        "equipment": h.equipment,
        "image": DEFAULT_HOUSE_IMAGE,
    }
    payload.update(extra)
    return payload


def _is_renter(user):
    return user is not None and user.role in ("tenant", "renter")


def _get_house_feedback_stats(house_id):
    feedbacks = HouseFeedback.query.filter_by(house_id=house_id).all()
    if not feedbacks:
        return 0.0, 0
    avg_score = sum(f.score for f in feedbacks) / len(feedbacks)
    return round(avg_score, 1), len(feedbacks)


def _update_landlord_rating(landlord_id):
    landlord = User.query.get(landlord_id)
    if not landlord:
        return None

    house_ids = [
        h.house_id for h in House.query.filter_by(landlord_id=landlord_id).all()
    ]
    if not house_ids:
        landlord.rating = 0.0
        db.session.commit()
        return 0.0

    feedbacks = HouseFeedback.query.filter(
        HouseFeedback.house_id.in_(house_ids)
    ).all()
    landlord.rating = (
        round(sum(f.score for f in feedbacks) / len(feedbacks), 1)
        if feedbacks else 0.0
    )
    db.session.commit()
    return landlord.rating


def _calc_budget_score(price, min_budget, max_budget):
    min_budget = min_budget or 0
    max_budget = max_budget or 999999
    weight = MATCH_WEIGHTS["budget"]

    if min_budget <= price <= max_budget:
        return weight, "租金符合預算區間"

    if price > max_budget:
        over_ratio = (price - max_budget) / max(max_budget, 1)
        if over_ratio >= 0.5:
            return 0, "租金明顯超出最高預算"
        partial = max(0, int(weight * (1 - over_ratio * 2)))
        return partial, "租金略高於最高預算"

    under_ratio = (min_budget - price) / max(min_budget, 1)
    partial = max(0, int(weight * (1 - min(under_ratio, 1))))
    return partial, "租金低於最低預算"


def _calc_room_type_score(expected_type, actual_type):
    weight = MATCH_WEIGHTS["room_type"]
    if not expected_type or expected_type == actual_type:
        return weight, "房型完全符合"

    similar_types = SIMILAR_ROOM_TYPES.get(expected_type, {expected_type})
    if actual_type in similar_types:
        return int(weight * 0.5), "房型相近"

    return 0, "房型不符"


def _calc_area_score(preferred_area, house):
    weight = MATCH_WEIGHTS["area"]
    if not preferred_area:
        return weight, "未設定地區偏好"

    preferred_area = preferred_area.strip()
    if preferred_area in house.area or preferred_area in house.location:
        return weight, "地區完全符合"

    if house.area in preferred_area or house.location.startswith(preferred_area):
        return int(weight * 0.6), "地區部分符合"

    return 0, "地區不符"


def _calc_landlord_rating_score(landlord):
    weight = MATCH_WEIGHTS["landlord_rating"]
    if not landlord or not landlord.rating:
        return int(weight * 0.4), "房東尚無評價紀錄"

    normalized = min(max(landlord.rating, 0), 5) / 5
    return round(weight * normalized), f"房東評價 {landlord.rating} 星"


def _calc_match_score(house, pref):
    landlord = User.query.get(house.landlord_id)
    breakdown = {}

    budget_score, budget_reason = _calc_budget_score(
        house.price, pref.min_budget, pref.max_budget
    )
    room_score, room_reason = _calc_room_type_score(pref.room_type, house.type)
    area_score, area_reason = _calc_area_score(pref.preferred_area, house)
    rating_score, rating_reason = _calc_landlord_rating_score(landlord)

    breakdown["budget"] = {"score": budget_score, "reason": budget_reason}
    breakdown["room_type"] = {"score": room_score, "reason": room_reason}
    breakdown["area"] = {"score": area_score, "reason": area_reason}
    breakdown["landlord_rating"] = {"score": rating_score, "reason": rating_reason}

    total_score = budget_score + room_score + area_score + rating_score
    return total_score, breakdown


def _serialize_preference(pref):
    return {
        "renter_id": pref.renter_id,
        "room_type": pref.room_type,
        "min_budget": pref.min_budget,
        "max_budget": pref.max_budget,
        "preferred_area": pref.preferred_area or "",
        "move_date": pref.move_date,
    }


# ［3-1. 收藏夾：切換收藏狀態 (POST)］
@app.route('/api/favorites/toggle', methods=['POST'])
def toggle_favorite_api():
    data = request.get_json() or {}
    user_id = data.get('user_id')
    house_id = data.get('house_id')

    if not user_id or not house_id:
        return jsonify({"message": "缺少使用者 ID 或房屋 ID"}), 400

    user = User.query.get(int(user_id))
    if not user:
        return jsonify({"message": "找不到該使用者"}), 404

    house = House.query.get(int(house_id))
    if not house:
        return jsonify({"message": "找不到該房源"}), 404

    fav = Favorite.query.filter_by(user_id=user_id, house_id=house_id).first()

    if fav:
        db.session.delete(fav)
        db.session.commit()
        return jsonify({
            "message": "已取消收藏",
            "status": "removed",
            "house_id": house_id,
        }), 200

    if not house.visibility:
        return jsonify({"message": "此房源已下架，無法收藏"}), 400

    new_fav = Favorite(user_id=user_id, house_id=house_id)
    db.session.add(new_fav)
    db.session.commit()
    return jsonify({
        "message": "已成功加入收藏夾！",
        "status": "added",
        "house_id": house_id,
    }), 200


# ［3-2. 收藏夾：讀取該使用者收藏的房源清單 (GET)］
@app.route('/api/favorites/<int:user_id>', methods=['GET'])
def get_user_favorites_api(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"message": "找不到該使用者"}), 404

    favs = Favorite.query.filter_by(user_id=user_id).order_by(
        Favorite.created_at.desc()
    ).all()

    if not favs:
        return jsonify([]), 200

    house_ids = [f.house_id for f in favs]
    fav_houses = House.query.filter(
        House.house_id.in_(house_ids),
        House.visibility == True,
    ).all()
    house_map = {h.house_id: h for h in fav_houses}

    results = []
    for fav in favs:
        house = house_map.get(fav.house_id)
        if not house:
            continue
        avg_score, review_count = _get_house_feedback_stats(house.house_id)
        results.append(_serialize_house(
            house,
            favorited_at=fav.created_at,
            avg_score=avg_score,
            review_count=review_count,
        ))

    return jsonify(results), 200


# ［3-3. 收藏夾：查詢使用者已收藏的房源 ID 清單 (GET)］
@app.route('/api/favorites/<int:user_id>/ids', methods=['GET'])
def get_user_favorite_ids_api(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"message": "找不到該使用者"}), 404

    house_ids = [
        fav.house_id
        for fav in Favorite.query.filter_by(user_id=user_id).all()
    ]
    return jsonify({"house_ids": house_ids}), 200


# ［3-4. 房屋評論：新增評論並動態更新房東綜合評分 (POST)］
@app.route('/api/houses/<int:house_id>/feedback', methods=['POST'])
def add_house_feedback_api(house_id):
    house = House.query.get(house_id)
    if not house:
        return jsonify({"message": "找不到該房源"}), 404

    data = request.get_json() or {}
    renter_id = data.get('renter_id')
    score = data.get('score')
    comment = (data.get('comment') or '').strip()

    if not renter_id or score is None:
        return jsonify({"message": "請提供完整的評分與房客身分資訊"}), 400

    try:
        score = int(score)
    except (TypeError, ValueError):
        return jsonify({"message": "評分格式不正確"}), 400

    if score < 1 or score > 5:
        return jsonify({"message": "評分必須介於 1 到 5 分之間"}), 400

    renter = User.query.get(int(renter_id))
    if not renter:
        return jsonify({"message": "找不到該房客"}), 404

    if not _is_renter(renter):
        return jsonify({"message": "只有房客身分可以發表評論"}), 403

    if renter.user_id == house.landlord_id:
        return jsonify({"message": "房東無法評論自己的房源"}), 403

    existing = HouseFeedback.query.filter_by(
        house_id=house_id, renter_id=renter_id
    ).first()
    if existing:
        return jsonify({"message": "您已經針對此房源發表過評論囉！"}), 400

    new_fb = HouseFeedback(
        house_id=house_id,
        renter_id=renter_id,
        score=score,
        comment=comment or None,
    )
    db.session.add(new_fb)
    db.session.commit()

    house_avg, review_count = _get_house_feedback_stats(house_id)
    landlord_rating = _update_landlord_rating(house.landlord_id)

    return jsonify({
        "message": "評論提交成功，已更新房東滿意度星等！",
        "house_avg_score": house_avg,
        "review_count": review_count,
        "landlord_rating": landlord_rating,
    }), 201


# ［3-5. 房屋評論：讀取特定房屋的評論清單 (GET)］
@app.route('/api/houses/<int:house_id>/feedbacks', methods=['GET'])
def get_house_feedbacks_api(house_id):
    house = House.query.get(house_id)
    if not house:
        return jsonify({"message": "找不到該房源"}), 404

    feedbacks = HouseFeedback.query.filter_by(house_id=house_id).order_by(
        HouseFeedback.time.desc()
    ).all()

    results = []
    for feedback in feedbacks:
        renter = User.query.get(feedback.renter_id)
        results.append({
            "renter_name": renter.name if renter else "匿名租客",
            "score": feedback.score,
            "comment": feedback.comment,
            "time": feedback.time,
        })

    avg_score, review_count = _get_house_feedback_stats(house_id)
    landlord = User.query.get(house.landlord_id)

    return jsonify({
        "house_id": house_id,
        "avg_score": avg_score,
        "review_count": review_count,
        "landlord_rating": landlord.rating if landlord else 0.0,
        "feedbacks": results,
    }), 200


# ==============================================================================
# 四、租客需求媒合核心 API (基本框架與加權演算法架構)
# ==============================================================================

# ［4-1. 租客需求儲存：建立或更新租客的租屋偏好 (POST)］
@app.route('/api/preferences', methods=['POST'])
def save_renter_preference_api():
    data = request.get_json() or {}
    renter_id = data.get('renter_id')
    room_type = data.get('room_type')
    min_budget = data.get('min_budget')
    max_budget = data.get('max_budget')
    preferred_area = (data.get('preferred_area') or '').strip()

    if not renter_id:
        return jsonify({"message": "缺少租客帳號識別資訊"}), 400

    renter = User.query.get(int(renter_id))
    if not renter:
        return jsonify({"message": "找不到該房客"}), 404

    if not _is_renter(renter):
        return jsonify({"message": "只有房客身分可以設定租屋偏好"}), 403

    try:
        min_budget = int(min_budget) if min_budget not in (None, '') else 0
        max_budget = int(max_budget) if max_budget not in (None, '') else 999999
    except (TypeError, ValueError):
        return jsonify({"message": "預算格式不正確"}), 400

    if min_budget < 0 or max_budget < 0:
        return jsonify({"message": "預算不可為負數"}), 400

    if min_budget > max_budget:
        return jsonify({"message": "最低預算不可大於最高預算"}), 400

    pref = RenterPreference.query.filter_by(renter_id=renter_id).first()

    if not pref:
        hp = HousePreference(lease_term="一年", gender="不限", smoke=False, pet=False)
        db.session.add(hp)
        db.session.flush()

        pref = RenterPreference(renter_id=renter_id, hp_id=hp.hp_id)
        db.session.add(pref)

    pref.room_type = room_type or "獨立套房"
    pref.min_budget = min_budget
    pref.max_budget = max_budget
    pref.preferred_area = preferred_area or None

    db.session.commit()
    return jsonify({
        "message": "個人化租屋偏好需求已儲存成功！",
        "preference": _serialize_preference(pref),
    }), 200


# ［4-2. 租客需求讀取 (GET)］
@app.route('/api/preferences/<int:renter_id>', methods=['GET'])
def get_renter_preference_api(renter_id):
    renter = User.query.get(renter_id)
    if not renter:
        return jsonify({"message": "找不到該房客"}), 404

    pref = RenterPreference.query.filter_by(renter_id=renter_id).first()
    if not pref:
        return jsonify({"message": "尚未設定租屋偏好"}), 404

    return jsonify(_serialize_preference(pref)), 200


# ［4-3. 智慧媒合演算法：根據偏好權重篩選推薦房源 (GET)］
@app.route('/api/match/<int:renter_id>', methods=['GET'])
def match_houses_api(renter_id):
    renter = User.query.get(renter_id)
    if not renter:
        return jsonify({"message": "找不到該房客"}), 404

    pref = RenterPreference.query.filter_by(renter_id=renter_id).first()
    if not pref:
        return jsonify({
            "message": "請先至需求媒合頁面設定並儲存您的租屋偏好條件"
        }), 404

    all_houses = House.query.filter_by(visibility=True).all()
    matched_list = []

    for house in all_houses:
        match_score, breakdown = _calc_match_score(house, pref)
        if match_score < MATCH_THRESHOLD:
            continue

        avg_score, review_count = _get_house_feedback_stats(house.house_id)
        matched_list.append(_serialize_house(
            house,
            match_score=match_score,
            match_breakdown=breakdown,
            avg_score=avg_score,
            review_count=review_count,
        ))

    matched_list.sort(key=lambda item: item['match_score'], reverse=True)

    return jsonify({
        "renter_id": renter_id,
        "threshold": MATCH_THRESHOLD,
        "weights": MATCH_WEIGHTS,
        "total_candidates": len(all_houses),
        "matched_count": len(matched_list),
        "results": matched_list,
    }), 200

if __name__ == '__main__':
    with app.app_context():
        _ensure_schema()

    app.run(debug=True)