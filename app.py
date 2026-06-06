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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
    app.run(debug=True)