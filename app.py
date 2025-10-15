from flask import Flask, render_template_string, request, redirect, url_for, session, send_from_directory, jsonify
import os
import psycopg2
from dotenv import load_dotenv

# Ortam değişkenlerini yükle
load_dotenv()

app = Flask(__name__)
app.secret_key = "supersecretkey"

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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
<html lang="tr">
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
        xhr.onload = function() { if(xhr.status==200){ location.reload(); } };
        xhr.send(data);
    }
    </script>
</head>
<body>
{% if page == 'login' or page=='register' %}
<div class="login-page">
    <div class="left-panel">
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
<div class="container" style="display:flex;">
    <div class="main" style="flex:3;padding:20px;">
        <div class="header">
            <h1>📁 Dosya Paylaşım Alanı</h1>
            <p>Hoşgeldin, <strong>{{ session['username'] }}</strong></p>
            <a href="{{ url_for('logout') }}" class="logout-btn">Çıkış Yap</a>
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
            <li>{{ user[1] }} — <small>{{ user[2] }}</small></li>
        {% endfor %}
        </ul>
    </div>
    {% endif %}
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
            cur.execute("SELECT * FROM users ORDER BY id")
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
            session["role"] = user[3]  # role sütunu
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
        return redirect(url_for("home"))
    return render_template_string(BASE_HTML, page="register")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

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
    return "", 200  # AJAX gönderimi için

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

if __name__=="__main__":
    port = int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0", port=port, debug=True)