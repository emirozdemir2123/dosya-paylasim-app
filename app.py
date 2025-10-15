from flask import Flask, render_template_string, request, redirect, url_for, session, send_from_directory
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = "supersecretkey"

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_db_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"))

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
<title>Dosya Paylaşım</title>
<style>
body { font-family: Arial; background: #f4f4f4; margin: 0; padding: 0; }
.container { display: flex; }
.main { flex: 3; padding: 20px; }
.admin-panel { flex: 1; background: #fff3cd; padding: 15px; border-left: 2px solid #ccc; }
.login-container { width: 300px; margin: 100px auto; text-align: center; }
input, button { margin: 5px; padding: 8px; width: 90%; }
.header { display: flex; justify-content: space-between; align-items: center; }
.logout-btn { background: #f33; color: #fff; padding: 6px 10px; text-decoration: none; border-radius: 4px; }
ul { list-style-type: none; padding: 0; }
li { margin-bottom: 8px; }
.upload-form { margin-top: 20px; }
</style>
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
    {% if error %}<p style="color:red">{{ error }}</p>{% endif %}
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
    {% if error %}<p style="color:red">{{ error }}</p>{% endif %}
</div>

{% elif page == 'files' %}
<div class="container">
<div class="main">
<div class="header">
<h1>📁 Dosya Paylaşım Alanı</h1>
<p>Hoşgeldin, <strong>{{ session['username'] }}</strong></p>
<a href="{{ url_for('logout') }}" class="logout-btn">Çıkış Yap</a>
</div>

<form id="uploadForm" enctype="multipart/form-data" class="upload-form">
    <input type="file" name="file" required>
    <input type="text" name="description" placeholder="Dosya açıklaması" required>
    <button type="submit">Yükle</button>
</form>
<progress id="progressBar" value="0" max="100" style="width:100%; display:none;"></progress>
<p id="progressText"></p>

<h2>Yüklenen Dosyalar</h2>
<ul class="file-list">
{% for file in files %}
    <li>
        <a href="{{ url_for('download', filename=file[1]) }}">{{ file[1] }}</a><br>
        <small>Açıklama: {{ file[2] }} | Yükleyen: {{ file[3] }}</small>
        {% if session.get('role') == 'admin' %}
        <form method="POST" action="{{ url_for('delete_file', file_id=file[0]) }}" style="display:inline">
            <button type="submit">Sil</button>
        </form>
        {% endif %}
    </li>
{% else %}
    <li>Henüz dosya yüklenmemiş.</li>
{% endfor %}
</ul>
</div>

{% if session.get('role') == 'admin' %}
<div class="admin-panel">
<h3>👑 Admin Paneli</h3>
<ul>
{% for user in users %}
    <li>{{ user[1] }} — {{ user[2] }} — <small>{{ user[3] }}</small></li>
{% endfor %}
</ul>
</div>
{% endif %}
</div>

<script>
const form = document.getElementById('uploadForm');
const progressBar = document.getElementById('progressBar');
const progressText = document.getElementById('progressText');

form.addEventListener('submit', function(e){
    e.preventDefault();
    const fileInput = form.querySelector('input[name="file"]');
    const description = form.querySelector('input[name="description"]').value;
    const file = fileInput.files[0];
    if(!file) return;

    const formData = new FormData();
    formData.append('file', file);
    formData.append('description', description);

    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/upload', true);

    xhr.upload.onprogress = function(e){
        if(e.lengthComputable){
            const percent = Math.round((e.loaded / e.total) * 100);
            progressBar.style.display = 'block';
            progressBar.value = percent;
            progressText.textContent = percent + '% yüklendi';
        }
    }

    xhr.onload = function(){
        if(xhr.status === 200){
            progressText.textContent = 'Yükleme tamamlandı!';
            window.location.reload();
        } else {
            progressText.textContent = 'Hata oluştu!';
        }
    }

    xhr.send(formData);
});
</script>
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
    if request.method == "POST":
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
            return redirect(url_for("home"))
        else:
            return render_template_string(BASE_HTML,page="login",error="Hatalı giriş bilgisi!")
    return render_template_string(BASE_HTML,page="login")

@app.route("/register",methods=["GET","POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO users (username,password,role) VALUES (%s,%s,%s)",(username,password,'user'))
            conn.commit()
        except psycopg2.IntegrityError:
            conn.rollback()
            return render_template_string(BASE_HTML,page="register",error="Bu kullanıcı adı zaten var!")
        finally:
            cur.close()
            conn.close()
        session["username"] = username
        session["role"] = "user"
        return redirect(url_for("home"))
    return render_template_string(BASE_HTML,page="register")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/upload",methods=["POST"])
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
                    (filename,description,session["username"]))
        conn.commit()
        cur.close()
        conn.close()
    return '',200

@app.route("/download/<filename>")
def download(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

# Admin için dosya silme
@app.route("/delete_file/<int:file_id>",methods=["POST"])
def delete_file(file_id):
    if session.get("role") != "admin":
        return "Yetkiniz yok!", 403
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT filename FROM files WHERE id=%s",(file_id,))
    file = cur.fetchone()
    if file:
        try:
            os.remove(os.path.join(UPLOAD_FOLDER,file[0]))
        except:
            pass
        cur.execute("DELETE FROM files WHERE id=%s",(file_id,))
        conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for("home"))

if __name__=="__main__":
    port = int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0",port=port,debug=True)
