from flask import Flask, render_template_string, request, redirect, url_for, session, send_from_directory
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = "supersecretkey"

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# PostgreSQL bağlantısı
def get_db_connection():
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    return conn

# Tabloları oluştur
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id SERIAL PRIMARY KEY,
            filename TEXT NOT NULL,
            description TEXT,
            uploaded_by TEXT NOT NULL
        )
    """)

    conn.commit()
    cur.close()
    conn.close()

init_db()

# HTML Template
BASE_HTML = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <title>Dosya Paylaşım</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    {% if page == 'login' %}
        <div class="login-container">
            <h2>Giriş Yap</h2>
            <form method="POST" action="{{ url_for('login') }}">
                <input type="text" name="username" placeholder="Kullanıcı adı" required>
                <input type="password" name="password" placeholder="Şifre" required>
                <button type="submit">Giriş</button>
            </form>
            <p>Hesabın yok mu? <a href="{{ url_for('register') }}">Kayıt Ol</a></p>
            {% if error %}<p class="error">{{ error }}</p>{% endif %}
        </div>

    {% elif page == 'register' %}
        <div class="login-container">
            <h2>Kayıt Ol</h2>
            <form method="POST" action="{{ url_for('register') }}">
                <input type="text" name="username" placeholder="Kullanıcı adı" required>
                <input type="password" name="password" placeholder="Şifre" required>
                <button type="submit">Kayıt Ol</button>
            </form>
            <p>Zaten hesabın var mı? <a href="{{ url_for('login') }}">Giriş Yap</a></p>
            {% if error %}<p class="error">{{ error }}</p>{% endif %}
        </div>

    {% elif page == 'files' %}
        <div class="container">
            <div class="header">
                <h1>📁 Dosya Paylaşım Alanı</h1>
                <p>Hoşgeldin, <strong>{{ session['username'] }}</strong></p>
                <a href="{{ url_for('logout') }}" class="logout-btn">Çıkış Yap</a>
            </div>

            <form method="POST" enctype="multipart/form-data" action="{{ url_for('upload') }}" class="upload-form">
                <input type="file" name="file" required>
                <input type="text" name="description" placeholder="Dosya açıklaması" required>
                <button type="submit">Yükle</button>
            </form>

            <h2>Yüklenen Dosyalar</h2>
            <ul class="file-list">
                {% for file in files %}
                    <li>
                        <a href="{{ url_for('download', filename=file[1]) }}">{{ file[1] }}</a><br>
                        <small>Açıklama: {{ file[2] }} | Yükleyen: {{ file[3] }}</small>
                    </li>
                {% else %}
                    <li>Henüz dosya yüklenmemiş.</li>
                {% endfor %}
            </ul>
        </div>
    {% endif %}
</body>
</html>
"""

# Anasayfa
@app.route("/")
def home():
    if "username" in session:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM files ORDER BY id DESC")
        files = cur.fetchall()
        cur.close()
        conn.close()
        return render_template_string(BASE_HTML, page="files", files=files)
    return redirect(url_for("login"))

# Giriş
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username=%s AND password=%s", (username, password))
        user = cur.fetchone()
        cur.close()
        conn.close()
        if user:
            session["username"] = username
            return redirect(url_for("home"))
        else:
            return render_template_string(BASE_HTML, page="login", error="Hatalı giriş bilgisi!")
    return render_template_string(BASE_HTML, page="login")

# Kayıt
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
            conn.commit()
        except psycopg2.IntegrityError:
            conn.rollback()
            return render_template_string(BASE_HTML, page="register", error="Bu kullanıcı adı zaten var!")
        finally:
            cur.close()
            conn.close()
        session["username"] = username
        return redirect(url_for("home"))
    return render_template_string(BASE_HTML, page="register")

# Çıkış
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# Dosya yükleme
@app.route("/upload", methods=["POST"])
def upload():
    if "username" not in session:
        return redirect(url_for("login"))

    file = request.files["file"]
    description = request.form["description"]

    if file:
        filename = file.filename
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO files (filename, description, uploaded_by) VALUES (%s, %s, %s)",
                    (filename, description, session["username"]))
        conn.commit()
        cur.close()
        conn.close()

    return redirect(url_for("home"))

# Dosya indirme
@app.route("/download/<filename>")
def download(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
