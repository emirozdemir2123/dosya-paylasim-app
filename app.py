from flask import Flask, render_template_string, request, redirect, url_for, session, send_from_directory, jsonify
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = "supersecretkey"
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_db_connection():
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    return conn

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'user'
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

BASE_HTML = """
<!DOCTYPE html>
<html lang="tr" data-theme="{{ session.get('theme', 'light') }}">
<head>
    <meta charset="UTF-8">
    <title>UpMyFile</title>
    <link rel="stylesheet" href="/static/style.css">
    <script>
    function uploadFile(form) {
        event.preventDefault();
        var file = form.file.files[0];
        var desc = form.description.value;
        var xhr = new XMLHttpRequest();
        xhr.open("POST", "{{ url_for('upload') }}", true);
        xhr.upload.onprogress = function(e) {
            var percent = (e.loaded / e.total) * 100;
            document.getElementById("progress-bar").style.width = percent + "%";
            document.getElementById("progress-bar").innerText = Math.round(percent) + "%";
        };
        var data = new FormData();
        data.append("file", file);
        data.append("description", desc);
        xhr.onload = function() { 
            if(xhr.status==200){ 
                location.reload(); 
            } else if(xhr.status==413) {
                alert("Dosya boyutu 200MB sınırını aşıyor!");
            }
        };
        xhr.send(data);
    }

    function showPassword(userId) {
        fetch("/get_password/" + userId)
        .then(response => response.json())
        .then(data => {
            if (data.password) {
                alert("Kullanıcı Şifresi: " + data.password);
            } else {
                alert("Şifre alınamadı!");
            }
        });
    }

    function toggleTheme() {
        fetch("/toggle_theme").then(()=>location.reload());
    }
    </script>
</head>
<body>
<header class="site-header">
    <a href="{{ url_for('home') }}" class="logo-link">
        <img src="/static/logo.png" alt="UpMyFile Logo" class="site-logo">
        <span class="logo-text">UpMyFile</span>
    </a>
    {% if session.get('username') %}
    <nav class="nav-links">
        <a href="{{ url_for('home') }}">🏠 Anasayfa</a>
        <a href="{{ url_for('settings') }}">⚙️ Ayarlar</a>
        <a href="{{ url_for('logout') }}">🚪 Çıkış</a>
    </nav>
    {% endif %}
</header>

{% if page == 'login' or page=='register' %}
<!-- GİRİŞ / KAYIT SAYFASI -->
<div class="login-page">
    <div class="left-panel">
        <img src="/static/logo.png" alt="Logo" class="login-logo">
        <h1>UpMyFile</h1>
    </div>
    <div class="right-panel">
        <div class="login-container">
            <h2>{% if page=='login' %}Giriş Yap{% else %}Kayıt Ol{% endif %}</h2>
            <form method="POST" action="{{ url_for(page) }}">
                <input type="text" name="username" placeholder="Kullanıcı adı" required>
                <input type="password" name="password" placeholder="Şifre" required>
                <button type="submit">{% if page=='login' %}Giriş{% else %}Kayıt{% endif %}</button>
            </form>
            {% if page=='login' %}
            <p>Hesabın yok mu? <a href="{{ url_for('register') }}">Kayıt Ol</a></p>
            {% else %}
            <p>Zaten hesabın var mı? <a href="{{ url_for('login') }}">Giriş Yap</a></p>
            {% endif %}
            {% if error %}<p class="error">{{ error }}</p>{% endif %}
        </div>
    </div>
</div>

{% elif page == 'files' %}
<!-- DOSYA SAYFASI -->
<div class="container">
    <div class="main">
        <div class="header">
            <h1>📁 Dosya Paylaşım Alanı</h1>
            <p>Hoşgeldin, <strong>{{ session['username'] }}</strong></p>
        </div>

        <form onsubmit="uploadFile(this);" enctype="multipart/form-data" class="upload-form">
            <input type="file" name="file" required>
            <input type="text" name="description" placeholder="Dosya açıklaması" required>
            <button type="submit">Yükle</button>
            <div class="progress"><div id="progress-bar" class="progress-bar">0%</div></div>
        </form>

        <h2>Yüklenen Dosyalar</h2>
        <ul class="file-list">
        {% for file in files %}
            <li>
                <a href="{{ url_for('download', filename=file[1]) }}">{{ file[1] }}</a> — {{ file[3] }}
                {% if session.role=='admin' %}
                <form method="POST" action="{{ url_for('delete_file', file_id=file[0]) }}" style="display:inline;">
                    <button type="submit">Sil</button>
                </form>
                {% endif %}
                <br><small>Açıklama: {{ file[2] }}</small>
            </li>
        {% else %}
            <li>Henüz dosya yüklenmemiş.</li>
        {% endfor %}
        </ul>
    </div>

    {% if session.role=='admin' %}
    <div class="admin-panel">
        <h3>👑 Admin Paneli</h3>
        <ul>
        {% for user in users %}
            <li style="display:flex; justify-content:space-between; align-items:center;">
                <span>{{ user[1] }}</span>
                <div>
                    <button type="button" onclick="showPassword({{ user[0] }})">🔐 Göster</button>
                    <form method="POST" action="{{ url_for('delete_user', user_id=user[0]) }}" style="display:inline;">
                        <button type="submit">🗑️ Sil</button>
                    </form>
                </div>
            </li>
        {% endfor %}
        </ul>
    </div>
    {% endif %}
</div>

{% elif page == 'settings' %}
<!-- AYARLAR SAYFASI -->
<div class="settings-container">
    <h1>⚙️ Ayarlar</h1>
    <h3>🔑 Şifre Değiştir</h3>
    <form method="POST" action="{{ url_for('change_password') }}" class="settings-form">
        <input type="password" name="old_password" placeholder="Eski Şifre" required>
        <input type="password" name="new_password" placeholder="Yeni Şifre" required>
        <button type="submit">Değiştir</button>
    </form>

    {% if message %}<p class="success">{{ message }}</p>{% endif %}
    {% if error %}<p class="error">{{ error }}</p>{% endif %}

    <h3>🌓 Tema</h3>
    <button onclick="toggleTheme()">Tema Değiştir (Şu an: {{ session.get('theme','light') }})</button>
</div>
{% endif %}
</body>
</html>
"""

@app.route("/")
def home():
    if "username" in session:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM files ORDER BY id DESC")
        files = cur.fetchall()
        users = []
        if session.get("role") == "admin":
            cur.execute("SELECT id, username, password FROM users ORDER BY id")
            users = cur.fetchall()
        cur.close()
        conn.close()
        return render_template_string(BASE_HTML, page="files", files=files, users=users)
    return redirect(url_for("login"))

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        username = request.form["username"]
        password = request.form["password"]
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username=%s AND password=%s",(username,password))
        user = cur.fetchone()
        cur.close()
        conn.close()
        if user:
            session["username"] = username
            session["role"] = user[3]
            session["theme"] = "light"
            return redirect(url_for("home"))
        else:
            return render_template_string(BASE_HTML, page="login", error="Hatalı giriş bilgisi!")
    return render_template_string(BASE_HTML, page="login")

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method=="POST":
        username = request.form["username"]
        password = request.form["password"]
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO users (username, password, role) VALUES (%s,%s,'user')",(username,password))
            conn.commit()
        except psycopg2.IntegrityError:
            conn.rollback()
            return render_template_string(BASE_HTML, page="register", error="Bu kullanıcı adı zaten var!")
        finally:
            cur.close()
            conn.close()
        session["username"] = username
        session["role"] = "user"
        session["theme"] = "light"
        return redirect(url_for("home"))
    return render_template_string(BASE_HTML, page="register")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/settings")
def settings():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template_string(BASE_HTML, page="settings")

@app.route("/change_password", methods=["POST"])
def change_password():
    if "username" not in session:
        return redirect(url_for("login"))
    old_pw = request.form["old_password"]
    new_pw = request.form["new_password"]
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT password FROM users WHERE username=%s", (session["username"],))
    user_pw = cur.fetchone()
    if user_pw and user_pw[0] == old_pw:
        cur.execute("UPDATE users SET password=%s WHERE username=%s", (new_pw, session["username"]))
        conn.commit()
        msg = "Şifre başarıyla değiştirildi!"
        cur.close()
        conn.close()
        return render_template_string(BASE_HTML, page="settings", message=msg)
    else:
        cur.close()
        conn.close()
        return render_template_string(BASE_HTML, page="settings", error="Eski şifre yanlış!")

@app.route("/toggle_theme")
def toggle_theme():
    current = session.get("theme", "light")
    session["theme"] = "dark" if current == "light" else "light"
    return "", 204

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
        cur.execute("INSERT INTO files (filename, description, uploaded_by) VALUES (%s,%s,%s)",
                    (filename, description, session["username"]))
        conn.commit()
        cur.close()
        conn.close()
    return "", 200

@app.route("/delete/<int:file_id>", methods=["POST"])
def delete_file(file_id):
    if session.get("role") != "admin":
        return "Yetkiniz yok!", 403
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT filename FROM files WHERE id=%s", (file_id,))
    file = cur.fetchone()
    if file:
        file_path = os.path.join(UPLOAD_FOLDER, file[0])
        if os.path.exists(file_path):
            os.remove(file_path)
        cur.execute("DELETE FROM files WHERE id=%s", (file_id,))
        conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for("home"))

@app.route("/download/<filename>")
def download(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

@app.route("/get_password/<int:user_id>")
def get_password(user_id):
    if session.get("role") != "admin":
        return jsonify({"error": "Yetkiniz yok!"}), 403
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT password FROM users WHERE id=%s", (user_id,))
    pw = cur.fetchone()
    cur.close()
    conn.close()
    return jsonify({"password": pw[0] if pw else "Bulunamadı"})

@app.route("/delete_user/<int:user_id>", methods=["POST"])
def delete_user(user_id):
    if session.get("role") != "admin":
        return "Yetkiniz yok!", 403
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE id=%s", (user_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for("home"))

@app.errorhandler(413)
def file_too_large(e):
    return "Dosya boyutu 200MB sınırını aşıyor!", 413

if __name__=="__main__":
    port = int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0", port=port, debug=True)