import os
import csv
from datetime import timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
import random

app = Flask(__name__)
app.config["SECRET_KEY"] = "Flashcard"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///Flash_card.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# ==========================================
# 1. MODELS (CẤU TRÚC DATABASE)
# ==========================================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(100), nullable=False) # Đã có cột mật khẩu
    stage = db.Column(db.Integer, default=1)
    level = db.Column(db.String(2), default="A1")

class Vocabulary(db.Model):
    id = db.Column(db.Integer, primary_key=True)  
    word = db.Column(db.String(100), nullable=False)
    meaning = db.Column(db.String(200), nullable=False) 
    level = db.Column(db.String(2))

class UserCard(db.Model):
    id = db.Column(db.Integer, primary_key=True) 
    user_id = db.Column(db.Integer, nullable=False)  
    word = db.Column(db.String(100), nullable=False)
    meaning = db.Column(db.String(200), nullable=False)
    status = db.Column(db.Integer, default=0) 

# ==========================================
# 2. ROUTES (ĐIỀU HƯỚNG TRANG WEB)
# ==========================================
@app.route("/")
@app.route("/home")
def home():
    if "user_id" in session:
        user = User.query.get(session["user_id"])
        
        # 1. Đếm tổng số từ của Band/Level hiện tại (Ví dụ tổng số từ A1)
        total_words = Vocabulary.query.filter_by(level=user.level).count()
        
        # 2. Lấy danh sách các từ vựng thuộc Level đó
        level_words = [w.word for w in Vocabulary.query.filter_by(level=user.level).all()]
        
        # 3. Đếm số từ user ĐÃ THUỘC (status=1) nằm trong Level này
        learned_words = 0
        if level_words:
            learned_words = UserCard.query.filter(
                UserCard.user_id == user.id, 
                UserCard.status == 1, 
                UserCard.word.in_(level_words)
            ).count()
        
        # 4. Tính toán % hoàn thành
        progress = 0
        if total_words > 0:
            progress = round((learned_words / total_words) * 100)
            
        return render_template("home.html", user=user, progress=progress, learned=learned_words, total=total_words)
        
    return render_template("home.html")
                
@app.route("/register", methods=["POST", "GET"])
def register():
    if request.method == "POST":
        user_name = request.form["fullname"] 
        user_email = request.form["email"]
        user_password = request.form["password"] 
        
        if User.query.filter_by(name=user_name).first():
            flash("Tên đăng nhập đã tồn tại!", "error")
            return redirect(url_for("register"))
            
        new_user = User(name=user_name, email=user_email, password=user_password)
        db.session.add(new_user)
        db.session.commit()
        
        session["user"] = new_user.name
        session["user_id"] = new_user.id
        
        return redirect(url_for("placement_test")) 
        
    return render_template("register.html")

@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method == "POST":
        user_name = request.form["username"]
        user_password = request.form["password"] 
        session.permanent = True
        
        # Lấy thông tin user dựa trên tên đăng nhập trước
        user = User.query.filter_by(name=user_name).first()
        
        if user:
            # Nếu tên đăng nhập đúng, kiểm tra tiếp mật khẩu
            if user.password == user_password:
                session["user"] = user.name
                session["user_id"] = user.id
                return redirect(url_for("home"))
            else:
                flash("Sai mật khẩu!", "error") # Sai mật khẩu
                return redirect(url_for("login"))
        else:
            flash("Sai tài khoản!", "error") # Không tìm thấy tên đăng nhập
            return redirect(url_for("login"))

    if "user_id" in session: 
        return redirect(url_for("home"))
    return render_template("login.html")    

@app.route("/logout")
def logout():
    session.pop("user", None)
    session.pop("user_id", None)
    return redirect(url_for("home"))   

@app.route("/test", methods=["POST", "GET"])
def placement_test():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        selected_level = request.form.get("cefr_level") 
        current_user = User.query.get(session["user_id"])
        
        if current_user and selected_level:
            current_user.level = selected_level
            db.session.commit()
        
        flash("Đã cập nhật lộ trình học thành công!", "success")
        return redirect(url_for("home"))
        
    return render_template("test.html")

@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email_nhap_vao = request.form["email"]
        user = User.query.filter_by(email=email_nhap_vao).first()
        
        if user:
            session['reset_email'] = email_nhap_vao
            return redirect(url_for("reset_password"))
        else:
            flash("Email không tồn tại trong hệ thống!", "error")
            
    return render_template("forgot_password.html")

@app.route("/reset_password", methods=["GET", "POST"])
def reset_password():
    if 'reset_email' not in session:
        return redirect(url_for('forgot_password'))

    if request.method == "POST":
        mat_khau_moi = request.form["password"]
        email_nguoi_dung = session['reset_email']
        
        user = User.query.filter_by(email=email_nguoi_dung).first()
        if user:
            user.password = mat_khau_moi
            db.session.commit()
            
            session.pop('reset_email', None)
            flash("Đổi mật khẩu thành công! Hãy đăng nhập lại.", "success")
            return redirect(url_for("login"))
            
    return render_template("reset_password.html")

# GIAO DIỆN HỌC FLASHCARD
# ==========================================
# GIAO DIỆN HỌC FLASHCARD (20 TỪ)
# ==========================================
@app.route("/study")
def study():
    if "user_id" not in session:
        flash("Bạn cần đăng nhập để vào học!", "error")
        return redirect(url_for("login"))
        
    user = User.query.get(session["user_id"])
    
    # 1. Quét tìm các từ "Chưa thuộc" (status = 0) trong Database
    weak_cards = UserCard.query.filter_by(user_id=user.id, status=0).all()
    weak_words = [card.word for card in weak_cards]
    
    vocab_review = []
    if weak_words:
        # Lấy thông tin đầy đủ của các từ yếu (Tối đa 20 từ)
        vocab_review = Vocabulary.query.filter(Vocabulary.word.in_(weak_words)).order_by(db.func.random()).limit(20).all()
        
    vocab_list = [{"id": w.id, "word": w.word, "meaning": w.meaning} for w in vocab_review]
    
    # 2. Nếu từ chưa thuộc ít hơn 20 từ, bù thêm từ MỚI vào cho đủ quota
    if len(vocab_list) < 20:
        needed = 20 - len(vocab_list)
        
        # Tìm các từ ĐÃ TỪNG HỌC (cả thuộc và chưa thuộc) để loại trừ, không bốc lại
        all_learned_cards = UserCard.query.filter_by(user_id=user.id).all()
        learned_words = [card.word for card in all_learned_cards]
        
        new_words_query = Vocabulary.query.filter_by(level=user.level)
        if learned_words:
            new_words_query = new_words_query.filter(~Vocabulary.word.in_(learned_words))
            
        new_words = new_words_query.order_by(db.func.random()).limit(needed).all()
        
        for w in new_words:
            vocab_list.append({"id": w.id, "word": w.word, "meaning": w.meaning})
    
    # Nếu học hết sạch Database
    if not vocab_list:
        vocab_list = [{"id": 0, "word": "Tuyệt vời", "meaning": "Cậu đã học thuộc toàn bộ từ vựng Level này!"}]
    else:
        # Lưu ID vào session cho bài Quiz
        session['current_study_ids'] = [w['id'] for w in vocab_list if w['id'] != 0]

    return render_template("study.html", vocab_list=vocab_list, user=user)

# ==========================================
# BÀI TEST 10 CÂU TRẮC NGHIỆM
# ==========================================
# ==========================================
# BÀI TEST & LƯU KẾT QUẢ VÀO DATABASE
# ==========================================
@app.route("/quiz", methods=["GET", "POST"])
def quiz():
    if "user_id" not in session: 
        return redirect(url_for("login"))
        
    user = User.query.get(session["user_id"])
        
    # --- KHI NGƯỜI DÙNG NỘP BÀI ---
    if request.method == "POST":
        score = 0
        correct_answers = session.get('quiz_answers', {})
        
        for q_id, data in correct_answers.items():
            user_ans = request.form.get(f"q_{q_id}")
            word_text = data["word"]
            
            # Tìm thẻ từ hiện tại trong Database
            existing_card = UserCard.query.filter_by(user_id=user.id, word=word_text).first()
            
            if user_ans == data["meaning"]:
                score += 1
                # NẾU TRẢ LỜI ĐÚNG -> Đánh dấu Đã thuộc (1)
                if existing_card:
                    existing_card.status = 1
                else:
                    new_card = UserCard(user_id=user.id, word=word_text, meaning=data["meaning"], status=1)
                    db.session.add(new_card)
            else:
                # NẾU TRẢ LỜI SAI -> Đánh dấu Chưa thuộc (0) để nhốt vào Sổ Tay
                if existing_card:
                    existing_card.status = 0
                else:
                    new_card = UserCard(user_id=user.id, word=word_text, meaning=data["meaning"], status=0)
                    db.session.add(new_card)
                    
        db.session.commit() # Chốt lưu vào Database
        
        # Báo kết quả ra màn hình chính
        if score == 10:
            flash("🎉 Xuất sắc tuyệt đối! Đạt 10/10 điểm.", "success")
        else:
            flash(f"🎯 Đạt {score}/10 điểm. Các từ trả lời sai đã bị đưa lại vào Sổ Tay Từ Khó để ôn tập!", "error")
            
        return redirect(url_for("home"))
        
    # --- KHI TẠO ĐỀ THI MỚI ---
    study_ids = session.get('current_study_ids', [])
    if not study_ids:
        return redirect(url_for("study"))
        
    studied_words = Vocabulary.query.filter(Vocabulary.id.in_(study_ids)).all()
    num_questions = min(10, len(studied_words))
    quiz_words = random.sample(studied_words, num_questions)
    
    questions = []
    all_meanings = [w.meaning for w in Vocabulary.query.all()] 
    correct_dict = {}
    
    for i, w in enumerate(quiz_words):
        correct_meaning = w.meaning
        wrong_options_pool = [m for m in all_meanings if m != correct_meaning]
        num_wrong = min(3, len(wrong_options_pool))
        wrong_meanings = random.sample(wrong_options_pool, num_wrong)
        
        options = wrong_meanings + [correct_meaning]
        random.shuffle(options)
        
        q_id = str(i + 1)
        questions.append({
            "id": q_id,
            "word": w.word,
            "options": options
        })
        correct_dict[q_id] = {"meaning": correct_meaning, "word": w.word} 
        
    session['quiz_answers'] = correct_dict
    return render_template("quiz.html", questions=questions)

@app.route("/mark_word", methods=["POST"])
def mark_word():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
        
    data = request.get_json()
    word_str = data.get("word")
    meaning_str = data.get("meaning")
    status = data.get("status") # 0 = Chưa thuộc, 1 = Đã thuộc
    
    user = User.query.get(session["user_id"])
    
    # Kiểm tra xem từ này đã có trong danh sách của User chưa
    card = UserCard.query.filter_by(user_id=user.id, word=word_str).first()
    if card:
        card.status = status # Cập nhật trạng thái
    else:
        new_card = UserCard(user_id=user.id, word=word_str, meaning=meaning_str, status=status)
        db.session.add(new_card)
        
    db.session.commit()
    return jsonify({"success": True})

# ==========================================
# GIAO DIỆN: SỔ TAY TỪ KHÓ (REVIEW)
# ==========================================
@app.route("/review")
def review():
    if "user_id" not in session:
        return redirect(url_for("login"))
        
    user = User.query.get(session["user_id"])
    # Lấy toàn bộ các từ bị đánh dấu "Chưa thuộc" (status = 0)
    weak_words = UserCard.query.filter_by(user_id=user.id, status=0).all()
    
    return render_template("review.html", weak_words=weak_words, user=user)

# ==========================================
# MINI GAME: NỐI TỪ (ĐỒNG BỘ VỚI QUIZ)
# ==========================================
@app.route("/match")
def match():
    if "user_id" not in session:
        flash("Bạn cần đăng nhập để chơi game!", "error")
        return redirect(url_for("login"))

    user = User.query.get(session["user_id"])

    # 1. Tăng lên 10 từ (Sẽ tạo ra 20 thẻ lật)
    match_words = Vocabulary.query.filter_by(level=user.level).order_by(db.func.random()).limit(10).all()
    
    if not match_words:
        flash("Chưa có từ vựng nào để chơi game!", "error")
        return redirect(url_for("home"))

    # 2. LƯU 10 TỪ NÀY VÀO SESSION (Để lát nữa trang Quiz lấy đúng 10 từ này ra hỏi)
    session['current_study_ids'] = [w.id for w in match_words]

    vocab_list = [{"id": w.id, "word": w.word, "meaning": w.meaning} for w in match_words]

    return render_template("match.html", vocab_list=vocab_list)

# ==========================================
# MINI GAME: XẾP CHỮ (CÓ TÍNH VÀO TIẾN ĐỘ)
# ==========================================
@app.route("/scramble")
def scramble():
    if "user_id" not in session:
        flash("Bạn cần đăng nhập để chơi game!", "error")
        return redirect(url_for("login"))

    user = User.query.get(session["user_id"])

    # Bốc ngẫu nhiên 10 từ vựng theo Level của user
    words = Vocabulary.query.filter_by(level=user.level).order_by(db.func.random()).limit(10).all()
    
    if not words:
        flash("Chưa có từ vựng nào để chơi game!", "error")
        return redirect(url_for("home"))

    # GIỮ NGUYÊN TỪ GỐC để gửi về Server chấm điểm
    vocab_list = [{"word": w.word, "meaning": w.meaning} for w in words]

    return render_template("scramble.html", vocab_list=vocab_list)


# ==========================================
# 3. KHỞI CHẠY APP & NẠP DỮ LIỆU
# ==========================================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        
        if Vocabulary.query.count() == 0:
            print("Chưa có từ vựng. Đang tiến hành nạp từ file vocab.csv...")
            try:
                with open('vocab.csv', mode='r', encoding='utf-8-sig') as file:
                    reader = csv.DictReader(file)
                    data = list(reader) 
                
                for row in data:
                    new_word = Vocabulary(word=row['word'], meaning=row['meaning'], level=row['level'])
                    db.session.add(new_word)
                db.session.commit()
                print("✅ Đã nạp thành công toàn bộ dữ liệu từ CSV vào Database!")
                
            except UnicodeDecodeError:
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

    app.run(debug=True)