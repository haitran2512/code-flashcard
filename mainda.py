import os
import csv
from datetime import timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
import random

# ==========================================
# KHỞI TẠO VÀ CẤU HÌNH ỨNG DỤNG WEB
# ==========================================
app = Flask(__name__)
app.config["SECRET_KEY"] = "Flashcard" # Chìa khóa bảo mật để dùng được tính năng 'session' (đăng nhập)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///Flash_card.db" # Tên file Database chứa dữ liệu
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False # Tắt cảnh báo hệ thống cho nhẹ máy
db = SQLAlchemy(app) # Khởi tạo công cụ quản lý Database

# ==========================================
# 1. MODELS (CẤU TRÚC CÁC BẢNG TRONG DATABASE)
# ==========================================
# Sửa ở đây nếu muốn thêm/bớt cột dữ liệu của Người dùng
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True) # Mã ID tự động tăng (1, 2, 3...)
    name = db.Column(db.String(100), unique=True, nullable=False) # Tên đăng nhập (unique=True nghĩa là không được trùng)
    email = db.Column(db.String(100), nullable=False) # Cột Email
    password = db.Column(db.String(100), nullable=False) # Cột Mật khẩu
    stage = db.Column(db.Integer, default=1) # (Có thể bỏ) Tiến độ bài học
    level = db.Column(db.String(2), default="A1") # Cột trình độ mặc định là A1

# Sửa ở đây nếu muốn thêm thông tin cho Từ vựng (ví dụ: phiên âm, ví dụ câu...)
class Vocabulary(db.Model):
    id = db.Column(db.Integer, primary_key=True)  
    word = db.Column(db.String(100), nullable=False) # Cột Từ tiếng Anh
    meaning = db.Column(db.String(200), nullable=False) # Cột Nghĩa tiếng Việt
    level = db.Column(db.String(2)) # Cột Phân loại trình độ của từ đó

# Bảng lưu lịch sử học của TỪNG người dùng (Ai đã học từ nào, thuộc hay chưa)
class UserCard(db.Model):
    id = db.Column(db.Integer, primary_key=True) 
    user_id = db.Column(db.Integer, nullable=False)  # Lưu ID của người dùng (Để biết thẻ này của ai)
    word = db.Column(db.String(100), nullable=False) # Lưu lại từ tiếng Anh
    meaning = db.Column(db.String(200), nullable=False) # Lưu lại nghĩa
    status = db.Column(db.Integer, default=0) # Trạng thái: 0 là Chưa thuộc (nằm trong Sổ tay), 1 là Đã thuộc

# ==========================================
# 2. ROUTES (CÁC ĐƯỜNG DẪN TRANG WEB)
# Nhìn vào @app.route("...") là biết nó phụ trách trang nào
# ==========================================

# --- TRANG CHỦ ---
@app.route("/")
@app.route("/home")
def home():
    # Kiểm tra xem người dùng đã đăng nhập chưa (có user_id trong trí nhớ web không)
    if "user_id" in session:
        # Lấy toàn bộ thông tin của User đó ra
        user = db.session.get(User, session["user_id"])
        
        # BẢO VỆ WEB: Nếu tài khoản bị xóa mất trong Database mà web vẫn nhớ nhầm -> Ép đăng xuất
        if not user: 
            session.clear() 
            return redirect(url_for("login"))
        
        # TÍNH TOÁN TIẾN ĐỘ HỌC:
        # 1. Đếm tổng số từ thuộc trình độ của user
        total_words = Vocabulary.query.filter_by(level=user.level).count()
        # 2. Lấy danh sách các từ đó ra
        level_words = [w.word for w in Vocabulary.query.filter_by(level=user.level).all()]
        
        # 3. Đếm số lượng từ trạng thái = 1 (Đã thuộc) của user này
        learned_words = 0
        if level_words:
            learned_words = UserCard.query.filter(
                UserCard.user_id == user.id, 
                UserCard.status == 1, 
                UserCard.word.in_(level_words)
            ).count()
        
        # 4. Tính phần trăm (%) tiến độ để làm thanh màu xanh
        progress = 0
        if total_words > 0:
            progress = round((learned_words / total_words) * 100)
            
        # Gửi dữ liệu tính toán được sang cho file home.html hiển thị
        return render_template("home.html", user=user, progress=progress, learned=learned_words, total=total_words)
        
    # Nếu chưa đăng nhập thì hiện trang chủ chào mừng mặc định
    return render_template("home.html")

# --- ĐĂNG KÝ TÀI KHOẢN ---
@app.route("/register", methods=["POST", "GET"])
def register():
    # Khi người dùng bấm nút Submit (POST)
    if request.method == "POST":
        # Hút dữ liệu từ các ô input của file HTML
        user_name = request.form["fullname"] 
        user_email = request.form["email"]
        user_password = request.form["password"] 
        
        # Kiểm tra xem tên đăng nhập đã bị ai lấy chưa
        if User.query.filter_by(name=user_name).first():
            flash("Tên đăng nhập đã tồn tại!", "error") # Hiện thông báo lỗi màu đỏ
            return redirect(url_for("register")) # Tải lại trang đăng ký
            
        # Tạo tài khoản mới và lưu cứng vào Database
        new_user = User(name=user_name, email=user_email, password=user_password)
        db.session.add(new_user)
        db.session.commit()
        
        # Lưu ID vào session (chính thức Đăng nhập thành công)
        session["user"] = new_user.name
        session["user_id"] = new_user.id
        
        # Chuyển hướng sang trang làm bài Test đầu vào
        return redirect(url_for("placement_test")) 
        
    return render_template("register.html")

# --- ĐĂNG NHẬP ---
@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method == "POST":
        user_name = request.form["username"]
        user_password = request.form["password"] 
        session.permanent = True # Nhớ trạng thái đăng nhập lâu hơn
        
        # Tìm User trong Database theo tên gõ vào
        user = User.query.filter_by(name=user_name).first()
        
        if user: # Nếu tìm thấy tên
            if user.password == user_password: # So sánh mật khẩu
                session["user"] = user.name
                session["user_id"] = user.id
                return redirect(url_for("home"))
            else:
                flash("Sai mật khẩu!", "error")
                return redirect(url_for("login"))
        else: # Nếu không tìm thấy tên
            flash("Sai tài khoản!", "error")
            return redirect(url_for("login"))

    # Nếu đang đăng nhập rồi mà cứ đòi vào link /login -> Đuổi về trang chủ
    if "user_id" in session: 
        return redirect(url_for("home"))
        
    return render_template("login.html")    

# --- ĐĂNG XUẤT ---
@app.route("/logout")
def logout():
    session.pop("user", None) # Xóa trí nhớ về tên
    session.pop("user_id", None) # Xóa trí nhớ về ID
    return redirect(url_for("home"))   

# --- QUÊN MẬT KHẨU (BƯỚC 1: XÁC NHẬN EMAIL) ---
@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email_nhap_vao = request.form["email"]
        user = User.query.filter_by(email=email_nhap_vao).first()
        
        if user: # Nếu Email đó có thật trong Database
            session['reset_email'] = email_nhap_vao # Lưu tạm email này để chuyển sang trang Đặt lại
            return redirect(url_for("reset_password"))
        else:
            flash("Email không tồn tại trong hệ thống!", "error")
            
    return render_template("forgot_password.html")

# --- QUÊN MẬT KHẨU (BƯỚC 2: ĐẶT LẠI PASS) ---
@app.route("/reset_password", methods=["GET", "POST"])
def reset_password():
    # Nếu chưa điền email ở bước 1 mà cứ cố vào link này -> Đuổi về bước 1
    if 'reset_email' not in session:
        return redirect(url_for('forgot_password'))

    if request.method == "POST":
        mat_khau_moi = request.form["password"]
        email_nguoi_dung = session['reset_email']
        
        # Cập nhật mật khẩu mới vào Database
        user = User.query.filter_by(email=email_nguoi_dung).first()
        if user:
            user.password = mat_khau_moi
            db.session.commit() # Chốt lưu
            
            session.pop('reset_email', None) # Xong việc thì xóa email lưu tạm đi
            flash("Đổi mật khẩu thành công! Hãy đăng nhập lại.", "success")
            return redirect(url_for("login"))
            
    return render_template("reset_password.html")

# ==========================================
# KHU VỰC ỨNG DỤNG HỌC TẬP CHÍNH
# ==========================================

# --- GIAO DIỆN HỌC FLASHCARD ---
@app.route("/study")
def study():
    if "user_id" not in session:
        flash("Bạn cần đăng nhập để vào học!", "error")
        return redirect(url_for("login"))
        
    user = db.session.get(User, session["user_id"])
    
    # 1. Tìm các thẻ CŨ mà user đã làm sai (status = 0)
    weak_cards = UserCard.query.filter_by(user_id=user.id, status=0).all()
    weak_words = [card.word for card in weak_cards]
    
    vocab_review = []
    if weak_words:
        # Bốc ngẫu nhiên tối đa 20 từ cũ để bắt học lại
        vocab_review = Vocabulary.query.filter(Vocabulary.word.in_(weak_words)).order_by(db.func.random()).limit(20).all()
        
    # Gói dữ liệu lại thành danh sách dạng Từ điển (Dictionary) cho JS dễ đọc
    vocab_list = [{"id": w.id, "word": w.word, "meaning": w.meaning} for w in vocab_review]
    
    # 2. Nếu từ cũ không đủ 20 từ, ta bốc thêm từ MỚI bù vào cho đủ quota
    if len(vocab_list) < 20:
        needed = 20 - len(vocab_list)
        # Lấy danh sách những từ đã từng học (để né chúng ra, không bốc lại)
        all_learned_cards = UserCard.query.filter_by(user_id=user.id).all()
        learned_words = [card.word for card in all_learned_cards]
        
        # Chỉ lấy các từ thuộc Level của user
        new_words_query = Vocabulary.query.filter_by(level=user.level)
        if learned_words: # Loại trừ các từ đã học
            new_words_query = new_words_query.filter(~Vocabulary.word.in_(learned_words))
            
        # Bốc ngẫu nhiên số lượng từ CÒN THIẾU
        new_words = new_words_query.order_by(db.func.random()).limit(needed).all()
        
        for w in new_words:
            vocab_list.append({"id": w.id, "word": w.word, "meaning": w.meaning})
    
    # 3. Xử lý trường hợp đã học hết sạch 100% từ trong Database
    if not vocab_list:
        vocab_list = [{"id": 0, "word": "Tuyệt vời", "meaning": "Cậu đã học thuộc toàn bộ từ vựng Level này!"}]
    else:
        # Ghi nhớ lại ID của 20 từ này để lát nữa mang sang phần Quiz thi luôn
        session['current_study_ids'] = [w['id'] for w in vocab_list if w['id'] != 0]

    return render_template("study.html", vocab_list=vocab_list, user=user)

# --- BÀI KIỂM TRA TRẮC NGHIỆM (QUIZ) ---
@app.route("/quiz", methods=["GET", "POST"])
def quiz():
    if "user_id" not in session: 
        return redirect(url_for("login"))
        
    user = db.session.get(User, session["user_id"])
        
    # KHI NGƯỜI DÙNG BẤM NÚT NỘP BÀI (Chấm điểm)
    if request.method == "POST":
        score = 0
        correct_answers = session.get('quiz_answers', {}) # Lấy đáp án gốc đã cất đi từ lúc tạo đề
        
        # Quét qua từng câu hỏi để chấm
        for q_id, data in correct_answers.items():
            user_ans = request.form.get(f"q_{q_id}") # Lấy đáp án user chọn
            word_text = data["word"]
            
            existing_card = UserCard.query.filter_by(user_id=user.id, word=word_text).first()
            
            if user_ans == data["meaning"]: # NẾU CHỌN ĐÚNG
                score += 1
                if existing_card:
                    existing_card.status = 1 # Cập nhật thẻ cũ thành "Đã thuộc"
                else:
                    new_card = UserCard(user_id=user.id, word=word_text, meaning=data["meaning"], status=1)
                    db.session.add(new_card)
            else: # NẾU CHỌN SAI
                if existing_card:
                    existing_card.status = 0 # Đẩy thẻ cũ về "Chưa thuộc" (Sổ tay)
                else:
                    new_card = UserCard(user_id=user.id, word=word_text, meaning=data["meaning"], status=0)
                    db.session.add(new_card)
                    
        db.session.commit() # Lưu toàn bộ kết quả vào Database
        
        # Báo điểm số ra màn hình
        if score == 10:
            flash("🎉 Xuất sắc tuyệt đối! Đạt 10/10 điểm.", "success")
        else:
            flash(f"🎯 Đạt {score}/10 điểm. Các từ trả lời sai đã bị đưa lại vào Sổ Tay Từ Khó để ôn tập!", "error")
            
        return redirect(url_for("home"))
        
    # KHI VÀO TRANG QUIZ (Tạo đề thi mới)
    # Lấy lại các ID từ vựng lúc nãy học ở Flashcard / Game
    study_ids = session.get('current_study_ids', [])
    if not study_ids:
        return redirect(url_for("study"))
        
    studied_words = Vocabulary.query.filter(Vocabulary.id.in_(study_ids)).all()
    num_questions = min(10, len(studied_words)) # Tạo tối đa 10 câu
    quiz_words = random.sample(studied_words, num_questions)
    
    questions = []
    all_meanings = [w.meaning for w in Vocabulary.query.all()] # Lấy toàn bộ nghĩa để làm đáp án nhiễu
    correct_dict = {}
    
    # Xây dựng từng câu hỏi 1
    for i, w in enumerate(quiz_words):
        correct_meaning = w.meaning
        wrong_options_pool = [m for m in all_meanings if m != correct_meaning] # Bỏ đáp án đúng ra
        num_wrong = min(3, len(wrong_options_pool))
        wrong_meanings = random.sample(wrong_options_pool, num_wrong) # Bốc 3 đáp án sai ngẫu nhiên
        
        options = wrong_meanings + [correct_meaning] # Trộn 3 sai + 1 đúng
        random.shuffle(options)
        
        q_id = str(i + 1)
        questions.append({
            "id": q_id,
            "word": w.word,
            "options": options
        })
        correct_dict[q_id] = {"meaning": correct_meaning, "word": w.word} # Cất đáp án đúng đi để lát chấm
        
    session['quiz_answers'] = correct_dict
    return render_template("quiz.html", questions=questions)

# --- API NHẬN ĐIỂM TỪ FLASHCARD KHI BẤM NÚT (KHÔNG CẦN TẢI LẠI TRANG) ---
@app.route("/mark_word", methods=["POST"])
def mark_word():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
        
    # Nhận dữ liệu gửi ngầm từ Javascript (AJAX / Fetch)
    data = request.get_json()
    word_str = data.get("word")
    meaning_str = data.get("meaning")
    status = data.get("status") # 1 là Đã thuộc, 0 là Chưa thuộc
    
    user = db.session.get(User, session["user_id"])
    
    card = UserCard.query.filter_by(user_id=user.id, word=word_str).first()
    if card:
        card.status = status 
    else:
        new_card = UserCard(user_id=user.id, word=word_str, meaning=meaning_str, status=status)
        db.session.add(new_card)
        
    db.session.commit()
    return jsonify({"success": True})

# --- GIAO DIỆN SỔ TAY TỪ KHÓ ---
@app.route("/review")
def review():
    if "user_id" not in session:
        return redirect(url_for("login"))
        
    user = db.session.get(User, session["user_id"])
    
    # Chỉ bốc những thẻ có status = 0 (Chưa thuộc) để đem ra hiển thị
    weak_words = UserCard.query.filter_by(user_id=user.id, status=0).all()
    
    return render_template("review.html", weak_words=weak_words, user=user)

# --- MINIGAME NỐI TỪ ---
@app.route("/match")
def match():
    if "user_id" not in session:
        flash("Bạn cần đăng nhập để chơi game!", "error")
        return redirect(url_for("login"))

    user = db.session.get(User, session["user_id"])

    # Bốc ngẫu nhiên 10 từ theo Level để làm thẻ trò chơi
    match_words = Vocabulary.query.filter_by(level=user.level).order_by(db.func.random()).limit(10).all()
    
    if not match_words:
        flash("Chưa có từ vựng nào để chơi game!", "error")
        return redirect(url_for("home"))

    # Đưa vào list chờ thi Quiz sau khi thắng
    session['current_study_ids'] = [w.id for w in match_words]
    vocab_list = [{"id": w.id, "word": w.word, "meaning": w.meaning} for w in match_words]

    return render_template("match.html", vocab_list=vocab_list)

# --- MINIGAME XẾP CHỮ ---
@app.route("/scramble")
def scramble():
    if "user_id" not in session:
        flash("Bạn cần đăng nhập để chơi game!", "error")
        return redirect(url_for("login"))

    user = db.session.get(User, session["user_id"])

    words = Vocabulary.query.filter_by(level=user.level).order_by(db.func.random()).limit(10).all()
    
    if not words:
        flash("Chưa có từ vựng nào để chơi game!", "error")
        return redirect(url_for("home"))

    vocab_list = [{"word": w.word, "meaning": w.meaning} for w in words]

    return render_template("scramble.html", vocab_list=vocab_list)

# --- API BẮT LỖI SAI GAME XẾP CHỮ (NHÉT VÀO SỔ TAY TỪ KHÓ) ---
@app.route("/scramble_wrong", methods=["POST"])
def scramble_wrong():
    if "user_id" not in session:
        return jsonify({"error": "Chưa đăng nhập"}), 401
        
    data = request.get_json()
    word_text = data.get("word")
    meaning_text = data.get("meaning")
    user_id = session["user_id"]
    
    existing_card = UserCard.query.filter_by(user_id=user_id, word=word_text).first()
    
    # Nếu gõ sai thì ép trạng thái về 0 (Chưa thuộc)
    if existing_card:
        existing_card.status = 0
    else:
        new_card = UserCard(user_id=user_id, word=word_text, meaning=meaning_text, status=0)
        db.session.add(new_card)
        
    db.session.commit()
    return jsonify({"success": True})


# ==========================================
# 3. KHỞI ĐỘNG MÁY CHỦ & NẠP DATA LẦN ĐẦU
# ==========================================
if __name__ == "__main__":
    with app.app_context():
        # Lệnh này kiểm tra xem đã có file Flash_card.db chưa, chưa có thì tự tạo mới tinh
        db.create_all()
        
        # Nếu Database vừa tạo đang trống trơn không có từ nào (count == 0)
        if Vocabulary.query.count() == 0:
            print("Chưa có từ vựng. Đang tiến hành nạp từ file vocab.csv...")
            try:
                # Đọc file Excel (CSV) chứa từ vựng
                with open('vocab.csv', mode='r', encoding='utf-8-sig') as file:
                    reader = csv.DictReader(file) # Đọc theo từng dòng (có chứa Tên cột)
                    data = list(reader) 
                
                # Quét từng dòng và nhét vào Database
                for row in data:
                    new_word = Vocabulary(word=row['word'], meaning=row['meaning'], level=row['level'])
                    db.session.add(new_word)
                db.session.commit() # Chốt lưu
                print("✅ Đã nạp thành công toàn bộ dữ liệu từ CSV vào Database!")
                
            except UnicodeDecodeError:
                # BẪY LỖI KHI CỨU HỘ: Dành cho máy tính dùng font chữ cổ (như Windows cũ)
                print("⚠️ Phát hiện file lưu dạng font Windows cũ, đang tự động chuyển hệ mã...")
                db.session.rollback() 
                
                with open('vocab.csv', mode='r', encoding='windows-1258') as file:
                    reader = csv.DictReader(file)
                    for row in reader:
                        new_word = Vocabulary(word=row['word'], meaning=row['meaning'], level=row['level'])
                        db.session.add(new_word)
                db.session.commit()
                print("✅ Đã tự động xử lý và nạp dữ liệu thành công từ file Excel!")
                
            except FileNotFoundError:
                print("❌ LỖI: Không tìm thấy file 'vocab.csv'.")

    # Mở máy chủ hoạt động
    app.run(debug=True)
