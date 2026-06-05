from flask import Flask, request, jsonify
from flask_cors import CORS
from models import db, User
from models import Favorite, HouseFeedback

app = Flask(__name__)
CORS(app)  # 讓 Flask app 允許跨網域存取

# 1. 資料庫基礎設定
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///renthouse.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 2. 與 Flask app 綁定
db.init_app(app)

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
        role=role
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
from models import Favorite, HouseFeedback

# ［3-1. 收藏夾：切換收藏狀態 (POST)］
@app.route('/api/favorites/toggle', methods=['POST'])
def toggle_favorite_api():
    data = request.get_json()
    user_id = data.get('user_id')
    house_id = data.get('house_id')
    
    if not user_id or not house_id:
        return jsonify({"message": "缺少使用者 ID 或房屋 ID"}), 400
        
    # 檢查是否已經收藏過
    fav = Favorite.query.filter_by(user_id=user_id, house_id=house_id).first()
    
    if fav:
        # 已存在則取消收藏 (Unfavorite)
        db.session.delete(fav)
        db.session.commit()
        return jsonify({"message": "已取消收藏", "status": "removed"}), 200
    else:
        # 不存在則新增收藏 (Favorite)
        new_fav = Favorite(user_id=user_id, house_id=house_id)
        db.session.add(new_fav)
        db.session.commit()
        return jsonify({"message": "已成功加入收藏夾！", "status": "added"}), 200

# ［3-2. 收藏夾：讀取該使用者收藏的房源清單 (GET)］
@app.route('/api/favorites/<int:user_id>', methods=['GET'])
def get_user_favorites_api(user_id):
    # 透過關聯表格進行查詢
    favs = Favorite.query.filter_by(user_id=user_id).all()
    house_ids = [f.house_id for f in favs]
    
    # 撈出所有收藏且未下架的房屋細節
    fav_houses = House.query.filter(House.house_id.in_(house_ids), House.visibility == True).all()
    
    results = []
    for h in fav_houses:
        results.append({
            "id": h.house_id,
            "location": h.location,
            "price": h.price,
            "size": h.size,
            "type": h.type,
            "equipment": h.equipment
        })
    return jsonify(results), 200

# ［3-3. 房屋評論：新增評論並動態更新房東綜合評分 (POST)］
@app.route('/api/houses/<int:house_id>/feedback', methods=['POST'])
def add_house_feedback_api(house_id):
    data = request.get_json()
    renter_id = data.get('renter_id')
    score = data.get('score')
    comment = data.get('comment')
    
    if not renter_id or score is None:
        return jsonify({"message": "請提供完整的評分與房客身分資訊"}), 400
        
    # 驗證複合主鍵限制：同一個房客對同一間房只能評論一次
    existing = HouseFeedback.query.filter_by(house_id=house_id, renter_id=renter_id).first()
    if existing:
        return jsonify({"message": "您已經針對此房源發表過評論囉！"}), 400
        
    # 建立新評論
    new_fb = HouseFeedback(
        house_id=house_id,
        renter_id=renter_id,
        score=int(score),
        comment=comment
    )
    db.session.add(new_fb)
    db.session.commit()
    
    # 🎯 動態反饋：重新計算該房東旗下所有房源的平均星等並更新至 users 欄位
    house = House.query.get(house_id)
    if house:
        landlord = User.query.get(house.landlord_id)
        if landlord:
            # 取得該房東擁有的所有房屋 ID 清單
            landlord_house_ids = [h.house_id for h in House.query.filter_by(landlord_id=landlord.user_id).all()]
            # 撈出對應的所有評價
            all_feedbacks = HouseFeedback.query.filter(HouseFeedback.house_id.in_(landlord_house_ids)).all()
            if all_feedbacks:
                avg_score = sum([f.score for f in all_feedbacks]) / len(all_feedbacks)
                landlord.rating = round(avg_score, 1) # 四捨五入至小數點第一位
                db.session.commit()

    return jsonify({"message": "評論提交成功，已更新房東滿意度星等！"}), 201

# ［3-4. 房屋評論：讀取特定房屋的評論清單 (GET)］
@app.route('/api/houses/<int:house_id>/feedbacks', methods=['GET'])
def get_house_feedbacks_api(house_id):
    feedbacks = HouseFeedback.query.filter_by(house_id=house_id).all()
    results = []
    for f in feedbacks:
        user = User.query.get(f.renter_id)
        results.append({
            "renter_name": user.name if user else "匿名租客",
            "score": f.score,
            "comment": f.comment,
            "time": f.time
        })
    return jsonify(results), 200


# ==============================================================================
# 四、租客需求媒合核心 API (基本框架與加權演算法架構)
# ==============================================================================
from models import RenterPreference, HousePreference

# ［4-1. 租客需求儲存：建立或更新租客的租屋偏好 (POST)］
@app.route('/api/preferences', methods=['POST'])
def save_renter_preference_api():
    data = request.get_json()
    renter_id = data.get('renter_id')
    room_type = data.get('room_type')
    min_budget = data.get('min_budget')
    max_budget = data.get('max_budget')
    
    if not renter_id:
        return jsonify({"message": "缺少租客帳號識別資訊"}), 400
        
    # 查看是否已建立過偏好框架
    pref = RenterPreference.query.filter_by(renter_id=renter_id).first()
    
    if not pref:
        # 先行建立底層的基礎 HousePreference 關聯對象
        hp = HousePreference(lease_term="一年", gender="不限", smoke=False, pet=False)
        db.session.add(hp)
        db.session.commit()
        
        pref = RenterPreference(renter_id=renter_id, hp_id=hp.hp_id)
        db.session.add(pref)
        
    # 更新欄位資料
    pref.room_type = room_type if room_type else "獨立套房"
    pref.min_budget = int(min_budget) if min_budget else 0
    pref.max_budget = int(max_budget) if max_budget else 999999
    
    db.session.commit()
    return jsonify({"message": "個人化租屋偏好需求已儲存成功！"}), 200

# ［4-2. 智慧媒合演算法：根據偏好權重篩選推薦房源 (GET)］
@app.route('/api/match/<int:renter_id>', methods=['GET'])
def match_houses_api(renter_id):
    pref = RenterPreference.query.filter_by(renter_id=renter_id).first()
    if not pref:
        return jsonify({"message": "請先至需求媒合頁面設定並儲存您的租屋偏好條件"}), 404
        
    # 智慧型條件評分演算法框架 (基於 100 分制倒扣邏輯)
    all_houses = House.query.filter_by(visibility=True).all()
    matched_list = []
    
    for h in all_houses:
        match_score = 100
        
        # 演算法權重權衡一：最高預算限制 (權重占比高：扣 40 分)
        if pref.max_budget and h.price > pref.max_budget:
            match_score -= 40
        # 最低預算調整 (輕微扣分項目：扣 10 分)
        elif pref.min_budget and h.price < pref.min_budget:
            match_score -= 10
            
        # 演算法權重權衡二：房型比對 (偏好吻合度：扣 30 分)
        if pref.room_type and pref.room_type != h.type:
            match_score -= 30
            
        # 媒合最低錄取門檻：高於 50 分者才推薦給前端
        if match_score >= 50:
            matched_list.append({
                "id": h.house_id,
                "landlord_id": h.landlord_id,
                "location": h.location,
                "price": h.price,
                "size": h.size,
                "type": h.type,
                "equipment": h.equipment,
                "match_score": match_score # 前端用來顯示進度條或百分比
            })
            
    # 根據媒合分數高低由上至下進行高分排序
    matched_list = sorted(matched_list, key=lambda x: x['match_score'], reverse=True)
    return jsonify(matched_list), 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
    app.run(debug=True)