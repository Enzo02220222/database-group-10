from flask import Flask, request, jsonify
from flask_cors import CORS
from models import db, User

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



if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
    app.run(debug=True)