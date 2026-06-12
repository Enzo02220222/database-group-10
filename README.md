# 🏠 RentHouse

![Python](https://img.shields.io/badge/Python-3.x-blue.svg)
![Flask](https://img.shields.io/badge/Flask-Framework-green.svg)
![SQLite](https://img.shields.io/badge/SQLite-Database-lightgrey.svg)

RentHouse 是一個專為租客與房東設計的租屋媒合平台。解決了傳統租屋資訊碎片化、缺乏真實租客評價的問題，並提供智慧化的條件篩選與收藏功能，讓找房不再像大海撈針。

## 核心功能 (Key Features)

* **雙重身分系統 (Role-Based System)：** 單一帳號架構，支援「房東」與「房客」雙身分權限切換，介面與功能依據角色動態呈現。
* **智慧媒合過濾 (Smart Filter)：** 根據預算、期望房型與地區，加權計算並推薦最適合的房源。
* **真實評價機制 (Tenant Feedback)：** 確保租屋資訊透明，防範踩雷，並動態更新房東滿意度星等。
* **房源刊登與收藏 (CRUD & Collections)：** 房東可輕鬆上架與管理出租物件，房客可一鍵收藏心儀房源。

## 技術架構 (Tech Stack)

* **前端 (Front-End)：** HTML5, CSS3, JavaScript, Bootstrap 5
* **後端 (Back-End)：** Python, Flask, Flask-CORS
* **資料庫 (Database)：** SQLite, SQLAlchemy (ORM)

## 系統與資料庫設計亮點 (Architecture & Database Design)

本專案在後端與資料庫設計上，著重於安全性、擴充性與資料完整性：

* **ORM 資料映射 (Object-Relational Mapping)：**
    導入 SQLAlchemy 框架，以物件導向思維操作資料庫。不僅提升程式碼的可讀性與維護性，更可防範 SQL Injection，保障系統與用戶資料安全。
* **統一用戶模型 (Unified User Model)：**
    捨棄將房東與房客拆分為兩張表的傳統做法，整合為單一 `users` 表，並採用 Role-Based 權限架構。此設計可避免資料冗餘，並賦予系統未來擴展（如身份轉換）的高度彈性。
* **複合主鍵設計 (Composite Primary Key) 確保資料完整性：**
    在 `house_feedbacks` 表中，將 `house_id` 與 `renter_id` 設為複合主鍵，於資料庫限制「一位租客對同一間房只能留下一次評價」，確保評分機制的公正性。

## 環境建置與啟動 (Installation & Setup)

請依照以下步驟在本地端運行此專案：

1. **Clone 專案到本地端**
   ```bash
   git clone：https://github.com/Enzo02220222/database-group-10.git
   cd RentHouse
   ```

2. **建立並啟動虛擬環境**
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # macOS/Linux:
   source venv/bin/activate
   ```

3. **安裝相依套件**
   ```bash
   pip install flask flask-cors flask-sqlalchemy
   ```

4. **啟動 Flask 伺服器**
   ```bash
   python app.py
   ```
   伺服器預設將運行於 `http://127.0.0.1:5000`。請使用瀏覽器開啟專案資料夾中的 `index.html`，即可開始體驗完整系統。

##       目錄結構 (Project Structure)

```text
RentHouse/
│
├── app.py               # Flask 應用程式進入點與 API 路由設定
├── models.py            # SQLAlchemy 資料庫實體與關聯定義
├── index.html           # 前端 SPA 單頁應用程式主視圖
└── renthouse.db         # SQLite 資料庫檔案
```

---
*Designed and developed by Group 10.*
